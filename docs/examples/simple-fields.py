import sys
import json
import random

json.dump({
    str(count): {
        "id": count,
        "foo": random.randint(15, 50),
        "bar": random.choice([
            "MAN", "LON", "LHR", "ABZ", "AMS", "AUS", "BCN",
            "BER", "BHX", "BRU", "CHI", "ORK", "DAL", "EDI",
        ]),
    }
    for count in range(200)
}, sys.stdout)
