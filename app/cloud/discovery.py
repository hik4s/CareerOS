"""Search public job feeds for the CareerOS job browser."""
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
import html
import json
import logging
import os
import re
import time
import unicodedata
from typing import Annotated, Literal
from urllib.parse import parse_qsl, quote, urlsplit
from xml.etree import ElementTree

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import require_user
from .proximity import city_center, nearest_distance

router = APIRouter(prefix='/api/discovery', dependencies=[Depends(require_user)])


def redact_credential_urls(record):
    message = record.getMessage()
    if 'serpapi.com/' in message and 'api_key=' in message:
        record.msg = re.sub(r'([?&]api_key=)[^&\s"]+', r'\1[redacted]', message)
        record.args = ()
    return True


logging.getLogger('httpx').addFilter(redact_credential_urls)
FEEDS = {
    key: (company, f'https://boards-api.greenhouse.io/v1/boards/{key}/jobs?content=true', 'jobs', company)
    for key, company in (
        ('quintoandar', 'Grupo QuintoAndar'), ('brex', 'Brex'), ('stone', 'Stone'),
        ('gympass', 'Wellhub'), ('vtex', 'VTEX'),
        ('sumup', 'SumUp'), ('wildlifestudios', 'Wildlife Studios'), ('ebury', 'Ebury'),
        ('rdstation', 'RD Station'), ('ilia', 'ília'), ('bancopan', 'Banco PAN'),
        ('zupinnovation', 'Zup Innovation'),
    )
}
FEEDS['arbeitnow'] = ('Arbeitnow', 'https://www.arbeitnow.com/api/job-board-api', 'data', '')
JSEARCH_PORTALS = {
    'jsearch_linkedin': ('LinkedIn', ('linkedin.com',)),
    'jsearch_indeed': ('Indeed', ('indeed.com', 'indeed.com.br')),
    'jsearch_glassdoor': ('Glassdoor', ('glassdoor.com', 'glassdoor.com.br')),
}
AGGREGATOR_FEEDS = {
    **{key: (f'{name} via JSearch', 'CAREEROS_JSEARCH_API_KEY')
       for key, (name, _) in JSEARCH_PORTALS.items()},
    'serpapi_google': ('Google Jobs via SerpApi', 'CAREEROS_SERPAPI_API_KEY'),
    'searchapi_google': ('Google Jobs via SearchApi', 'CAREEROS_SEARCHAPI_API_KEY'),
    'searchapi_linkedin': ('LinkedIn via SearchApi', 'CAREEROS_SEARCHAPI_API_KEY'),
}
AGGREGATOR_TTL = 24 * 3600
PAGE_SIZE = 20
CACHE_TTL = 300
MAX_FEED_BYTES = 5 * 1024 * 1024
_cache = {}
_refresh_tasks = {}
_locks = {key: asyncio.Lock() for key in FEEDS}
_locks.update({key: asyncio.Lock() for key in AGGREGATOR_FEEDS})
_locks.update(gupy=asyncio.Lock(), careers=asyncio.Lock(), employer=asyncio.Lock(),
              syndication=asyncio.Lock())
CAREER_TTL = 3600
CAREER_LIMIT = 30


@dataclass
class Snapshot:
    expires: float
    jobs: list
    available: bool
    updated_at: str | None
    partial: bool = False
_jooble_cache = {}
_jooble_lock = asyncio.Lock()


def clean(value, limit):
    if not isinstance(value, str):
        return ''
    return ' '.join(re.sub(r'<[^>]*>', ' ', html.unescape(value)).split())[:limit]


def description_text(value):
    if not isinstance(value, str):
        return ''
    markup = html.unescape(value)
    markup = re.sub(r'<li\b[^>]*>', '\n• ', markup, flags=re.I)
    markup = re.sub(r'<(?:br\b[^>]*|/(?:p|div|li|h[1-6]))\s*>', '\n', markup, flags=re.I)
    plain = html.unescape(re.sub(r'<[^>]*>', ' ', markup))
    lines = (' '.join(line.split()) for line in plain.splitlines())
    return '\n'.join(line for line in lines if line)[:30000]


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(c))


LEVELS = {
    'intern': re.compile(r'\b(?:estagio|estagiari[oa]|intern|internship|aprendiz)\b'),
    'junior': re.compile(r'\b(?:junior|jr|entry.level)\b'),
    'mid': re.compile(r'\b(?:pleno|plena|mid.level|intermediate)\b'),
    'senior': re.compile(r'\b(?:senior|sr|staff|principal|lead)\b'),
    'trainee': re.compile(r'\btrainee\b'),
}
BRAZIL = re.compile(r'\b(?:brasil|brazil|br|sao paulo|rio de janeiro|belo horizonte|curitiba|'
                    r'porto alegre|brasilia|recife|fortaleza|salvador|florianopolis|manaus|'
                    r'campinas|goiania|espirito santo|minas gerais|pernambuco|parana|bahia)\b')
GLOBAL_REMOTE = re.compile(r'\b(?:worldwide|anywhere|global|mundial|latin america|latam|america latina)\b')
EXCLUDES_BRAZIL = re.compile(r'\b(?:(?:excluding|except|exceto)\s+(?:brasil|brazil)|(?:brasil|brazil)\s+excluded)\b')
ALIASES = (
    ('estagio', 'estagiario', 'estagiaria', 'intern', 'internship'),
    ('junior', 'jr'), ('dados', 'data'), ('desenvolvedor', 'desenvolvedora', 'developer'),
    ('engenheiro', 'engenheira', 'engineer'), ('analista', 'analyst'),
    ('remoto', 'remota', 'remote'),
)
STOP_WORDS = {'a', 'as', 'o', 'os', 'de', 'da', 'do', 'das', 'dos', 'em', 'no', 'na', 'para', 'e'}


def search_terms(value):
    words = re.findall(r'[\w+#.]+', folded(value))
    terms = dict.fromkeys(word.strip('.') for word in words if word.strip('.') not in STOP_WORDS | {''})
    return [re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(alias) for alias in
            next((group for group in ALIASES if term in group), (term,))) + r')(?!\w)') for term in terms]


def infer_work_model(job):
    place = folded(job['location'])
    title = folded(job['title'])
    if job.get('work_model'):
        return job['work_model']
    if re.search(r'\b(?:hybrid|hibrid[oa])\b', place + ' ' + title):
        return 'hybrid'
    if job['remote'] or re.search(r'\b(?:remote|remot[oa])\b', place + ' ' + title):
        return 'remote'
    if re.search(r'\b(?:on.site|onsite|presencial)\b', place + ' ' + title):
        return 'onsite'
    return ''


def matches_location(job, where, model):
    place = folded(job['location'])
    if where == 'brasil':
        regions = folded(job.get('applicant_regions', ''))
        if model == 'remote' and EXCLUDES_BRAZIL.search(regions + ' ' + place):
            return False
        if model == 'remote' and regions:
            return bool(BRAZIL.search(regions) or GLOBAL_REMOTE.search(regions))
        if BRAZIL.search(place):
            return True
        return model == 'remote' and bool(GLOBAL_REMOTE.search(place)) and not re.search(r'\b(?:only|somente)\b', place)
    return not where or where in re.sub(r'\bbrazil\b', 'brasil', place)


def relevance(job, title, company, terms, *, title_only=False, provider_matched=False):
    score = 0
    scope = 'title' if terms else ''
    for term in terms:
        if term.search(title):
            score += 12
            continue
        if title_only:
            return None
        if scope == 'title':
            scope = 'details'
        if term.search(company):
            score += 5
        elif term.search(job['search_text']):
            score += 1
        elif provider_matched:
            scope = 'provider'
        else:
            return None
    return score, scope


def best_match(job, alternatives, *, title_only, provider_matched):
    title, company = folded(job['title']), folded(job['company'])
    best = None
    for terms in alternatives:
        match = relevance(job, title, company, terms, title_only=title_only,
                          provider_matched=provider_matched)
        if match is None:
            continue
        score, scope = match
        score /= max(1, len(terms))
        if best is None or score > best[0]:
            best = score, scope
    return best


def duplicate_keys(job):
    parts = urlsplit(job['url'])
    query = parse_qsl(parts.query)
    host = parts.hostname or ''
    if domain_matches(host, ('linkedin.com',)):
        match = re.fullmatch(r'/jobs/view/(?:[^/]+-)?(\d+)/?', parts.path)
        if match:
            yield 'linkedin', match[1]
    if domain_matches(host, ('indeed.com', 'indeed.com.br')) and parts.path.rstrip('/') == '/viewjob':
        identifier = dict(query).get('jk')
        if identifier:
            yield 'indeed', identifier
    parameters = tuple(sorted((key, value) for key, value in query
                              if not key.startswith('utm_') and key not in ('fbclid', 'gclid')))
    yield parts.hostname, parts.path.rstrip('/'), parameters
    if len(job['description']) >= 100 and job['company'] and job['location']:
        digest = sha256(' '.join(job['description'].casefold().split()).encode()).digest()
        yield (folded(job['title']), folded(job['company']), folded(job['location']), digest)


def posting_expired(value):
    if isinstance(value, str) and value:
        with suppress(ValueError):
            expires = datetime.fromisoformat(value)
            now = datetime.now(timezone.utc)
            if len(value) == 10:
                return expires.date() < now.date()
            return expires.replace(tzinfo=expires.tzinfo or timezone.utc) <= now
    return False


def safe_listing_url(value):
    if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 32 for c in value):
        return ''
    try:
        url = urlsplit(value)
        if url.scheme == 'https' and url.hostname and not url.username and not url.password and url.port in (None, 443):
            return value
    except ValueError:
        pass
    return ''


def normalize(row, source, company):
    if not isinstance(row, dict):
        return None
    title = clean(row.get('title'), 500)
    url = safe_listing_url(row.get('url') if not company else row.get('absolute_url'))
    if not title or not url:
        return None
    place = row.get('location')
    location = clean(place.get('name') if isinstance(place, dict) else place, 500)
    tags = row.get('tags')
    keywords = ' '.join(clean(x, 100) for x in tags[:20]) if isinstance(tags, list) else ''
    remote = row.get('remote') is True or bool(re.search(r'\b(remote|remoto)\b', folded(location)))
    description = description_text(row.get('content') if company else row.get('description'))
    company = company or clean(row.get('company_name'), 500)
    return {
        'title': title, 'company': company,
        'location': location, 'url': url, 'source': source, 'remote': remote,
        'description': description,
        'work_model': clean(row.get('work_model'), 20),
        'applicant_regions': clean(row.get('applicant_regions'), 500),
        'valid_through': clean(row.get('valid_through'), 50),
        'search_text': folded(' '.join((title, company, keywords, description))),
    }


def gupy_jobs(companies):
    for company in companies:
        if not isinstance(company, dict) or not isinstance(company.get('jobs'), list):
            continue
        for row in company['jobs']:
            if not isinstance(row, dict):
                continue
            address = row.get('address')
            address = address if isinstance(address, dict) else {}
            country = address.get('country')
            location = ', '.join(dict.fromkeys(filter(None, (
                clean(address.get('city'), 200), clean(address.get('state') or address.get('region'), 200),
                'Brasil' if country == 'BR' else clean(country, 100),
            ))))
            url = row.get('url')
            if isinstance(url, str) and url.startswith('http://'):
                url = 'https://' + url[len('http://'):]
            description = '\n'.join(
                row[field] for field in ('description', 'responsibilities', 'prerequisites')
                if isinstance(row.get(field), str)
            )
            job = normalize({
                'title': row.get('title'), 'company_name': company.get('name'),
                'location': location, 'url': url, 'description': description,
                'remote': row.get('remoteWorking'), 'tags': [row.get('type')],
                'valid_through': row.get('expiringDate'),
            }, 'Gupy', '')
            if job:
                yield job


async def fetch_content(method, url, *, accept, authorization='', client=None, headers=None, **options):
    headers = {'Accept': accept, 'User-Agent': 'CareerOS', **(headers or {})}
    if authorization:
        headers['Authorization'] = authorization
    async with asyncio.timeout(10), AsyncExitStack() as stack:
        if client is None:
            connection = await asyncio.to_thread(httpx.AsyncClient, timeout=8, follow_redirects=False)
            client = await stack.enter_async_context(connection)
        async with client.stream(method, url, headers=headers, **options) as response:
            response.raise_for_status()
            content = bytearray()
            async for chunk in response.aiter_bytes():
                if len(content) + len(chunk) > MAX_FEED_BYTES:
                    raise ValueError('Feed too large')
                content.extend(chunk)
    return content


async def fetch_rows(method, url, field, **options):
    payload = json.loads(await fetch_content(method, url, accept='application/json', **options))
    rows = payload.get(field) if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError('Invalid feed')
    return rows


def domain_matches(host, domains):
    return any(host == domain or host.endswith('.' + domain) for domain in domains)


def portal_for_url(url):
    host = urlsplit(url).hostname or ''
    portals = (*JSEARCH_PORTALS.values(), ('Gupy', ('gupy.io',)),
               ('InfoJobs', ('infojobs.com.br',)), ('Catho', ('catho.com.br',)))
    return next((name for name, domains in portals if domain_matches(host, domains)), None)


async def jsearch_jobs(key, token):
    publisher, domains = JSEARCH_PORTALS[key]
    rows = await fetch_rows(
        'GET', 'https://api.openwebninja.com/jsearch/search', 'data',
        headers={'x-api-key': token},
        params={'query': f'estágio tecnologia da informação Brasil via {publisher}',
                'country': 'br', 'language': 'pt', 'date_posted': 'month'},
    )
    jobs = []
    for row in rows[:50]:
        if not isinstance(row, dict):
            continue
        options = row.get('apply_options')
        links = [row.get('job_apply_link')]
        if isinstance(options, list):
            links.extend(option.get('apply_link') for option in options[:20] if isinstance(option, dict))
        for link in links:
            if not safe_listing_url(link):
                continue
            host = urlsplit(link).hostname
            if domain_matches(host, domains):
                break
        else:
            continue
        country = clean(row.get('job_country'), 20).upper()
        if country and country != 'BR':
            continue
        location = ', '.join(filter(None, (clean(row.get('job_city'), 150),
                                            clean(row.get('job_state'), 100))))
        location = location or clean(row.get('job_location'), 300)
        if country == 'BR' and not re.search(r'\b(?:brasil|brazil|br)\b', folded(location)):
            location = ', '.join(filter(None, (location, 'Brasil')))
        job = normalize({
            'title': row.get('job_title'), 'company_name': row.get('employer_name'),
            'url': link, 'location': location, 'description': row.get('job_description'),
            'remote': row.get('job_is_remote'),
        }, f'{publisher} via JSearch', '')
        if job:
            jobs.append(job)
    return jobs


async def aggregator_jobs(key, token):
    if key in JSEARCH_PORTALS:
        return await jsearch_jobs(key, token)
    query = 'estágio tecnologia da informação Brasil'
    if key == 'serpapi_google':
        rows = await fetch_rows('GET', 'https://serpapi.com/search.json', 'jobs_results',
                                params={'engine': 'google_jobs', 'q': query, 'gl': 'br',
                                        'hl': 'pt', 'api_key': token})
        provider, options_key = 'SerpApi', 'apply_options'
    else:
        engine = 'linkedin_jobs' if key == 'searchapi_linkedin' else 'google_jobs'
        params = {'engine': engine, 'q': query, 'location': 'Brazil'}
        if engine == 'google_jobs':
            params.update(gl='br', hl='pt')
        rows = await fetch_rows('GET', 'https://www.searchapi.io/api/v1/search', 'jobs',
                                authorization='Bearer ' + token, params=params)
        provider, options_key = 'SearchApi', 'apply_links'
    jobs = []
    for row in rows[:50]:
        if not isinstance(row, dict):
            continue
        options = row.get(options_key)
        links = [row.get('link'), row.get('apply_link')]
        if isinstance(options, list):
            links.extend(item.get('link') for item in options[:20] if isinstance(item, dict))
        links = [url for link in links if (url := safe_listing_url(link))]
        if not links:
            continue
        url = next((link for link in links if portal_for_url(link)), links[0])
        portal = portal_for_url(url)
        if key == 'searchapi_linkedin' and portal != 'LinkedIn':
            continue
        extensions = row.get('detected_extensions')
        job = normalize({
            'title': row.get('title'), 'company_name': row.get('company_name'),
            'location': row.get('location'), 'url': url, 'description': row.get('description'),
            'remote': isinstance(extensions, dict) and extensions.get('work_from_home') is True,
        }, f'{portal or "Google Jobs"} via {provider}', '')
        if job:
            jobs.append(job)
    return jobs


def enabled_aggregators():
    return [(key, name) for key, (name, variable) in AGGREGATOR_FEEDS.items()
            if os.getenv(variable, '').strip()]


class JobMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reading = False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.reading = dict(attrs).get('type') == 'application/ld+json'

    def handle_endtag(self, tag):
        if tag == 'script':
            self.reading = False

    def handle_data(self, data):
        if self.reading:
            self.scripts.append(data)


def posting_nodes(value):
    if isinstance(value, list):
        for item in value:
            yield from posting_nodes(item)
    elif isinstance(value, dict):
        types = value.get('@type', [])
        if types == 'JobPosting' or (isinstance(types, list) and 'JobPosting' in types):
            yield value
        if '@graph' in value:
            yield from posting_nodes(value['@graph'])


def structured_job(markup, url, source):
    parser = JobMarkup()
    parser.feed(markup)
    for script in parser.scripts:
        try:
            nodes = json.loads(script)
        except (ValueError, RecursionError):
            continue
        for posting in posting_nodes(nodes):
            expires = posting.get('validThrough')
            if posting_expired(expires):
                return None
            company = posting.get('hiringOrganization')
            locations = posting.get('jobLocation')
            locations = locations if isinstance(locations, list) else [locations]
            places = []
            for location in locations:
                address = location.get('address') if isinstance(location, dict) else None
                if isinstance(address, dict):
                    places.extend(clean(address.get(key), 150)
                                  for key in ('addressLocality', 'addressRegion', 'addressCountry'))
            regions = posting.get('applicantLocationRequirements')
            regions = regions if isinstance(regions, list) else [regions]
            eligibility = ', '.join(clean(region.get('name'), 150) for region in regions
                                    if isinstance(region, dict) and region.get('name'))
            job = normalize({
                'title': posting.get('title'), 'url': url,
                'company_name': company.get('name') if isinstance(company, dict) else '',
                'location': ', '.join(dict.fromkeys(filter(None, places))),
                'description': posting.get('description'),
                'remote': posting.get('jobLocationType') == 'TELECOMMUTE',
                'applicant_regions': eligibility, 'valid_through': expires,
            }, source, '')
            if job:
                return job
    raise ValueError('JobPosting unavailable')


ONJOB = ('OnJob.io', 'https://onjob.io/sitemap-jobs.xml', '/job/')


def employer_settings():
    url = safe_listing_url(os.getenv('CAREEROS_EMPLOYER_SITEMAP_URL', '').strip())
    prefix = os.getenv('CAREEROS_EMPLOYER_JOB_PATH_PREFIX', '').strip()
    if url and re.fullmatch(r'/[a-zA-Z0-9/_-]+/', prefix):
        return urlsplit(url).hostname, url, prefix
    return None


def career_url(value, sitemap_url, prefix):
    if not safe_listing_url(value):
        return False
    parts = urlsplit(value)
    return (parts.hostname == urlsplit(sitemap_url).hostname and not parts.query and not parts.fragment
            and parts.path.startswith(prefix) and len(parts.path) > len(prefix)
            and all(segment not in ('.', '..') for segment in parts.path.split('/'))
            and bool(re.fullmatch(r'/[a-zA-Z0-9/_-]+', parts.path)))


async def fetch_career_job(url, source, client=None):
    try:
        markup = await fetch_content('GET', url, accept='text/html', client=client)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (404, 410):
            return None
        raise
    return structured_job(markup.decode('utf-8', errors='replace'), url, source)


async def career_jobs(source, sitemap_url, prefix, previous=()):
    connection = await asyncio.to_thread(httpx.AsyncClient, timeout=8, follow_redirects=False)
    async with asyncio.timeout(25), connection as client:
        content = await fetch_content('GET', sitemap_url, accept='application/xml', client=client)
        if b'<!DOCTYPE' in content.upper():
            raise ValueError('Unexpected sitemap declaration')
        sitemap = ElementTree.fromstring(content)
        if sitemap.tag.rsplit('}', 1)[-1] != 'urlset':
            raise ValueError('Invalid sitemap')
        links = [item.text for item in sitemap.findall('./{*}url/{*}loc')]
        urls = list(dict.fromkeys(url for url in links if career_url(url, sitemap_url, prefix)))[:CAREER_LIMIT]
        if links and not urls:
            raise ValueError('No valid postings in sitemap')
        jobs = []
        failures = 0
        previous_by_url = {job['url']: job for job in previous}
        for offset in range(0, len(urls), 5):
            batch_urls = urls[offset:offset + 5]
            batch = await asyncio.gather(*(fetch_career_job(url, source, client) for url in batch_urls),
                                         return_exceptions=True)
            for url, job in zip(batch_urls, batch):
                if isinstance(job, (httpx.HTTPError, TimeoutError, ValueError, RecursionError)):
                    failures += 1
                    job = previous_by_url.get(url)
                elif isinstance(job, BaseException):
                    raise job
                if job:
                    jobs.append(job)
        if urls and failures == len(urls):
            raise ValueError('No posting pages could be checked')
        return jobs, bool(failures)


def syndication_settings():
    url = safe_listing_url(os.getenv('CAREEROS_JOB_FEED_URL', '').strip())
    return (urlsplit(url).hostname, url) if url else None


def syndicated_jobs(content, source):
    if b'<!DOCTYPE' in content.upper():
        raise ValueError('Unexpected feed declaration')
    root = ElementTree.fromstring(content)
    kind = root.tag.rsplit('}', 1)[-1]
    if kind == 'rss' and root.find('./{*}channel') is not None:
        entries = root.findall('./{*}channel/{*}item')
    elif kind == 'feed':
        entries = root.findall('./{*}entry')
    else:
        raise ValueError('Invalid job feed')
    jobs = []
    for entry in entries[:500]:
        if kind == 'rss':
            url = entry.findtext('./{*}link')
            description = entry.findtext('./{*}encoded') or entry.findtext('./{*}description')
        else:
            url = next((link.get('href') for link in entry.findall('./{*}link')
                        if link.get('rel', 'alternate') == 'alternate' and link.get('href')), None)
            description = entry.findtext('./{*}content') or entry.findtext('./{*}summary')
        job = normalize({'title': entry.findtext('./{*}title'), 'url': url,
                         'description': description}, source, '')
        if job:
            jobs.append(job)
    if entries and not jobs:
        raise ValueError('No valid postings in nonempty feed')
    return jobs


@router.get('/import')
async def preview_import(url: str = Query(max_length=4096)):
    if not safe_listing_url(url):
        raise HTTPException(422, 'Informe um link HTTPS válido.')
    for snapshot in _cache.values():
        for job in snapshot.jobs:
            if job['url'] == url:
                return {key: value for key, value in job.items() if key != 'search_text'}
    for source, sitemap, prefix in filter(None, (ONJOB, employer_settings())):
        if not career_url(url, sitemap, prefix):
            continue
        try:
            job = await fetch_career_job(url, source)
            if job:
                return {key: value for key, value in job.items() if key != 'search_text'}
        except (httpx.HTTPError, TimeoutError, ValueError):
            pass
    return {'url': url}


def snapshot_path(key):
    return Path(os.getenv('CAREEROS_DISCOVERY_CACHE_DIR') or 'data/discovery') / f'{key}.json'


def read_snapshot(key):
    try:
        data = json.loads(snapshot_path(key).read_bytes())
        jobs, updated = data['jobs'], data['updated_at']
        fields = ('url', 'search_text', 'location', 'title', 'description', 'company', 'source')
        if (not isinstance(jobs, list) or (updated is not None and not isinstance(updated, str))
            or any(not isinstance(job, dict) or not all(isinstance(job.get(field), str) for field in fields)
                   or not isinstance(job.get('remote'), bool) for job in jobs)):
            raise ValueError('Invalid snapshot')
        remaining = 0
        if key in AGGREGATOR_FEEDS and updated:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(updated)).total_seconds()
            remaining = max(0, AGGREGATOR_TTL - max(0, age))
        return Snapshot(time.monotonic() + remaining, jobs, bool(remaining), updated)
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        return Snapshot(0, [], False, None)


def save_snapshot(key, snapshot):
    path = snapshot_path(key)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps({'jobs': snapshot.jobs, 'updated_at': snapshot.updated_at},
                                    ensure_ascii=False).encode('utf-8'))
        temporary.replace(path)
    except OSError:
        pass
    finally:
        if temporary:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)


def gupy_settings():
    url = safe_listing_url(os.getenv('CAREEROS_GUPY_FEED_URL', '').strip())
    token = os.getenv('CAREEROS_GUPY_FEED_TOKEN', '').strip()
    return (url, token) if url and token else None


async def get_feed(key, gupy_url='', gupy_token='', *, force=False):
    async with _locks[key]:
        cached = _cache.get(key)
        if cached is None:
            cached = await asyncio.to_thread(read_snapshot, key)
            _cache[key] = cached
        if not force and time.monotonic() < cached.expires:
            return cached.jobs, cached.available
        try:
            partial = False
            if key in ('careers', 'employer'):
                jobs, partial = await career_jobs(*(ONJOB if key == 'careers' else employer_settings()),
                                                  previous=cached.jobs)
            elif key == 'syndication':
                source, url = syndication_settings()
                content = await fetch_content('GET', url, accept='application/rss+xml, application/atom+xml, application/xml')
                jobs = syndicated_jobs(content, source)
            elif key in AGGREGATOR_FEEDS:
                token = os.getenv(AGGREGATOR_FEEDS[key][1], '').strip()
                if not token:
                    return [], False
                jobs = await aggregator_jobs(key, token)
            elif key == 'gupy':
                rows = await fetch_rows('GET', gupy_url, 'companies', authorization=gupy_token)
                jobs = list(gupy_jobs(rows))
            else:
                source, url, field, company = FEEDS[key]
                rows = await fetch_rows('GET', url, field)
                jobs = [job for row in rows[:500] if (job := normalize(row, source, company))]
                if rows and not jobs:
                    raise ValueError('No valid postings in nonempty feed')
            ttl = CAREER_TTL if key in ('careers', 'employer') and not partial else CACHE_TTL
            if key in AGGREGATOR_FEEDS:
                ttl = AGGREGATOR_TTL
            snapshot = Snapshot(time.monotonic() + ttl, jobs, not partial,
                                datetime.now(timezone.utc).isoformat(), partial)
            await asyncio.to_thread(save_snapshot, key, snapshot)
        except (httpx.HTTPError, TimeoutError, ValueError, ElementTree.ParseError, RecursionError):
            retry = 300 if key in ('careers', 'employer') else 30
            if key in AGGREGATOR_FEEDS:
                retry = AGGREGATOR_TTL
            snapshot = Snapshot(time.monotonic() + retry,
                                cached.jobs, False, cached.updated_at)
        _cache[key] = snapshot
        return snapshot.jobs, snapshot.available


def finish_refresh(key, task):
    if _refresh_tasks.get(key) is task:
        _refresh_tasks.pop(key)
    if not task.cancelled() and task.exception():
        logging.getLogger(__name__).warning('Unexpected job catalog refresh failure for %s', key)


async def search_feed(key, *args):
    cached = _cache.get(key)
    if cached and time.monotonic() < cached.expires:
        return cached.jobs, cached.available, False
    task = _refresh_tasks.get(key)
    if task is None:
        task = asyncio.create_task(get_feed(key, *args))
        _refresh_tasks[key] = task
        task.add_done_callback(lambda done: finish_refresh(key, done))
    if not cached or cached.updated_at is None:
        await asyncio.wait([task], timeout=1.25)
    if task.done() and not task.cancelled() and task.exception() is None:
        jobs, available = task.result()
        return jobs, available, False
    cached = _cache.get(key)
    return (cached.jobs if cached else [], bool(cached and cached.available), not task.done())


async def refresh_catalog():
    while True:
        await asyncio.sleep(CACHE_TTL)
        settings = gupy_settings()
        tasks = [search_feed(key) for key in (*FEEDS, 'careers')]
        tasks.extend(search_feed(key) for key, _ in enabled_aggregators())
        if employer_settings():
            tasks.append(search_feed('employer'))
        if syndication_settings():
            tasks.append(search_feed('syndication'))
        if settings:
            tasks.append(search_feed('gupy', *settings))
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        if any(isinstance(outcome, Exception) for outcome in outcomes):
            logging.getLogger(__name__).warning('Unexpected job catalog refresh failure')


@asynccontextmanager
async def discovery_lifespan(app):
    task = asyncio.create_task(refresh_catalog())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        pending = list(_refresh_tasks.values())
        for refresh in pending:
            refresh.cancel()
        await asyncio.gather(*pending, return_exceptions=True)


async def search_jooble(key, query, location, remote):
    keywords = f'{query} remoto' if remote else query
    location = location or 'Brasil'
    cache_key = (keywords.casefold(), location.casefold(), remote)
    async with asyncio.timeout(12), _jooble_lock:
        cached = _jooble_cache.get(cache_key)
        if cached and time.monotonic() < cached[0]:
            return cached[1]
        try:
            rows = await fetch_rows('POST', f'https://br.jooble.org/api/{quote(key, safe="")}', 'jobs',
                                    json={'keywords': keywords, 'location': location, 'ResultOnPage': 50})
            jobs = []
            for row in rows[:50]:
                if not isinstance(row, dict):
                    continue
                job = normalize({
                    'title': row.get('title'), 'company_name': row.get('company'),
                    'location': row.get('location'), 'url': row.get('link'),
                    'description': row.get('snippet'),
                }, 'Jooble', '')
                if job and (not remote or job['remote']):
                    jobs.append(job)
            result, ttl = (jobs, True), 900
        except (httpx.HTTPError, TimeoutError, ValueError):
            result, ttl = ([], False), 60
        _jooble_cache.pop(cache_key, None)
        if len(_jooble_cache) >= 128:
            del _jooble_cache[next(iter(_jooble_cache))]
        _jooble_cache[cache_key] = (time.monotonic() + ttl, result)
        return result


async def jooble_feed(key, query, location, remote):
    try:
        jobs, available = await search_jooble(key, query, location, remote)
        return jobs, available, False
    except TimeoutError:
        return [], False, False


@router.get('/jobs')
async def discover_jobs(q: str = Query('', max_length=120),
                        location: str = Query('', max_length=100),
                        remote: bool = False,
                        page: int = Query(1, ge=1),
                        title_only: bool = False,
                        radius_km: Annotated[int, Query(ge=0, le=100)] = 0,
                        work_model: Literal['', 'remote', 'hybrid', 'onsite'] = '',
                        level: Literal['', 'intern', 'trainee', 'junior', 'mid', 'senior'] = ''):
    requested_model = work_model or ('remote' if remote else '')
    origin = city_center(folded(location)) if radius_km else None
    if radius_km and origin is None:
        raise HTTPException(422, 'Para buscar por distância, informe uma cidade brasileira reconhecida. Use cidade e UF se houver ambiguidade.')
    names = [feed[0] for feed in FEEDS.values()]
    requests = [search_feed(key) for key in FEEDS]
    keys = [*FEEDS, 'careers']
    names.append(ONJOB[0])
    requests.append(search_feed('careers'))
    for key, source in enabled_aggregators():
        keys.append(key)
        names.append(source)
        requests.append(search_feed(key))
    employer = employer_settings()
    if employer:
        keys.append('employer')
        names.append(employer[0])
        requests.append(search_feed('employer'))
    syndication = syndication_settings()
    if syndication:
        keys.append('syndication')
        names.append(syndication[0])
        requests.append(search_feed('syndication'))
    settings = gupy_settings()
    if settings:
        keys.append('gupy')
        names.append('Gupy')
        requests.append(search_feed('gupy', *settings))
    jooble_key = os.getenv('CAREEROS_JOOBLE_BR_API_KEY', '').strip()
    if jooble_key and q.strip():
        names.append('Jooble')
        requests.append(jooble_feed(jooble_key, q.strip(), location.strip(), requested_model == 'remote'))
    feeds = await asyncio.gather(*requests)
    alternatives = [terms for group in q.split(',') if (terms := search_terms(group))] or [[]]
    where = folded(location.strip())
    if where in ('br', 'brazil'):
        where = 'brasil'
    candidates, sources = [], []
    for index, (name, (jobs, ok, refreshing)) in enumerate(zip(names, feeds)):
        status = {'name': name, 'available': ok}
        if refreshing:
            status['refreshing'] = True
        snapshot = _cache.get(keys[index]) if index < len(keys) else None
        if snapshot and snapshot.updated_at:
            status['updated_at'] = snapshot.updated_at
        if snapshot and snapshot.partial:
            status['partial'] = True
        status['unique_matches'] = 0
        sources.append(status)
        for job in jobs:
            if posting_expired(job.get('valid_through')):
                continue
            model = infer_work_model(job)
            if requested_model and model != requested_model:
                continue
            if level and not LEVELS[level].search(folded(job['title'])):
                continue
            if not radius_km and not matches_location(job, where, model) and (name != 'Jooble' or where == 'brasil'):
                continue
            match = best_match(job, alternatives, title_only=title_only,
                               provider_matched=name == 'Jooble' and not radius_km)
            if match is not None:
                distance = nearest_distance(origin, folded(job['location'])) if origin is not None else None
                if origin is not None and (distance is None or distance > radius_km):
                    continue
                score, scope = match
                candidates.append((score, distance, status, job, model, scope))
    results, seen = [], set()
    for _, distance, status, job, model, scope in sorted(
        candidates, key=lambda item: (-item[0], item[1] or 0, -len(item[3]['description']))
    ):
        identities = tuple(duplicate_keys(job))
        if seen.intersection(identities):
            continue
        seen.update(identities)
        status['unique_matches'] += 1
        results.append({
            **{key: value for key, value in job.items() if key != 'search_text'},
            'work_model': model, 'remote': model == 'remote',
            'match_scope': scope,
            **({'distance_km': round(distance, 1)} if distance is not None else {}),
            'unconfirmed': not status['available'] and bool(status.get('updated_at')),
        })
    page = min(page, max(1, (len(results) + PAGE_SIZE - 1) // PAGE_SIZE))
    offset = (page - 1) * PAGE_SIZE
    # Older tabs still call portals.map() on this response.
    return {'jobs': results[offset:offset + PAGE_SIZE], 'total': len(results), 'portals': [],
            'page': page, 'page_size': PAGE_SIZE, 'sources': sources}
