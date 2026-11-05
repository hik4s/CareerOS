"""Bounded, cached regional source discovery and public JobPosting extraction."""
import asyncio
from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import queue
import socket
import ssl
import time
import threading
import unicodedata
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser

from .proximity import city_center

import httpx

REGION_TTL = 24 * 3600
MAX_REGIONS = 128
MAX_PAGES = 4
MAX_BYTES = 1024 * 1024
_cache = {}
_tasks = {}
_slots = asyncio.Semaphore(2)
_budget_day = ''
_budget_count = 0
_resolver_slots = threading.BoundedSemaphore(2)


def region_key(location):
    value = ''.join(c for c in unicodedata.normalize('NFKD', location.casefold())
                    if not unicodedata.combining(c))
    normalized = re.sub(r'\s+', ' ', re.sub(r'\s*[,;-]\s*', ', ', value)).strip()
    point = city_center(normalized)
    return f'geo:{point[0]}:{point[1]}' if point is not None else normalized


def public_url(value):
    if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 33 for c in value):
        raise ValueError('Invalid source URL')
    parts = urlsplit(value)
    host = parts.hostname
    if (parts.scheme != 'https' or not host or parts.port not in (None, 443) or
            parts.username or parts.password or parts.fragment or '\\' in value or
            not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host) or
            '.' not in host or host.endswith(('.local', '.internal', '.localhost'))):
        raise ValueError('Invalid source URL')
    return parts


def resolve_public_host(host):
    # DNS has no socket timeout. Keep at most two daemon lookups, even if the
    # system resolver stalls, and release collectors after two seconds.
    slots = _resolver_slots
    if not slots.acquire(blocking=False):
        raise TimeoutError('Source resolver busy')
    result = queue.Queue(maxsize=1)
    def resolve():
        try:
            result.put((socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM), None))
        except Exception as exc:
            result.put((None, exc))
        finally:
            slots.release()
    threading.Thread(target=resolve, daemon=True).start()
    try:
        records, error = result.get(timeout=2)
    except queue.Empty:
        raise TimeoutError('Source DNS timeout') from None
    if error:
        raise error
    return records


class PublicHTTPS(http.client.HTTPSConnection):
    """Pin the validated IP while retaining hostname verification and SNI."""
    def connect(self):
        records = resolve_public_host(self.host)
        addresses = list(dict.fromkeys(record[4][0] for record in records))
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise ValueError('Non-public source address')
        connection = socket.create_connection((addresses[0], 443), timeout=self.timeout)
        try:
            self.sock = connection
            self.sock = self._context.wrap_socket(connection, server_hostname=self.host,
                                                   do_handshake_on_connect=False)
            if time.monotonic() >= getattr(self, 'deadline', float('inf')):
                self.sock.close()
                raise TimeoutError('Source deadline exceeded')
            self.sock.do_handshake()
        except BaseException:
            connection.close()
            raise


def public_page(url):
    parts = public_url(url)
    path = parts.path or '/'
    if parts.query:
        path += '?' + parts.query
    connection = PublicHTTPS(parts.hostname, timeout=5, context=ssl.create_default_context())
    connection.deadline = time.monotonic() + 8
    def interrupt():
        if connection.sock:
            try:
                connection.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()

    timer = threading.Timer(8, interrupt)
    timer.daemon = True
    timer.start()
    try:
        connection.request('GET', path, headers={
            'Host': parts.hostname, 'User-Agent': 'CareerOS/1.0',
            'Accept': 'text/html,text/plain', 'Accept-Encoding': 'identity',
        })
        response = connection.getresponse()
        content = response.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError('Source too large')
        # Redirects are not followed. Every request is independently validated.
        return response.status, content
    finally:
        timer.cancel()
        connection.close()


def permitted_page(url):
    parts = public_url(url)
    status, robots = public_page('https://' + parts.hostname + '/robots.txt')
    if status == 200:
        policy = RobotFileParser()
        policy.parse(robots.decode('utf-8', errors='replace').splitlines())
        if not policy.can_fetch('CareerOS', url):
            raise ValueError('Source disallows collection')
    elif status != 404:
        raise ValueError('Unable to check source collection rules')
    status, content = public_page(url)
    if status in (404, 410):
        return None
    if status != 200:
        raise ValueError('Source unavailable')
    return content.decode('utf-8', errors='replace')


class PostingLinks(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        href = dict(attrs).get('href')
        if not href:
            return
        url = urljoin(self.base, href)
        try:
            parts = public_url(url)
        except ValueError:
            return
        if (parts.hostname == urlsplit(self.base).hostname and
                re.search(r'/(?:vagas?|jobs?|oportunidades?)/[^/]+', parts.path) and
                not parts.query and url not in self.links and len(self.links) < 2):
            self.links.append(url)


@dataclass
class RegionSnapshot:
    expires: float
    jobs: list
    sources: list
    available: bool
    reason: str = ''


def snapshot_path(key):
    directory = Path(os.getenv('CAREEROS_DISCOVERY_CACHE_DIR') or 'data/discovery')
    return directory / ('region-' + sha256(key.encode()).hexdigest() + '.json')


def read_region(key):
    try:
        data = json.loads(snapshot_path(key).read_bytes())
        if not isinstance(data['jobs'], list) or not isinstance(data['sources'], list):
            return None
        if any(not isinstance(job, dict) or not all(isinstance(job.get(field), str)
               for field in ('url', 'title', 'location', 'description', 'search_text', 'company', 'source'))
               or not isinstance(job.get('remote'), bool) for job in data['jobs']):
            return None
        remaining = min(REGION_TTL, max(0, data['expires_at'] - time.time()))
        return RegionSnapshot(time.monotonic() + remaining, data['jobs'], data['sources'], data['available'], data.get('reason', ''))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_region(key, snapshot):
    path = snapshot_path(key)
    temporary = path.with_suffix('.tmp')
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps({
            'expires_at': time.time() + min(REGION_TTL, max(0, snapshot.expires - time.monotonic())), 'jobs': snapshot.jobs,
            'sources': snapshot.sources, 'available': snapshot.available, 'reason': snapshot.reason,
        }), encoding='utf-8')
        temporary.replace(path)
    except OSError:
        pass


def provider():
    if os.getenv('CAREEROS_SEARCHAPI_API_KEY', '').strip():
        return 'searchapi'
    if os.getenv('CAREEROS_SERPAPI_API_KEY', '').strip():
        return 'serpapi'
    return None


async def search_sources(location, fetch_rows):
    # Only the region is transmitted. No profile, resume or contact information.
    query = f'"{location.replace(chr(34), "")}" (vagas OR empregos OR estágio) (prefeitura OR universidade OR recrutamento OR portal)'
    if provider() == 'searchapi':
        return await fetch_rows('GET', 'https://www.searchapi.io/api/v1/search', 'organic_results',
            authorization='Bearer ' + os.environ['CAREEROS_SEARCHAPI_API_KEY'].strip(),
            params={'engine': 'google', 'q': query, 'gl': 'br', 'hl': 'pt', 'num': 10})
    return await fetch_rows('GET', 'https://serpapi.com/search.json', 'organic_results',
        params={'engine': 'google', 'q': query, 'gl': 'br', 'hl': 'pt', 'num': 10,
                'api_key': os.environ['CAREEROS_SERPAPI_API_KEY'].strip()})


async def collect_region(location, fetch_rows, parse_job):
    global _budget_day, _budget_count
    async with _slots:
        today = time.strftime('%Y-%m-%d', time.gmtime())
        if today != _budget_day:
            _budget_day, _budget_count = today, 0
        if _budget_count >= 20:
            return RegionSnapshot(time.monotonic() + 300, [], [], False, 'daily_limit')
        _budget_count += 1
        rows = await search_sources(location, fetch_rows)
        candidates, seen = [], set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                parts = public_url(row.get('link'))
            except (ValueError, TypeError):
                continue
            if parts.hostname in seen:
                continue
            seen.add(parts.hostname)
            candidates.append((row['link'], parts.hostname))
            if len(candidates) == MAX_PAGES:
                break
        jobs, sources = [], []
        remaining_links = 2
        # A small queue also bounds sockets and parser work across cities.
        for url, host in candidates:
            source = {'name': host, 'url': url, 'status': 'needs_adapter'}
            try:
                markup = await asyncio.to_thread(permitted_page, url)
                if markup is None:
                    source['status'] = 'closed'
                else:
                    try:
                        job = parse_job(markup, url, host)
                        if job is None:
                            source['status'] = 'closed'
                    except ValueError:
                        job = None
                        links = PostingLinks(url)
                        links.feed(markup)
                        for child in links.links[:remaining_links]:
                            remaining_links -= 1
                            try:
                                detail = await asyncio.to_thread(permitted_page, child)
                                found = parse_job(detail, child, host) if detail else None
                                if found:
                                    jobs.append(found)
                                    source['status'] = 'integrated'
                            except (ValueError, OSError, http.client.HTTPException):
                                continue
                    if job:
                        jobs.append(job)
                        source['status'] = 'integrated'
            except ValueError:
                # No JobPosting or a policy restriction means no vacancy is imported.
                pass
            except (httpx.HTTPError, OSError, http.client.HTTPException):
                source['status'] = 'unavailable'
            sources.append(source)
            _cache[region_key(location)] = RegionSnapshot(0, list(jobs), list(sources), True)
        return RegionSnapshot(time.monotonic() + REGION_TTL, jobs, sources, True)


async def regional_feed(location, fetch_rows, parse_job):
    key = region_key(location)
    if not key or key in ('br', 'brazil', 'brasil'):
        return RegionSnapshot(0, [], [], False, 'city_required'), False
    if not provider():
        return RegionSnapshot(0, [], [], False, 'provider_not_configured'), False
    cached = _cache.get(key)
    if cached is None:
        cached = await asyncio.to_thread(read_region, key)
        if cached:
            _cache[key] = cached
    if cached and time.monotonic() < cached.expires:
        return cached, False
    task = _tasks.get(key)
    if task is None:
        if len(_tasks) >= 8:
            return cached or RegionSnapshot(0, [], [], False, 'busy'), False

        async def refresh():
            try:
                result = await collect_region(location, fetch_rows, parse_job)
                if result.reason == 'daily_limit' and cached:
                    result.jobs, result.sources = cached.jobs, cached.sources
                await asyncio.to_thread(save_region, key, result)
            except (httpx.HTTPError, TimeoutError, ValueError, OSError):
                result = RegionSnapshot(time.monotonic() + 60,
                    cached.jobs if cached else [], cached.sources if cached else [], False, 'unavailable')
            if len(_cache) >= MAX_REGIONS:
                _cache.pop(next(iter(_cache)))
            _cache[key] = result
            return result

        task = asyncio.create_task(refresh())
        _tasks[key] = task

        def finished(done):
            if _tasks.get(key) is done:
                _tasks.pop(key, None)
            if not done.cancelled():
                done.exception()
        task.add_done_callback(finished)
    await asyncio.wait([task], timeout=.25)
    if task.done() and not task.cancelled() and task.exception() is None:
        return task.result(), False
    return cached or RegionSnapshot(0, [], [], False), not task.done()
