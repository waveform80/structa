import sys
import json
import random

airports = {
    "MAN", "LON", "LHR", "ABZ", "AMS", "AUS", "BCN",
    "BER", "BHX", "BRU", "CHI", "ORK", "DAL", "EDI",
}

facilities = [
    "WiFi", "Shopping", "Conferences", "Chapel", "Parking",
    "Lounge", "Spotters Area", "Taxi Rank", "Train Station",
    "Tram Stop", "Bus Station", "Duty Free",
]

data = {
    airport: {
        "code": airport,
        "facilities": random.sample(
            facilities, random.randint(3, len(facilities))),
        "terminals": random.randint(1, 4),
        "movements": random.randint(10000, 300000),
        "passengers": random.randint(1000000, 30000000),
        "cargo": random.randint(10000, 1000000),
    }
    for airport in airports
}

for entry in data.values():
    # Exclude reporting terminals if the airport only has one
    if entry['terminals'] == 1:
        del entry['terminals']
    # Exclude some other stats semi-randomly
    if random.random() > 0.7:
        del entry['movements']
    if random.random() > 0.9:
        del entry['cargo']

json.dump(data, sys.stdout)
