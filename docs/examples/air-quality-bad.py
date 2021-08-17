import sys
import json
import random
import datetime as dt
from scipy.stats import skewnorm

readings = {
    # stat:  (min, max),
    'O3':    (0, 50),
    'NO':    (0, 200),
    'NO2':   (0, 100),
    'PM10':  (0, 100),
    'PM2.5': (0, 100),
}

locations = {
    # location: {stat: (skew, scale), ...}
    'Mancford Peccadillo': {
        'O3':    (0,  1),
        'NO':    (5,  1),
        'NO2':   (0,  1),
        'PM10':  (10, 3),
        'PM2.5': (10, 1),
    },
    'Mancford Shartson': {
        'O3':    (-10, 1),
        'NO':    (10,  1),
        'NO2':   (0,   1),
    },
    'Salport': {
        'NO':    (10,  1),
        'NO2':   (-10, 1/2),
        'PM10':  (5,   1/2),
        'PM2.5': (5,   1/2),
    },
    'Prestchester': {
        'O3':    (1,  1),
        'NO':    (5,  1/2),
        'NO2':   (0,  1),
        'PM10':  (5,  1/2),
        'PM2.5': (10, 1/2),
    },
    'Blackshire': {
        'O3':    (-10, 1),
        'NO':    (50,  1/2),
        'NO2':   (10,  1/2),
        'PM10':  (10,  1/2),
        'PM2.5': (10,  1/2),
    },
    'St. Wigpools': {
        'O3':    (0,  1),
        'NO':    (10, 1),
        'NO2':   (5,  3/4),
        'PM10':  (5,  1/2),
        'PM2.5': (5,  1/2),
    },
}

def skewfunc(min, max, a=0, scale=1):
    s = skewnorm(a)
    real_min = s.ppf(0.0001)
    real_max = s.ppf(0.9999)
    real_range = real_max - real_min
    res_range = max - min
    def skewrand():
        return min + res_range * scale * (s.rvs() - real_min) / real_range
    return skewrand

generators = {
    location: {
        reading: skewfunc(read_min, read_max, skew, scale)
        for reading, params in loc_readings.items()
        for read_min, read_max in (readings[reading],)
        for skew, scale in (params,)
    }
    for location, loc_readings in locations.items()
}

timestamps = [
    dt.datetime(2020, 1, 1) + dt.timedelta(hours=n)
    for n in range(10000)
]

data = {
    location: {
        'euid': 'GB{:04d}A'.format(random.randint(200, 2000)),
        'ukid': 'UKA{:05d}'.format(random.randint(100, 800)),
        'lat': random.random() + 53.0,
        'long': random.random() - 3.0,
        'alt': random.randint(5, 100),
        'readings': {
            reading: {
                timestamp.isoformat(): loc_gen()
                for timestamp in timestamps
            }
            for reading, loc_gen in loc_gens.items()
        }
    }
    for location, loc_gens in generators.items()
}

for location in data:
    if random.random() < 0.5:
        reading = random.choice(list(data[location]['readings']))
        date = random.choice(list(data[location]['readings'][reading]))
        value = data[location]['readings'][reading].pop(date)
        data[location]['readings'][reading]['2020-02-31T12:34:56'] = value

json.dump(data, sys.stdout)
