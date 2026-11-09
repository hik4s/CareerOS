"""Public company job boards on fixed ATS hosts. No API keys or arbitrary URLs."""
import json
from pathlib import Path
import re

import httpx

PAGE_SIZE = 100
MAX_PAGES = 10
MAX_LISTINGS = PAGE_SIZE * MAX_PAGES


def validate_sources(rows):
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValueError('Expected at most 100 public sources')
    sources = {}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'provider', 'board', 'name'}
                or row['provider'] not in ('greenhouse', 'lever', 'ashby')
                or not isinstance(row['board'], str)
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', row['board'])
                or not isinstance(row['name'], str) or not 1 <= len(row['name'].strip()) <= 100):
            raise ValueError('Invalid public source')
        key = row['provider'] + '_' + row['board'].lower()
        if key in sources:
            raise ValueError('Duplicate public source')
        sources[key] = row
    return sources


SOURCES = validate_sources(json.loads(Path(__file__).with_name('job_sources.json').read_text(encoding='utf-8')))


def address_text(address):
    if not isinstance(address, dict):
        return ''
    address = address.get('postalAddress') or address
    if not isinstance(address, dict):
        return ''
    values = [address.get(key) for key in ('addressLocality', 'addressRegion', 'addressCountry')]
    return ', '.join('Brasil' if value.upper() in ('BR', 'BRA') else value
                     for value in values if isinstance(value, str) and value)


def ashby_posting(row, company):
    def paired_location(location, address):
        return ', '.join(value for value in (location, address_text(address)) if isinstance(value, str) and value)
    locations = [paired_location(row.get('location'), row.get('address'))]
    secondary = row.get('secondaryLocations')
    if isinstance(secondary, list):
        for location in secondary[:50]:
            if isinstance(location, dict):
                locations.append(paired_location(location.get('location'), location.get('address')))
    workplace = {'Remote':'remote', 'Hybrid':'hybrid', 'OnSite':'onsite'}.get(str(row.get('workplaceType')), '')
    return {'title':row.get('title'), 'company_name':company,
            'location':'; '.join(dict.fromkeys(value for value in locations if isinstance(value, str) and value)),
            'url':row.get('jobUrl'), 'apply_url':row.get('applyUrl'),
            'description':row.get('descriptionPlain') or row.get('descriptionHtml'),
            'remote':workplace == 'remote', 'work_model':workplace,
            'employment_type':row.get('employmentType'), 'published_at':row.get('publishedAt')}


def lever_posting(row, company):
    categories = row.get('categories') if isinstance(row.get('categories'), dict) else {}
    parts = [row.get('openingPlain'), row.get('descriptionPlain') or row.get('description'), row.get('additionalPlain')]
    if isinstance(row.get('lists'), list):
        parts.extend(str(section.get('text', '')) + '\n' + str(section.get('content', ''))
                     for section in row['lists'][:30] if isinstance(section, dict))
    return {'title':row.get('text'), 'company_name':company, 'location':categories.get('location'),
            'country_code':row.get('country'), 'url':row.get('hostedUrl'), 'apply_url':row.get('applyUrl'),
            'description':'\n'.join(part for part in parts if isinstance(part, str)),
            'work_model':{'remote':'remote','hybrid':'hybrid','on-site':'onsite'}.get(str(row.get('workplaceType')), ''),
            'employment_type':categories.get('commitment')}


async def collect_catalog(source, fetch, normalize):
    provider, board, name = source['provider'], source['board'], source['name']
    if provider in ('ashby', 'greenhouse'):
        url = (f'https://api.ashbyhq.com/posting-api/job-board/{board}' if provider == 'ashby'
               else f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true')
        # Descriptions for a whole Greenhouse board can exceed the generic 5 MiB feed budget.
        payload = json.loads(await fetch('GET', url, accept='application/json',
                                         **({'max_bytes':10 * 1024 * 1024} if provider == 'greenhouse' else {})))
        rows = payload.get('jobs') if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError('Invalid public catalog')
        jobs = []
        for row in rows[:MAX_LISTINGS]:
            if not isinstance(row, dict) or provider == 'ashby' and row.get('isListed') is not True:
                continue
            job = normalize(ashby_posting(row, name), name + ' · Ashby', '') if provider == 'ashby' else normalize(row, name, name)
            if job:
                jobs.append(job)
        return jobs, len(rows) > MAX_LISTINGS
    if provider != 'lever':
        raise ValueError('Unsupported provider')
    jobs, seen = [], set()
    for page in range(MAX_PAGES):
        try:
            rows = json.loads(await fetch('GET', f'https://api.lever.co/v0/postings/{board}',
                                         accept='application/json', params={'mode':'json','limit':PAGE_SIZE,'skip':page * PAGE_SIZE}))
            if not isinstance(rows, list):
                raise ValueError('Invalid public catalog')
        except (httpx.HTTPError, TimeoutError, ValueError):
            if jobs:
                return jobs, True
            raise
        added = 0
        for row in rows[:PAGE_SIZE]:
            if not isinstance(row, dict):
                continue
            job = normalize(lever_posting(row, name), name + ' · Lever', '')
            if job and job['url'] not in seen:
                seen.add(job['url'])
                jobs.append(job)
                added += 1
        if rows and not added:
            return jobs, True
        if len(rows) < PAGE_SIZE:
            return jobs, False
    return jobs, True
