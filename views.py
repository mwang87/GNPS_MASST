# views.py
from flask import abort, render_template, request, redirect, make_response
import uuid
import json
import zipfile
import io

from app import app
import requests
import os

ALLOWED_EXTENSIONS = set(['mgf', 'mzxml', 'mzml'])

@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    return '{"status" : "up"}'

@app.route('/', methods=['GET'])
def homepage():
    response = make_response(render_template('dashboard.html'))
    response.set_cookie('username', str(uuid.uuid4()))
    return response

@app.route('/foodmasst', methods=['GET'])
def foodmasst():
    response = make_response(render_template('foodmasst.html'))
    response.set_cookie('username', str(uuid.uuid4()))
    return response

@app.route('/submit', methods=['POST'])
@app.route('/masst/submit', methods=['POST'])
def submit():
    TEST_MODE = False
    if "test" in request.form:
        TEST_MODE = True

    try:
        if len(request.form["peaks"]) < 2:
            raise Exception
    except:
        abort(400, "Peaks not entered")
    try:
        if len(request.form["precursormz"]) < 1:
            raise Exception
    except:
        abort(400, "Precursor not entered")

    if len(request.form["peaks"]) > 50000:
        abort(400, "Peaks are too long, must be less than 20K characters")

    # using environment variables
    username = os.environ.get('gnpsusername', 'defaultusername')
    password = os.environ.get('gnpspassword', 'defaultusername')
    email = "nobody@ucsd.edu"
    dataset_filter = request.form["database"]

    analog_search = "0"
    if request.form["analogsearch"] == "Yes":
        analog_search = "1"

    if len(request.form.get("email", "")) > 2:
        email = request.form["email"]

    if len(request.form["login"]) > 2 and len(request.form["password"]) > 2:
        username = request.form["login"]
        password = request.form["password"]

    description = request.values.get("description", "GNPS MASST from Webform")
    if len(description) == 0:
        description = "GNPS MASST From Webform "

    if TEST_MODE:
        return "Test Passed"

    task_id = launch_GNPS_workflow(description, username, password, email, request.form["pmtolerance"], request.form["fragmenttolerance"], request.form["cosinescore"], request.form["matchedpeaks"], analog_search, request.form["precursormz"], request.form["peaks"], dataset_filter)

    if task_id is None or len(task_id) != 32:
        abort(500, "Task launch at GNPS Failed")

    return redirect("https://gnps.ucsd.edu/ProteoSAFe/status.jsp?task=%s" % (task_id))


def launch_GNPS_workflow(job_description, username, password, email, pm_tolerance, fragment_tolerance, score_threshold, matched_peaks, analog_search, precursor_mz, peaks_string, dataset_filter):
    invokeParameters = {}
    invokeParameters["workflow"] = "SEARCH_SINGLE_SPECTRUM"
    invokeParameters["workflow_version"] = "release_29"
    invokeParameters["protocol"] = "None"
    invokeParameters["desc"] = job_description
    invokeParameters["library_on_server"] = "d.speclibs;"

    #Search Parameters
    invokeParameters["tolerance.PM_tolerance"] = pm_tolerance
    invokeParameters["tolerance.Ion_tolerance"] = fragment_tolerance

    invokeParameters["ANALOG_SEARCH"] = analog_search
    invokeParameters["FIND_MATCHES_IN_PUBLIC_DATA"] = "1"
    invokeParameters["MAX_SHIFT_MASS"] = "100"
    invokeParameters["MIN_MATCHED_PEAKS"] = matched_peaks
    invokeParameters["SCORE_THRESHOLD"] = score_threshold
    invokeParameters["SEARCH_LIBQUALITY"] = "3"
    invokeParameters["SEARCH_RAW"] = "0"
    invokeParameters["TOP_K_RESULTS"] = "1"
    invokeParameters["DATABASES"] = dataset_filter

    #Filter Parameters
    invokeParameters["FILTER_LIBRARY"] = "1"
    invokeParameters["FILTER_PRECURSOR_WINDOW"] = "1"
    invokeParameters["FILTER_SNR_PEAK_INT"] = "0"
    invokeParameters["FILTER_STDDEV_PEAK_INT"] = "0"
    invokeParameters["MIN_PEAK_INT"] = "0"
    invokeParameters["WINDOW_FILTER"] = "1"

    #Spectrum
    invokeParameters["precursor_mz"] = precursor_mz
    invokeParameters["spectrum_string"] = peaks_string

    #Post Processing
    invokeParameters["CREATE_NETWORK"] = "No"

    invokeParameters["email"] = email
    invokeParameters["uuid"] = "1DCE40F7-1211-0001-979D-15DAB2D0B500"

    task_id = invoke_workflow("gnps.ucsd.edu", invokeParameters, username, password)

    return task_id

def invoke_workflow(base_url, parameters, login, password):
    username = login
    password = password

    s = requests.Session()

    payload = {
        'user' : username,
        'password' : password,
        'login' : 'Sign in'
    }

    r = s.post('https://' + base_url + '/ProteoSAFe/user/login.jsp', data=payload, verify=False)
    r = s.post('https://' + base_url + '/ProteoSAFe/InvokeTools', data=parameters, verify=False)
    task_id = r.text

    import sys
    print(r.text, file=sys.stderr, flush=True)

    if len(task_id) > 4 and len(task_id) < 60:
        print("Launched Task: : " + r.text)
        return task_id
    else:
        print(task_id)
        return None


# Display some results
@app.route('/foodmasst/result', methods=['GET'])
def foodmasstresult():
    task = request.values.get("task")

    # Checking if the task is the proper type
    url = "https://gnps.ucsd.edu/ProteoSAFe/status_json.jsp?task={}".format(task)
    r = requests.get(url)

    if r.status_code != 200:
        return "Error: Task not found"
    
    response = r.json()

    if response["workflow"] != "SEARCH_SINGLE_SPECTRUM":
        return "Error: Task not of type SEARCH_SINGLE_SPECTRUM"

    # Getting the actual html and displaying it
    download_url = "https://proteomics2.ucsd.edu/ProteoSAFe/DownloadResult?task={}&view=download_food_tree_html".format(task)
    response = requests.post(download_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as thezip:
        for zipinfo in thezip.infolist():
            with thezip.open(zipinfo) as thefile:
                if "main.html" in thefile.name:
                    return thefile.read()

    return "Error: Not Found"

# Display some results
@app.route('/personalcaremasst/result', methods=['GET'])
def personalcaremasstresult():
    task = request.values.get("task")

    # Checking if the task is the proper type
    url = "https://gnps.ucsd.edu/ProteoSAFe/status_json.jsp?task={}".format(task)
    r = requests.get(url)

    if r.status_code != 200:
        return "Error: Task not found"
    
    response = r.json()

    if response["workflow"] != "SEARCH_SINGLE_SPECTRUM":
        return "Error: Task not of type SEARCH_SINGLE_SPECTRUM"

    # Getting the actual html and displaying it
    download_url = "https://proteomics2.ucsd.edu/ProteoSAFe/DownloadResult?task={}&view=download_personalcare_tree_html".format(task)
    response = requests.post(download_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as thezip:
        for zipinfo in thezip.infolist():
            with thezip.open(zipinfo) as thefile:
                if "main.html" in thefile.name:
                    return thefile.read()

    return "Error: Not Found"