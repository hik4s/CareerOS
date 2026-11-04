"""City-center distances using the Brazilian extract of GeoNames cities15000."""
import csv
from collections import defaultdict
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
import re


@lru_cache(maxsize=1)
def city_index():
    cities = defaultdict(list)
    with Path(__file__).with_name('brazil_cities.csv').open(encoding='utf-8', newline='') as file:
        for city, state, state_name, lat, lon in csv.reader(file):
            cities[city].append((state, state_name, (float(lat), float(lon))))
    return cities


@lru_cache(maxsize=4096)
def city_center(location):
    """Resolve a folded city string, optionally qualified by Brazilian state or country."""
    location = re.sub(r'\s*\((?:hybrid|hibrid[oa]|remote|remot[oa]|on-site|presencial)\)\s*$', '', location)
    parts = re.split(r'\s*,\s*|\s+-\s+', location.strip())
    qualifiers = set(parts[1:]) - {'br', 'brasil', 'brazil', 'remote', 'remoto',
                                   'hybrid', 'hibrido', 'presencial', 'on-site'}
    matches = [point for state, name, point in city_index().get(parts[0], ())
               if qualifiers <= {state, name}]
    return matches[0] if len(matches) == 1 else None


def distance_km(origin, destination):
    lat1, lon1 = map(radians, origin)
    lat2, lon2 = map(radians, destination)
    haversine = sin((lat2 - lat1) / 2)**2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2)**2
    return 12742 * asin(sqrt(min(1, haversine)))


def nearest_distance(origin, location):
    points = (city_center(part) for part in re.split(r'\s*[;|]\s*', location))
    return min((distance_km(origin, point) for point in points if point is not None), default=None)
