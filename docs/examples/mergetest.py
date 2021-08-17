import apt
import json
import random

cache = apt.cache.Cache()
data = {
    'U{num:04d}-{sub:02d}'.format(num=num, sub=sub): {
        'id': 'U{num:04d}-{sub:02d}'.format(num=num, sub=sub),
        'releases': {
            release: {
                name: {
                    'version': package.versions[0].version,
                    'description': package.versions[0].description,
                    'metavars': {
                        metavar: {
                            num: list(range(num))
                            for num in [
                                random.randint(1, 100)
                                for i in range(random.randint(2, 10))
                            ]
                        }
                        for metavar in random.choices(
                            ('foo', 'bar', 'baz', 'quux', 'xyzzy'),
                            weights=(5, 5, 5, 4, 2), k=random.randint(2, 5))
                    }
                }
                for name in (random.choice(cache.keys()),)
                for package in (cache[name],)
            }
            for release in random.choices(
                ('precise', 'trusty', 'xenial', 'bionic', 'focal', 'groovy'),
                weights=(3, 3, 4, 4, 5, 6), k=random.randint(2, 6))
        }
    }
    for num in range(1000)
    for sub in range(random.randint(1, 15))
}

with open('mergetest.json', 'w') as fp:
    json.dump(data, fp)
