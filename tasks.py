from celery import Celery
import glob
import sys
import os
import uuid
import requests
import pandas as pd

celery_instance = Celery('tasks', backend='redis://masst-redis', broker='pyamqp://guest@masst-rabbitmq//', )

@celery_instance.task(time_limit=60)
def task_computeheartbeat():
    print("UP", file=sys.stderr, flush=True)
    return "Up"

@celery_instance.task(time_limit=60)
def task_searchmasst(usi, analog_search):
    print(usi, file=sys.stderr, flush=True)

    spectrum_json = requests.get("https://metabolomics-usi.ucsd.edu/json/?usi={}".format(usi)).json()

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