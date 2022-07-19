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

    output_results_list = []

    for usi in all_usi:
        results_dict = query_usi(usi, database_name)
        results_df = pd.DataFrame(results_dict["results"])

        #if masst_type == "microbemasst":
            # Lets do additionally processing
        #    print("MICROBEMASST")

        results_df["query_usi"] = usi
        output_results_list.append(results_df)
        
    output_results_df = pd.concat(output_results_list)
    output_results_df.to_csv(output_file, index=False, sep="\t")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fast MASST Client')
    parser.add_argument('input_file', help='file to query with USIs')
    parser.add_argument('output_file', help='output_file')
    parser.add_argument('--masst_type', help='Type of MASST to give youresults: gnpsdata, microbemasst', default="masst")
    args = parser.parse_args()

    query_all(pd.read_csv(args.input_file), args.masst_type, args.output_file)