import pandas as pd
import argparse
import requests
import requests_cache
requests_cache.install_cache('demo_cache')

def query_usi(usi, database, analog=False, precursor_mz_tol=0.02, fragment_mz_tol=0.02, min_cos=0.7):
    URL = "https://fastlibrarysearch.ucsd.edu/search"

    params = {
        "usi": usi,
        "library": database,
        "analog": "Yes" if analog else "No",
        "pm_tolerance": precursor_mz_tol,
        "fragment_tolerance": fragment_mz_tol,
        "cosine_threshold": min_cos,
    }

    r = requests.get(URL, params=params, timeout=50)

    return r.json()

def query_all(usi_df, masst_type, output_file):
    print(usi_df)

    database_name = "gnpsdata_index"
    all_usi = list(usi_df["usi"])

    for usi in all_usi:
        results_dict = query_usi(usi, database_name)

        print(len(results_dict["results"]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MassT Client')
    parser.add_argument('input_file', help='file to query')
    parser.add_argument('output_file', help='output_file')
    parser.add_argument('--masst_type', help='Type of MASST to give youresults: gnpsdata, microbemasst', default="masst")
    args = parser.parse_args()

    query_all(pd.read_csv(args.input_file), args.masst_type, args.output_file)