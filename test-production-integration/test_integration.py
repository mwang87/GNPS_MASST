import requests

PRODUCTION_URL = "masst.ucsd.edu"

def test_production():
    url = f"https://{PRODUCTION_URL}/heartbeat"
    r = requests.get(url)
    r.raise_for_status()


def test_dry_submit():
    parameters = {}
    parameters["test"] = "1"
    parameters["peaks"] = """463.381	43.591
693.498	119.206
694.496	42.985
707.494	508.18
708.512	197.117
709.558	18.679
723.4	43.831
800.494	476.556
801.518	196.451
802.496	95.972
814.513	86.182
931.574	50.803
972.868	14.634
1016.62	66.809
1017.58	16.578
1025.57	22.426"""
    parameters["precursormz"] = "1044.66"
    parameters["database"] = "ALL"
    parameters["analogsearch"] = "No"
    parameters["pmtolerance"] = "2.0"
    parameters["fragmenttolerance"] = "0.5"
    parameters["cosinescore"] = "0.7"
    parameters["matchedpeaks"] = "6"
    
    url = f"https://{PRODUCTION_URL}/submit"
    r = requests.post(url, data=parameters)
    r.raise_for_status()
    
    
    