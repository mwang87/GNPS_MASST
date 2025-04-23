# -*- coding: utf-8 -*-
import dash
import werkzeug.utils
from dash import dcc, html, ctx
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import os
import urllib
import urllib.parse
import json
from flask import Flask, send_file, request
import requests

from flask_caching import Cache
from app import app

dash_app = dash.Dash(
    name="dashinterface",
    server=app,
    url_base_pathname="/plantmasst/",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)

dash_app.title = 'plantMASST'

cache = Cache(dash_app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'temp/flask-cache',
    'CACHE_DEFAULT_TIMEOUT': 0,
    'CACHE_THRESHOLD': 1000000
})


dash_app.index_string = """<!DOCTYPE html>
<html>
    <head>
        <!-- Umami Analytics -->
        <script async defer data-website-id="a2c04f32-dca9-4fcd-b3f3-0f9aeeb2d74e" src="https://analytics.gnps2.org/umami.js"></script>
        <script async defer data-website-id="74bc9983-13c4-4da0-89ae-b78209c13aaf" src="https://analytics.gnps2.org/umami.js"></script>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""

NAVBAR = dbc.Navbar(
    children=[
        dbc.NavbarBrand(
            html.Img(src="https://gnps2.org/static/img/logo.png", width="120px"),
            href="https://www.cs.ucr.edu/~mingxunw/"
        ),
        dbc.Nav(
            [
                dbc.NavItem(dbc.NavLink("plantMASST Dashboard - Version 2025.04.03", href="/plantmasst")),
                dbc.NavItem(dbc.NavLink("Documentation", href="https://wang-bioinformatics-lab.github.io/GNPS2_Documentation/plantmasst/", target="_blank")),
            ],
        navbar=True)
    ],
    color="light",
    dark=False,
    sticky="top",
)

DATASELECTION_CARD = [
    dbc.CardHeader(html.H5("Data Selection")),
    dbc.CardBody(
        [
            html.H5(children='GNPS Data Selection - Enter USI or Spectrum Peaks'),
            html.Br(),
            html.Br(),
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Spectrum USI"),
                    dbc.Input(id='usi1', placeholder="Enter GNPS USI", value=""),
                ],
                className="mb-3",
            ),
            html.Hr(),
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Spectrum Peaks"),
                    dbc.Textarea(id='peaks',
                                 placeholder="Enter one peak per line as follows.\n"
                                             "Tab, comma or space separated are accepted, see examples on the right panel\n"
                                             "Then click on 'Search plantMASST by Spectrum Peaks'\n\n"
                                             "m/z1\t\tintensity1\nm/z2\tintensity2\nm/z3\tintensity3\n...", rows=10),
                ],
                className="mb-3"
            ),
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Precursor m/z"),
                    dbc.Input(id='precursor_mz', type='', placeholder="precursor m/z", min = 1, max=10000),
                    dbc.Tooltip("Use with Spectrum Peaks Search (required)", target="precursor_mz", placement="bottom"),
                    dbc.InputGroupText("Charge"),
                    dbc.Input(id='charge', type='number', placeholder="charge", min = 1, max=40),
                    dbc.Tooltip("Use with Spectrum Peaks Search (optional, default=1)", target="charge", placement="bottom"),
                    dbc.InputGroupText("Use only the top N most intense peaks (optional)"),
                    dbc.Input(id='max_peaks', type='number', placeholder="max_peaks", min=3, max=1000, step=1),
                    dbc.Tooltip("Use with Spectrum Peaks or USI Search (optional). Leave blank for a standard search.\
                                 When provided, keeps only the most intense peak for each rounded m/z value, " \
                                 "then selects the top N by intensity. (min = 3; max = 1000)",
                                target="max_peaks", placement="bottom"),
                ],
                className="mb-3 no-margin-bottom"
            ),
            html.Hr(),
            dbc.InputGroup(
                [
                    dbc.InputGroupText("PM Tolerance (Da)"),
                    dbc.Input(id='pm_tolerance', type='number', placeholder="pm tolerance", value=0.05, min = 0.01, max = 0.2, step=0.01),
                    dbc.Tooltip("Tolerance for precursor mass in Daltons. Min= 0.01 ppm; Max= 0.2 ppm", target="pm_tolerance", placement="bottom"),
                    dbc.InputGroupText("Fragment Tolerance (Da)"),
                    dbc.Input(id='fragment_tolerance', type='number', placeholder="fragment_tolerance", value=0.05,min = 0.01, max = 0.2, step=0.01),
                    dbc.Tooltip("Tolerance for fragment mass in Daltons. Min= 0.01 ppm; Max= 0.2 ppm", target="fragment_tolerance", placement="bottom"),
                    dbc.InputGroupText("Cosine Threshold"),
                    dbc.Input(id='cosine_threshold', type='number', placeholder="cosine_threshold", value=0.7, min=0.5, max=1.0, step=0.01),
                    dbc.Tooltip("Cosine Threshold for matching. Min= 0.5; Max= 1.0", target="cosine_threshold", placement="bottom"),
                    dbc.InputGroupText("Minimum Matched Peaks"),
                    dbc.Input(id='min_matched_peaks', type='number', placeholder="min_matched_peaks", value=3, min=1, max=100, step=1),
                    dbc.Tooltip("Minimum number of matched peaks for a match. Min= 1; Max= 100", target="min_matched_peaks", placement="bottom"),
                ],
                className="mb-3",
            ),
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Analog Search"),
                    dbc.Select(
                        id="analog_select",
                        options=[
                            {"label": "Yes", "value": "Yes"},
                            {"label": "No", "value": "No"},
                        ],
                        value="No"
                    ),
                    dbc.InputGroupText("Delta Mass Below (Da)"),
                    dbc.Input(id='delta_mass_below', type='number', placeholder="delta_mass_below", value=130, min = 0, max = 300, step=1),
                    dbc.Tooltip("Min= 0; Max= 300", target="delta_mass_below", placement="bottom"),
                    dbc.InputGroupText("Delta Mass Above (Da)"),
                    dbc.Input(id='delta_mass_above', type='number', placeholder="delta_mass_above", value=200, min = 0, max = 300, step=1),
                    dbc.Tooltip("Min= 0; Max= 300", target="delta_mass_above", placement="bottom"),
                ],
                className="mb-3",
            ),
            dbc.Row([
                dbc.Col([
                    html.Div(
                        dbc.Button("Search plantMASST by USI", color="warning", id="search_button_usi", n_clicks=0),
                        className="d-grid gap-2",
                    )
                ]),
                dbc.Col([
                    html.Div(
                        dbc.Button("Search plantMASST by Spectrum Peaks", color="warning", id="search_button_peaks", n_clicks=0),
                        className="d-grid gap-2",
                    )
                ]),
                dbc.Col([
                    html.Div(
                        dbc.Button("Copy Link", color="warning", id="copy_link_button", n_clicks=0),
                        className="d-grid gap-2",
                    )
                ]),
                dbc.Col([
                    html.A( html.Div(
                        dbc.Button("Open External MASST Search Results", color="warning", n_clicks=0),
                        className="d-grid gap-2"), id="link_to_masst", href="", target="_blank"),
                ])]
            ),
            html.Div(
                [
                    dcc.Link(id="query_link", href="#", target="_blank"),
                ],
                style={
                        "display" :"none"
                }
            )
        ]
    )
]

LEFT_DASHBOARD = [
    html.Div(
        [
            html.Div(DATASELECTION_CARD),
        ]
    )
]

MIDDLE_DASHBOARD = [
    dbc.CardHeader(html.H5("Data Exploration")),
    dbc.CardBody(
        [
            dcc.Loading(
                id="output",
                children=[html.Div([html.Div(id="loading-output-23")])],
                type="default",
            ),
            html.Br(),
            html.Hr(),
            html.Br(),
            dcc.Loading(
                id="spectrummirror",
                children=[html.Div([html.Div(id="loading-output-24")])],
                type="default",
            ),

        ]
    )
]

CONTRIBUTORS_DASHBOARD = [
    dbc.CardHeader(html.H5("Contributors")),
    dbc.CardBody(
        [
            "Mingxun Wang PhD - UC Riverside",
            html.Br(),
            "Robin Schmid PhD - UC San Diego",
            html.Br(),
            "Wender Gomes PhD - UC San Diego",
            html.Br(),
            "Helena M. Russo PhD - UC San Diego",
            html.Br(),
            "Wilhan Nunes PhD - UC San Diego",
            html.Br(),
            "Simone Zuffa PhD - UC San Diego",
            html.Br(),
            "Ben Pullman PhD - UC San Diego",
            html.Br(),
            html.Hr(),
            html.H6("Preprint Citaton"),
            html.A("plantMASST - Community-driven chemotaxonomic digitization of plants",
                   href='https://doi.org/10.1101/2024.05.13.593988', target='_blank'),
        ]
    )
]


def create_example(lib_id, use_peaks=False):
    if not use_peaks:
        hash_dict = {"usi1": f"mzspec:GNPS:GNPS-LIBRARY:accession:{lib_id}", "peaks": [""], "precursor_mz": [""]}
        return f"/plantmasst#{urllib.parse.quote(json.dumps(hash_dict))}"
    else:
        url = f"https://metabolomics-usi.gnps2.org/json/?usi1=mzspec:GNPS:GNPS-LIBRARY:accession:{lib_id}"
        response = requests.get(url)
        data = response.json()

        spectrum_details = data.get("peaks", [])
        peaks_list = "\n".join(f"{mz}, {intensity}" for mz, intensity in spectrum_details)

        charge = data.get('precursor_charge')
        precursor_mz = data.get('precursor_mz')

        hash_dict = {
            "usi1": "",
            "peaks": peaks_list,
            "precursor_mz": precursor_mz,
            "charge": charge}

        return f"/plantmasst/#{urllib.parse.quote(json.dumps(hash_dict))}"

# Name, ID, Library ID, and use_peaks param
examples_data = [
    ("Moroidin", "CCMSLIB00005435899"),
    ("Rutin", "CCMSLIB00003139483"),
    ("Isoschaftoside", "CCMSLIB00005778294"),
    ("Orientin", "CCMSLIB00004696818"),
    ("Dicaffeoylquinic acid", "CCMSLIB00005724378"),
    ("Digalloylquinic acid", "CCMSLIB00004692123"),
    ("Tetrahydropapaveroline", "CCMSLIB00000222377"),
    ("Aurantiamide acetate", "CCMSLIB00005727351"),
    ("Makisterone A", "CCMSLIB00004717894"),
    ("6-Hydroxyloganin", "CCMSLIB00000853770"),
    ("Karakin", "CCMSLIB00010007469"),
    ("Procyanidin B2", "CCMSLIB00000081689"),
    ("Secoisolariciresinol", "CCMSLIB00005741229"),
    ("Epiyangambin", "CCMSLIB00004719556"),
]

peaks_examples = []
for text, lib_id in examples_data:
        peaks_examples.append(html.A(text, href=create_example(lib_id, use_peaks=True))),
        peaks_examples.append(html.Br())

usi_examples = []
for text, lib_id in examples_data:
        usi_examples.append(html.A(text, href=create_example(lib_id, use_peaks=False))),
        usi_examples.append(html.Br())

EXAMPLES_DASHBOARD = [
    dbc.CardHeader(html.H5("Examples")),
    dbc.CardBody(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H6("Using USI"),
                            html.Br(),
                            *usi_examples,
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            html.H6("Using peaks"),
                            html.Br(),
                            *peaks_examples
                        ],
                        width=6,
                    ),
                ]
            )
        ]
    )
]

BODY = dbc.Container(
    [
        dcc.Location(id='url', refresh=False),
        dbc.Row([
            dbc.Col(
                dbc.Card(LEFT_DASHBOARD),
                className="col-9"
            ),
            dbc.Col(
                [
                    dbc.Card(CONTRIBUTORS_DASHBOARD),
                    html.Br(),
                    dbc.Card(EXAMPLES_DASHBOARD)
                ],
                className="col-3"
            ),
        ], style={"marginTop": 30}),
        html.Br(),
        dbc.Row([
            dbc.Card(MIDDLE_DASHBOARD)
        ])
    ],
    fluid=True,
    className="",
)

dash_app.layout = html.Div(children=[NAVBAR, BODY])

def _get_url_param(param_dict, key, default):
    return param_dict.get(key, default)

@dash_app.callback([
                Output('usi1', 'value'),
                Output('peaks', 'value'),
                Output('precursor_mz', 'value'),
                Output('charge', 'value'),
                Output('max_peaks', 'value'),
                Output('pm_tolerance', 'value'),
                Output('fragment_tolerance', 'value'),
                Output('cosine_threshold', 'value'),
                Output('min_matched_peaks', 'value'),
                Output('analog_select', 'value'),
                Output('delta_mass_below', 'value'),
                Output('delta_mass_above', 'value'),
              ],
              [
                  Input('url', 'hash')
              ])
def determine_task(search):

    try:
        query_dict = json.loads(urllib.parse.unquote(search[1:]))
    except:
        query_dict = {}

    usi1 = _get_url_param(query_dict, "usi1", 'mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00000085687')
    peaks = _get_url_param(query_dict, "peaks", '')
    charge = _get_url_param(query_dict, "charge", '')
    max_peaks = _get_url_param(query_dict, "max_peaks", None)
    precursor_mz = _get_url_param(query_dict, "precursor_mz", '')
    charge = _get_url_param(query_dict, "charge", '')
    pm_tolerance = _get_url_param(query_dict, "pm_tolerance", 0.05)
    fragment_tolerance = _get_url_param(query_dict, "fragment_tolerance", 0.05)
    cosine_threshold = _get_url_param(query_dict, "cosine_threshold", 0.7)
    min_matched_peaks = _get_url_param(query_dict, "min_matched_peaks", 3)
    analog_select = _get_url_param(query_dict, "analog_select", 'No')
    delta_mass_below = _get_url_param(query_dict, "delta_mass_below", 130)
    delta_mass_above = _get_url_param(query_dict, "delta_mass_above", 200)

    return [usi1, peaks, precursor_mz, charge, max_peaks, pm_tolerance, fragment_tolerance, cosine_threshold, min_matched_peaks, analog_select, delta_mass_below, delta_mass_above]


def sort_and_filter_by_intensity(peaks_string, max_peaks=None):
    if max_peaks is not None:
        lines = peaks_string.strip().split('\n')
        pairs = [tuple(map(float, line.split())) for line in lines if line.strip()]

        # Create a dictionary to store the most intense peak for each rounded m/z
        peak_dict = {}
        for mz, intensity in pairs:
            mz_rounded = round(mz)
            if mz_rounded not in peak_dict or intensity > peak_dict[mz_rounded][1]:
                peak_dict[mz_rounded] = (mz, intensity)

        # Get the list of most intense peaks per rounded m/z and sort by intensity
        unique_peaks = list(peak_dict.values())
        sorted_peaks = sorted(unique_peaks, key=lambda x: x[1], reverse=True)[:max_peaks]

        # Sort the final result by m/z
        sorted_by_mz = sorted(sorted_peaks, key=lambda x: x[0])
        filtered_peaks = '\n'.join(f"{mz} {intensity}" for mz, intensity in sorted_by_mz)
    else:
        filtered_peaks = peaks_string

    return filtered_peaks


@dash_app.callback([
                Output('output', 'children')
              ],
              [
                Input('search_button_usi', 'n_clicks'),
                Input('search_button_peaks', 'n_clicks'),
              ],
              [
                State('usi1', 'value'),
                State('peaks', 'value'),
                State('max_peaks', 'value'),
                State('precursor_mz', 'value'),
                State('charge', 'value'),
                State('pm_tolerance', 'value'),
                State('fragment_tolerance', 'value'),
                State('cosine_threshold', 'value'),
                State('min_matched_peaks', 'value'),
                State('analog_select', 'value'),
                State('delta_mass_below', 'value'),
                State('delta_mass_above', 'value')
              ])
def draw_output(
                search_button_usi,
                search_button_peaks,
                usi1,
                peaks,
                max_peaks,
                precursor_mz,
                charge,
                prec_mz_tol,
                ms2_mz_tol,
                min_cos,
                min_matched_peaks,
                use_analog,
                analog_mass_below,
                analog_mass_above):

    button_id = ctx.triggered_id if not None else 'No clicks yet'

    import sys
    print("HERE", search_button_usi, button_id, file=sys.stderr)

    # This is on load
    if search_button_usi == 0 and search_button_peaks == 0:
        return [dash.no_update]

    # For plantMASST code from robin
    # import sys
    # sys.path.insert(0, "microbe_masst/code/")
    # import microbe_masst

    import uuid
    mangling = str(uuid.uuid4())
    # keep temp/microbemasst as the folder for the results. it's all generated automatically and we only pick plants here
    output_temp = os.path.join("temp", "microbemasst", mangling)
    os.makedirs(output_temp, exist_ok=True)

    out_file = "../../{}/fastMASST".format(output_temp)

    # TODO seems to always run analog
    use_analog = use_analog == "Yes"

    # If USI is a list
    if len(usi1) == 1:
        usi1 = usi1[0]

    if button_id == "search_button_usi":
        if max_peaks is not None:
            # Retrieve peaks using the API
            url = f"https://metabolomics-usi.gnps2.org/json/?usi1={usi1}"
            response = requests.get(url)
            data = response.json()

            # Extract and filter peaks
            spectrum_details = data.get("peaks", [])
            peaks_list = "\n".join(f"{mz} {intensity}" for mz, intensity in spectrum_details)
            filtered_peaks = sort_and_filter_by_intensity(peaks_list, max_peaks)

            # Write filtered peaks to an MGF file
            mgf_string = f"""BEGIN IONS
PEPMASS={data.get('precursor_mz')}
MSLEVEL=2
CHARGE={data.get('precursor_charge', 1)}
{filtered_peaks}
END IONS\n"""
            mgf_filename = os.path.join(output_temp, "input_spectra.mgf")
            with open(mgf_filename, "w") as o:
                o.write(mgf_string)

            # Update the command to use the MGF file
            cmd = 'cd microbe_masst/code/ && python masst_batch_client.py \
            --in_file "{}" \
            --out_file "{}" \
            --parallel_queries 1 \
            --precursor_mz_tol {} \
            --mz_tol {} \
            --min_cos {} \
            --min_matched_signals {} \
            --analog {} \
            --analog_mass_below {} \
            --analog_mass_above {} \
            '.format(os.path.join("../..", mgf_filename),
                     out_file,
                     prec_mz_tol,
                     ms2_mz_tol,
                     min_cos,
                     min_matched_peaks,
                     use_analog,
                     analog_mass_below,
                     analog_mass_above
                     )
        else:
            # Original command for USI search
            cmd = 'cd microbe_masst/code/ && python masst_client.py \
            --usi_or_lib_id "{}" \
            --out_file "{}" \
            --precursor_mz_tol {} \
            --mz_tol {} \
            --min_cos {} \
            --min_matched_signals {} \
            --analog_mass_below {} \
            --analog_mass_above {} \
            '.format(usi1,
                     out_file,
                     prec_mz_tol,
                     ms2_mz_tol,
                     min_cos,
                     min_matched_peaks,
                     analog_mass_below,
                     analog_mass_above
                     )
        # Tacking on the analog flag
        if use_analog:
            cmd += " --analog true"


    elif button_id == "search_button_peaks":
        # Writing out the MGF file if we are using peaks
        print("USING PEAKS")
        peaks = peaks.replace(",", " ").replace("\t", " ")
        # extract m/z intensity, sort most intense first, and get the top N peaks if max_peaks is set
        peaks = sort_and_filter_by_intensity(peaks, max_peaks)

        # default charge to 1 if not passed
        charge = '1' if charge is None else charge
        mgf_string = """BEGIN IONS
PEPMASS={}
MSLEVEL=2
CHARGE={}
{}
END IONS\n""".format(precursor_mz, charge, peaks)

        mgf_filename = os.path.join(output_temp, "input_spectra.mgf")
        with open(mgf_filename, "w") as o:
            o.write(mgf_string)

        cmd = 'cd microbe_masst/code/ && python masst_batch_client.py \
        --in_file "{}" \
        --out_file "{}" \
        --parallel_queries 1 \
        --precursor_mz_tol {} \
        --mz_tol {} \
        --min_cos {} \
        --min_matched_signals {} \
        --analog {} \
        --analog_mass_below {} \
        --analog_mass_above {} \
        '.format(os.path.join("../..", mgf_filename),
                out_file,
                prec_mz_tol,
                ms2_mz_tol,
                min_cos,
                min_matched_peaks,
                use_analog,
                analog_mass_below,
                analog_mass_above
                )

    import sys
    print(cmd, file=sys.stderr, flush=True)
    os.system(cmd)

    response_list = [html.Iframe(src="/plantmasst/results?task={}&analog={}".format(mangling, use_analog), width="100%", height="900px")]

    # Creating download link for the results
    response_list.append(html.Br())
    response_list.append(html.A("Download Results", href="/plantmasst/results?task={}&analog={}".format(mangling, use_analog), download="mangling.html", target="_blank"))

    return [response_list]

@dash_app.callback([
                Output('spectrummirror', 'children')
              ],
              [
                  Input('usi1', 'value'),
                  Input('table', 'derived_virtual_data'),
                  Input('table', 'derived_virtual_selected_rows'),
              ]
)
def draw_spectrum(usi1, table_data, table_selected):
    try:
        selected_row = table_data[table_selected[0]]
    except:
        return ["Choose Match to Show Mirror Plot"]

    dataset_accession = selected_row["Accession"]
    dataset_scan = selected_row["DB Scan"]

    database_usi = "mzspec:MSV000084314:{}:scan:{}".format("updates/2020-11-18_mwang87_d115210a/other/MGF/{}.mgf".format(dataset_accession), dataset_scan)

    url_params_dict = {}
    url_params_dict["usi1"] = usi1
    url_params_dict["usi2"] = database_usi

    url_params = urllib.parse.urlencode(url_params_dict)

    link_url = "https://metabolomics-usi.gnps2.org/dashinterface"
    link = html.A("View Spectrum Mirror Plot in Metabolomics Resolver", href=link_url + "?" + url_params, target="_blank")
    svg_url = "https://metabolomics-usi.gnps2.org/svg/mirror/?{}".format(url_params)

    image_obj = html.Img(src=svg_url)

    return [[link, html.Br(), image_obj]]


@dash_app.callback([
                Output('query_link', 'href'),
              ],
                [
                    Input('usi1', 'value'),
                    Input('peaks', 'value'),
                    Input('precursor_mz', 'value'),
                    Input('charge', 'value'),
                    Input('max_peaks', 'value'),
                    Input('pm_tolerance', 'value'),
                    Input('fragment_tolerance', 'value'),
                    Input('cosine_threshold', 'value'),
                    Input('min_matched_peaks', 'value'),
                    Input('analog_select', 'value'),
                    Input('delta_mass_below', 'value'),
                    Input('delta_mass_above', 'value'),
                ])
def draw_url(usi1, peaks, precursor_mz, charge, max_peaks, pm_tolerance, fragment_tolerance, cosine_threshold, min_matched_peaks, analog_select, delta_mass_below, delta_mass_above):
    params = {}
    params["usi1"] = usi1
    params["peaks"] = peaks
    params["precursor_mz"] = precursor_mz
    params["charge"] = charge
    params["max_peaks"] = max_peaks
    params["pm_tolerance"] = pm_tolerance
    params["fragment_tolerance"] = fragment_tolerance
    params["cosine_threshold"] = cosine_threshold
    params["min_matched_peaks"] = min_matched_peaks
    params["analog_select"] = analog_select
    params["delta_mass_below"] = delta_mass_below
    params["delta_mass_above"] = delta_mass_above

    url_params = urllib.parse.quote(json.dumps(params))

    return [request.host_url + "/plantmasst#" + url_params]


@dash_app.callback([
                Output('link_to_masst', 'href'),
              ],
                [
                    Input('usi1', 'value'),
                ])
def draw_url(usi1):
    params = {}
    params["usi1"] = usi1

    try:
        params["usi1"] = usi1[0]
    except:
        pass

    url_params = urllib.parse.urlencode(params)

    return ["https://fasst.gnps2.org/fastsearch/?" + url_params]


dash_app.clientside_callback(
    """
    function(n_clicks, button_id, text_to_copy) {
        original_text = "Copy Link"
        if (n_clicks > 0) {
            const el = document.createElement('textarea');
            el.value = text_to_copy;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            setTimeout(function(id_to_update, text_to_update){ 
                return function(){
                    document.getElementById(id_to_update).textContent = text_to_update
                }}(button_id, original_text), 1000);
            document.getElementById(button_id).textContent = "Copied!"
            return 'Copied!';
        } else {
            return original_text;
        }
    }
    """,
    Output('copy_link_button', 'children'),
    [
        Input('copy_link_button', 'n_clicks'),
        Input('copy_link_button', 'id'),
    ],
    [
        State('query_link', 'href'),
    ]
)

# API
@app.route("/plantmasst/results")
def plantmasst_results():
    use_analog = request.args.get("analog") == "True"
    html_file = plant_masst_path(request.args.get("task"), use_analog)
    return send_file(html_file)

def plant_masst_path(task, use_analog):
    """
    actual file found - success and matches to plantMASST,
    matches file found - success but no matches,
    no success - just placeholder to show error,
    :param task: taskid
    :param use_analog: whether to export the _analog html file or not
    :return: the html file that matches the state
    """
    # keep temp/microbemasst/ as folder. All files are generated there
    task_path = os.path.basename(task)
    output_folder = os.path.join("temp", "microbemasst", task_path)
    html_file = os.path.join(output_folder, "fastMASST_analog_plant.html") \
        if use_analog == True else os.path.join(output_folder, "fastMASST_plant.html")
    if os.path.isfile(html_file):
        return html_file
    elif os.path.isfile(os.path.join(output_folder, "fastMASST_matches.tsv")):
        return os.path.join("html_results", "success_no_matches_metadata.html")
    else:
        return os.path.join("html_results", "error_result.html")




if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
    # app.run_server(debug=True, port=5000, host="0.0.0.0")
