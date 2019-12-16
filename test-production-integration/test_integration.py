import requests

PRODUCTION_URL = "masst.ucsd.edu"

def test_production():
    url = f"https://{PRODUCTION_URL}/heartbeat"
    r = requests.get(url)
    r.raise_for_status()