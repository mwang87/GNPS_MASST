from celery import Celery
import glob
import sys
import os
import uuid
import requests
import requests_cache
import pandas as pd

# Requests cache for massive information, that expires after 24 hours
requests_cache.install_cache('temp/requests_cache', expire_after=84600)

# Global data for datasets
all_gnps_datasets = requests.get("https://massive.ucsd.edu/ProteoSAFe/QueryDatasets?pageSize=3000&offset=0&query={%22title_input%22:%22GNPS%22}").json()
datasets_df = pd.DataFrame(all_gnps_datasets["row_data"])


celery_instance = Celery('tasks', backend='redis://masst-redis', broker='pyamqp://guest@masst-rabbitmq//', )

@celery_instance.task(time_limit=60)
def task_computeheartbeat():
    print("UP", file=sys.stderr, flush=True)
    return "Up"

@celery_instance.task(time_limit=60)
def task_searchmasst(usi, analog_search):
    print(usi, file=sys.stderr, flush=True)

    spectrum_json = requests.get("https://metabolomics-usi.ucsd.edu/json/?usi1={}".format(usi)).json()

    random_string = str(uuid.uuid4()).replace("-", "")
    temp_query_mgf = os.path.join("temp", "{}.mgf".format(random_string))
    temp_results_tsv = os.path.join("temp", "{}.tsv".format(random_string))

    with open(temp_query_mgf, "w") as o:
        o.write("BEGIN IONS\n")
        o.write("SEQ=*..*\n")
        o.write("PEPMASS={}\n".format(spectrum_json["precursor_mz"]))
        for peak in spectrum_json["peaks"]:
            o.write("{} {}\n".format(peak[0], peak[1]))
        o.write("END IONS\n")

    if analog_search == "Yes":
        cmd = "./bin/search {} -a -l ./bin/library -o {}".format(temp_query_mgf, temp_results_tsv)
    else:
        cmd = "./bin/search {} -l ./bin/library -o {}".format(temp_query_mgf, temp_results_tsv)
        
    os.system(cmd)

    results_df = pd.read_csv(temp_results_tsv, sep="\t")
    results_df = results_df.drop(["Query File", "Query Scan"], axis=1)

    # Adding dataset information
    results_df["Accession"] = results_df["DB File"].apply(lambda x: os.path.basename(x).split("_")[0])

    merged_df = results_df.merge(datasets_df, how="left", left_on="Accession", right_on="dataset")
    results_df = merged_df[["Accession", "title", "DB Scan", "Score", "Matched Peaks", "M/Z Delta"]]
    results_df["title"] = results_df["title"].apply(lambda x: x[:40])

    return results_df.to_dict(orient="records")


# celery_instance.conf.beat_schedule = {
#     "cleanup": {
#         "task": "tasks._task_cleanup",
#         "schedule": 3600
#     }
# }


celery_instance.conf.task_routes = {
    'tasks.task_computeheartbeat': {'queue': 'worker'},
    'tasks.task_searchmasst': {'queue': 'worker'},
}