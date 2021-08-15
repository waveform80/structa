import sys
import json
import random

json.dump({
    str(flight_id): {
        "flight_id": flight_id,
        "passengers": random.randint(50, 200),
        "from": random.choice([
            "MAN", "LON", "LHR", "ABZ", "AMS", "AUS", "BCN",
            "BER", "BHX", "BRU", "CHI", "ORK", "DAL", "EDI",
        ]),
    }
    for flight_id in range(200)
}, sys.stdout)
