"""Search published feeds and build links to external job portals."""
import asyncio
import html
import json
import re
import time
import unicodedata
from urllib.parse import quote, urlencode, urlsplit

import httpx
from fastapi import APIRouter, Depends, Query

from .auth import require_user

router = APIRouter(prefix='/api/discovery', dependencies=[Depends(require_user)])
FEEDS = {
    'quintoandar': ('Grupo QuintoAndar', 'https://boards-api.greenhouse.io/v1/boards/quintoandar/jobs', 'jobs', 'Grupo QuintoAndar'),
    'brex': ('Brex', 'https://boards-api.greenhouse.io/v1/boards/brex/jobs', 'jobs', 'Brex'),
    'arbeitnow': ('Arbeitnow', 'https://www.arbeitnow.com/api/job-board-api', 'data', ''),
}
CACHE_TTL = 300
MAX_FEED_BYTES = 5 * 1024 * 1024
_cache = {}
_locks = {key: asyncio.Lock() for key in FEEDS}


def clean(value, limit):
    if not isinstance(value, str):
        return ''
    return ' '.join(re.sub(r'<[^>]*>', ' ', html.unescape(value)).split())[:limit]


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(c))


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
    return {
        'title': title, 'company': company or clean(row.get('company_name'), 500),
        'location': location, 'url': url, 'source': source, 'remote': remote,
        'description': clean(row.get('description'), 1500), 'keywords': keywords,
    }


async def get_feed(key):
    async with _locks[key]:
        cached = _cache.get(key)
        now = time.monotonic()
        if cached and now < cached[0]:
            return cached[1]
        source, url, field, company = FEEDS[key]
        try:
            async with asyncio.timeout(10), httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                async with client.stream('GET', url, headers={'Accept': 'application/json'}) as response:
                    response.raise_for_status()
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(content) + len(chunk) > MAX_FEED_BYTES:
                            raise ValueError('Feed too large')
                        content.extend(chunk)
            payload = json.loads(content)
            rows = payload.get(field) if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise ValueError('Invalid feed')
            jobs = [job for row in rows[:500] if (job := normalize(row, source, company))]
            result = (jobs, True)
            ttl = CACHE_TTL
        except (httpx.HTTPError, TimeoutError, ValueError):
            result = ([], False)
            ttl = 30
        _cache[key] = (time.monotonic() + ttl, result)
        return result


def portal_links(term, location, remote):
    def link(base, **params):
        return base + '?' + urlencode({k: v for k, v in params.items() if v})

    query = ' '.join(filter(None, (term, 'remoto' if remote else '')))
    slug = '-'.join(re.findall(r'\w+', folded(query)))
    return [
        {'name': 'LinkedIn', 'url': link('https://www.linkedin.com/jobs/search/', keywords=term, location=location or 'Brasil', f_WT='2' if remote else '')},
        {'name': 'Gupy', 'url': 'https://portal.gupy.io/job-search/term%3D' + quote(query, safe='') if query else 'https://portal.gupy.io/vagas'},
        {'name': 'InfoJobs', 'url': ('https://www.infojobs.com.br/vagas-de-emprego-' + quote(slug, safe='-') + '.aspx') if slug else 'https://www.infojobs.com.br/vagas-de-emprego.aspx'},
        {'name': 'Indeed', 'url': link('https://br.indeed.com/jobs', q=query, l=location)},
        {'name': 'Catho', 'url': 'https://www.catho.com.br/vagas/'},
        {'name': 'Vagas.com.br', 'url': 'https://www.vagas.com.br/'},
        {'name': 'Glassdoor', 'url': 'https://www.glassdoor.com.br/Vaga/index.htm'},
        {'name': 'Empregos.com.br', 'url': 'https://www.empregos.com.br/'},
        {'name': 'Trabalha Brasil', 'url': 'https://www.trabalhabrasil.com.br/vagas-de-emprego'},
        {'name': 'Jooble', 'url': 'https://br.jooble.org/'},
        {'name': 'Trampos', 'url': 'https://trampos.co/oportunidades'},
        {'name': 'CIEE', 'url': 'https://portal.ciee.org.br/quero-uma-vaga/'},
        {'name': 'Nube', 'url': 'https://www.nube.com.br/vagas'},
        {'name': 'SINE', 'url': 'https://www.gov.br/trabalho-e-emprego/pt-br/servicos/trabalhador/intermediacao-de-mao-de-obra'},
    ]


@router.get('/jobs')
async def discover_jobs(q: str = Query('', max_length=120),
                        location: str = Query('', max_length=100),
                        remote: bool = False):
    feeds = await asyncio.gather(*(get_feed(key) for key in FEEDS))
    words = folded(q).split()
    where = re.sub(r'\bbrazil\b', 'brasil', folded(location.strip()))
    results, seen, sources = [], set(), []
    for key, (jobs, ok) in zip(FEEDS, feeds):
        sources.append({'name': FEEDS[key][0], 'available': ok})
        for job in jobs:
            haystack = folded(' '.join(job[field] for field in ('title', 'company', 'keywords')))
            if (not all(word in haystack for word in words) or
                (where and where not in re.sub(r'\bbrazil\b', 'brasil', folded(job['location']))) or
                (remote and not job['remote']) or job['url'] in seen):
                continue
            seen.add(job['url'])
            results.append({k: v for k, v in job.items() if k != 'keywords'})
    return {'jobs': results[:50], 'total': len(results), 'sources': sources,
            'portals': portal_links(q.strip(), location.strip(), remote)}
