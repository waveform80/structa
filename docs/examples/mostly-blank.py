import sys
import json
import random

json.dump([
    '' if random.random() < 0.7 else str(random.randint(0, 100))
    for i in range(10000)
], sys.stdout)
