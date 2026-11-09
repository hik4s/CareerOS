"""Measure only the public company catalogs; no account or paid-provider keys used."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.cloud import discovery

QUERIES = ('estagio', 'estagio python', 'desenvolvedor python', 'frontend', 'backend', 'dados', 'suporte tecnico')


def unique(jobs):
    seen, result = set(), []
    for job in jobs:
        identities = set(discovery.duplicate_keys(job))
        if not seen.intersection(identities):
            seen.update(identities)
            result.append(job)
    return result


async def collect():
    async def source(key):
        jobs, available = await discovery.get_feed(key, force=True)
        return {'key':key, 'available':available, 'partial':discovery._cache[key].partial, 'jobs':jobs}
    return await asyncio.gather(*(source(key) for key in (*discovery.FEEDS, *discovery.PUBLIC_SOURCES)))


def summarize(feeds):
    jobs = [job for feed in feeds for job in feed['jobs']]
    brazil = unique([job for job in jobs if discovery.matches_location(job, 'brasil', discovery.infer_work_model(job))
                     and not discovery.posting_expired(job.get('valid_through'))])
    return {
        'collected_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Public catalogs only; all job families and seniority levels; Brazil inferred from provider metadata/location',
        'sources':len(feeds), 'available':sum(feed['available'] for feed in feeds),
        'raw_listings':len(jobs), 'brazil_unique':len(brazil),
        'queries':[{'q':query, 'matches':sum(bool(discovery.best_match(job, [discovery.search_terms(query)],
                    title_only=False, provider_matched=False)) for job in brazil)} for query in QUERIES],
        'per_source':[{key:value for key,value in feed.items() if key != 'jobs'} | {'listings':len(feed['jobs'])} for feed in feeds],
    }


async def main(output):
    started = time.monotonic()
    result = summarize(await collect())
    result['seconds'] = round(time.monotonic() - started, 2)
    serialized = json.dumps(result, ensure_ascii=True, indent=2)
    if output:
        Path(output).write_text(serialized + '\n', encoding='utf-8')
    print(serialized)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='Optional JSON report file')
    asyncio.run(main(parser.parse_args().output))
