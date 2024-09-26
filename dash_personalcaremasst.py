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

from flask_caching import Cache
from app import app

dash_app = dash.Dash(
    name="dashinterface",
    server=app,
    url_base_pathname="/personalcaremasst/",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)

dash_app.title = 'personalcareMASST'

cache = Cache(dash_app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'temp/flask-cache',
    'CACHE_DEFAULT_TIMEOUT': 0,
    'CACHE_THRESHOLD': 1000000
})

NAVBAR = dbc.Navbar(
    children=[
        dbc.NavbarBrand(
            html.Img(src="https://gnps2.org/static/img/logo.png", width="120px"),
            href="https://www.cs.ucr.edu/~mingxunw/"
        ),
        dbc.Nav(
            [
                dbc.NavItem(dbc.NavLink("microbeMASST Dashboard - Version 2024.08.26", href="/personalcareMASST")),
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
                    dbc.Textarea(id='peaks', placeholder="Enter one peak per line as follows:\n\nm/z1\tintensity1\nm/z2\tintensity2\nm/z3\tintensity3\n...", rows=10),
                ],
                className="mb-3"
            ),
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Precursor m/z"),
                    dbc.Input(id='precursor_mz', type='', placeholder="precursor m/z", min = 1, max=10000),
                    dbc.InputGroupText("Charge"),
                    dbc.Input(id='charge', type='number', placeholder="charge", min = 1, max=40),
                ],
                className="mb-3 no-margin-bottom"
            ),
            html.Hr(),
            dbc.InputGroup(
                [
                    dbc.InputGroupText("PM Tolerance (Da)"),
                    dbc.Input(id='pm_tolerance', type='number', placeholder="pm tolerance", value=0.05, min = 0.05, max = 0.4, step=0.05),
                    dbc.InputGroupText("Fragment Tolerance (Da)"),
                    dbc.Input(id='fragment_tolerance', type='number', placeholder="fragment_tolerance", value=0.05,min = 0.05, max = 0.4, step=0.05),
                    dbc.InputGroupText("Cosine Threshold"),
                    dbc.Input(id='cosine_threshold', type='number', placeholder="cosine_threshold", value=0.7, min=0.5, max=1.0, step=0.05),
                    dbc.InputGroupText("Minimum Matched Peaks"),
                    dbc.Input(id='min_matched_peaks', type='number', placeholder="min_matched_peaks", value=3, min=1, max=1000, step=1),
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
                    dbc.InputGroupText("Delta Mass Above (Da)"),
                    dbc.Input(id='delta_mass_above', type='number', placeholder="delta_mass_above", value=200, min = 0, max = 300, step=1),
                ],
                className="mb-3",
            ),
            dbc.Row([
                dbc.Col([
                    html.Div(
                        dbc.Button("Search personalcareMASST by USI", color="warning", id="search_button_usi", n_clicks=0),
                        className="d-grid gap-2",
                    )
                ]),
                dbc.Col([
                    html.Div(
                        dbc.Button("Search personalcareMASST by Spectrum Peaks", color="warning", id="search_button_peaks", n_clicks=0),
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
            "Coming soon",
            html.Br(),
        ]
    )
]

EXAMPLES_DASHBOARD = [
    dbc.CardHeader(html.H5("Examples")),
    dbc.CardBody(
        [
            html.P("Coming Soon"),
        ]
    )
]


# EXAMPLES_DASHBOARD = [
#     dbc.CardHeader(html.H5("Examples")),
#     dbc.CardBody(
#         [
#             html.A("lovastatin", id="example_molecule1", href='/microbemasst#%7B"usi1"%3A%20"mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00005435737"%2C%20"peaks"%3A%20%5B""%5D%2C%20"precursor_mz"%3A%20%5B""%5D%7D'),
#             html.Br(),
#             html.A("mevastatin", id="example_molecule2", href="/microbemasst#%7B%22usi1%22%3A%20%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00005435644%22%2C%20%22peaks%22%3A%20%5B%22%22%5D%2C%20%22precursor_mz%22%3A%20%5B%22%22%5D%7D"),
#             html.Br(),
#             html.A("arylomycin A4", id="example_molecule3",
#                    href="/microbemasst#%7B%22usi1%22%3A%20%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00000075066%22%2C%20%22peaks%22%3A%20%5B%22%22%5D%2C%20%22precursor_mz%22%3A%20%5B%22%22%5D%7D"),
#             html.Br(),
#             html.A("salinosporamide B", id="example_molecule4",
#                    href="/microbemasst#%7B%22usi1%22%3A%20%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00005721044%22%2C%20%22peaks%22%3A%20%5B%22%22%5D%2C%20%22precursor_mz%22%3A%20%5B%22%22%5D%7D"),
#             html.Br(),
#             html.A("yersiniabactin", id="example_molecule5",
#                    href="/microbemasst#%7B%22usi1%22%3A%20%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00005435750%22%2C%20%22peaks%22%3A%20%5B%22%22%5D%2C%20%22precursor_mz%22%3A%20%5B%22%22%5D%7D"),
#             html.Br(),
#             html.A("promicroferrioxamine", id="example_molecule6",
#                    href="/microbemasst#%7B%22usi1%22%3A%20%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00005716848%22%2C%20%22peaks%22%3A%20%5B%22%22%5D%2C%20%22precursor_mz%22%3A%20%5B%22%22%5D%7D"),
#             html.Br(),
#             html.A("glutamate-cholic acid (Glu-CA)", id="example_molecule7",
#                    href="/microbemasst#%7B%22usi1%22%3A%20%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00006582258%22%2C%20%22peaks%22%3A%20%5B%22%22%5D%2C%20%22precursor_mz%22%3A%20%5B%22%22%5D%7D"),
#             html.Br(),
#             html.A("glutamate-deoxycholic acid (Glu-DCA)", id="example_molecule8",
#                    href="/microbemasst#%7B%22usi1%22%3A%20%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00006582092%22%2C%20%22peaks%22%3A%20%5B%22%22%5D%2C%20%22precursor_mz%22%3A%20%5B%22%22%5D%7D"),
#             html.Br(),
#             html.A("ornitine-deoxycholic acid (Orn-DCA)", id="example_molecule9",
#                    href="/microbemasst#%7B%22usi1%22%3A%20%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00006582109%22%2C%20%22peaks%22%3A%20%5B%22%22%5D%2C%20%22precursor_mz%22%3A%20%5B%22%22%5D%7D"),
#             html.Br(),
#             html.A("citrulline-deoxycholic acid (Cit-DCA)", id="example_molecule10",
#                    href="/microbemasst#%7B%22usi1%22%3A%20%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00006582368%22%2C%20%22peaks%22%3A%20%5B%22%22%5D%2C%20%22precursor_mz%22%3A%20%5B%22%22%5D%7D"),
#             html.Br(),
#             html.A("commendamide", id="example_molecule11",
#                    href="/microbemasst#%7B%22usi1%22%3A%20%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00004679239%22%2C%20%22peaks%22%3A%20%5B%22%22%5D%2C%20%22precursor_mz%22%3A%20%5B%22%22%5D%7D"),
#             html.Br(),
#             html.A("Example Spectrum", id="example_molecule12",
#                    href="/microbemasst#%7B%22usi1%22%3A%20%5B%22mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00000085687%22%5D%2C%20%22peaks%22%3A%20%2280.94821%5Ct7964.9106%5Cn81.07002%5Ct8971.145%5Cn83.086006%5Ct3202.9917%5Cn85.06494%5Ct11110.859%5Cn90.97681%5Ct13512.115%5Cn91.05407%5Ct4261.0435%5Cn93.06991%5Ct9205.178%5Cn95.08565%5Ct14519.592%5Cn103.05421%5Ct4894.4756%5Cn105.07022%5Ct18651.326%5Cn107.085655%5Ct13574.504%5Cn109.10135%5Ct10270.613%5Cn119.08573%5Ct11157.091%5Cn120.08088%5Ct221964.84%5Cn121.10135%5Ct8484.143%5Cn123.08051%5Ct7757.252%5Cn123.11662%5Ct6180.583%5Cn125.09632%5Ct8554.115%5Cn131.04897%5Ct5342.3145%5Cn131.08565%5Ct8830.906%5Cn133.1012%5Ct14499.361%5Cn135.11697%5Ct7826.523%5Cn137.09662%5Ct3308.8342%5Cn143.08559%5Ct8934.355%5Cn145.10161%5Ct15179.775%5Cn147.1171%5Ct12624.565%5Cn149.05942%5Ct5136.6265%5Cn149.09752%5Ct3545.7485%5Cn155.08594%5Ct3597.0366%5Cn157.10156%5Ct17111.832%5Cn158.96388%5Ct16269.059%5Cn159.11728%5Ct21265.994%5Cn161.13286%5Ct13106.975%5Cn163.11238%5Ct4724.445%5Cn163.88464%5Ct3307.1091%5Cn164.93143%5Ct3316.7693%5Cn166.08643%5Ct343150.66%5Cn169.10081%5Ct4978.5405%5Cn171.1173%5Ct16191.34%5Cn173.13289%5Ct9658.38%5Cn175.11165%5Ct3796.6746%5Cn181.10126%5Ct5202.631%5Cn183.11746%5Ct9410.617%5Cn185.13248%5Ct10079.273%5Cn187.11198%5Ct6951.734%5Cn187.14844%5Ct6882.854%5Cn189.12732%5Ct6969.42%5Cn189.16422%5Ct3857.043%5Cn190.10503%5Ct3302.049%5Cn195.11647%5Ct4379.094%5Cn197.13237%5Ct8527.008%5Cn199.14832%5Ct33320.46%5Cn201.16425%5Ct9311.901%5Cn202.12257%5Ct7010.554%5Cn203.14282%5Ct3477.1448%5Cn209.13268%5Ct79797.53%5Cn211.14864%5Ct17406.05%5Cn213.1636%5Ct41344.633%5Cn215.14247%5Ct4830.4175%5Cn215.17964%5Ct8076.428%5Cn216.92337%5Ct14960.939%5Cn223.14853%5Ct21175.191%5Cn225.16386%5Ct21953.17%5Cn226.95168%5Ct22947.79%5Cn227.1435%5Ct47863.613%5Cn227.17917%5Ct30053.355%5Cn229.15894%5Ct15989.257%5Cn231.17638%5Ct5512.4907%5Cn237.16281%5Ct15475.934%5Cn239.18%5Ct10031.895%5Cn241.15839%5Ct11053.998%5Cn241.19487%5Ct17048.861%5Cn243.1748%5Ct12207.303%5Cn248.12822%5Ct51872.527%5Cn249.16403%5Ct7189.1157%5Cn251.17932%5Ct4746.559%5Cn253.19557%5Ct4837.2207%5Cn255.17413%5Ct17253.908%5Cn263.1798%5Ct9416.583%5Cn277.19507%5Ct7972.8696%5Cn279.211%5Ct4387.4307%5Cn281.1903%5Ct5729.192%5Cn288.15817%5Ct4419.695%5Cn293.22647%5Ct9807.555%5Cn295.20596%5Ct20866.555%5Cn295.24225%5Ct13296.892%5Cn309.22437%5Ct4090.7576%5Cn309.25928%5Ct10990.491%5Cn311.92468%5Ct4586.2993%5Cn319.24237%5Ct127415.27%5Cn337.2529%5Ct267401.4%5Cn355.26404%5Ct8754.0625%5Cn456.32526%5Ct8601.617%5Cn484.3201%5Ct5518.0684%5Cn502.33197%5Ct303219.62%5Cn520.3417%5Ct36472.902%22%2C%20%22precursor_mz%22%3A%20%22556.363%22%7D"),
#             html.Br(),
#         ]
#     )
# ]

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
    return param_dict.get(key, [default])

@dash_app.callback([
                Output('usi1', 'value'),
                Output('peaks', 'value'),
                Output('precursor_mz', 'value'),
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
    precursor_mz = _get_url_param(query_dict, "precursor_mz", '')

    return [usi1, peaks, precursor_mz]




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
                State('precursor_mz', 'value'),
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
                precursor_mz,
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

    # For MicrobeMASST code from robin
    # import sys
    # sys.path.insert(0, "microbe_masst/code/")
    # import microbe_masst

    import uuid
    mangling = str(uuid.uuid4())
    output_temp = os.path.join("temp", "microbemasst", mangling)
    os.makedirs(output_temp, exist_ok=True)

    out_file = "../../{}/fastMASST".format(output_temp)

    # TODO seems to always run analog
    use_analog = use_analog == "Yes"

    # If USI is a list
    if len(usi1) == 1:
        usi1 = usi1[0]

    # TODO - personalcareMASST maybe needs change
    if button_id == "search_button_usi":
        cmd = 'cd microbe_masst/code/ && python masst_client.py \
        --usi_or_lib_id "{}" \
        --out_file "{}" \
        --precursor_mz_tol {} \
        --mz_tol {} \
        --min_cos {} \
        --min_matched_signals {} \
        --analog_mass_below {} \
        --analog_mass_above {} \
        --database metabolomicspanrepo_index_latest \
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
            cmd += " --analog {}"


    elif button_id == "search_button_peaks":
        # Writing out the MGF file if we are using peaks
        print("USING PEAKS")
        mgf_string = """BEGIN IONS
PEPMASS={}
MSLEVEL=2
CHARGE=1
{}
END IONS\n""".format(precursor_mz, peaks.replace(",", " ").replace("\t", " "))

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
        --database metabolomicspanrepo_index_latest \
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

    response_list = [html.Iframe(src="/personalcareMASST/results?task={}".format(mangling), width="100%", height="900px")]

    # Creating download link for the results
    response_list.append(html.Br())
    response_list.append(html.A("Download Results", href="/personalcareMASST/results?task={}".format(mangling), download="mangling.html", target="_blank"))

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
                ])
def draw_url(usi1, peaks, precursor_mz):
    params = {}
    params["usi1"] = usi1
    params["peaks"] = peaks
    params["precursor_mz"] = precursor_mz

    url_params = urllib.parse.quote(json.dumps(params))

    return [request.host_url + "/personalcareMASST#" + url_params]


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
@app.route("/personalcareMASST/results")
def personalcareMASST_results():
    html_file = personalcareMASST(request.args.get("task"))

    return send_file(html_file)

def personalcareMASST(task):
    """
    actual file found - success and matches to personalcareMASST,
    matches file found - success but no matches,
    no success - just placeholder to show error,
    :param task: taskid
    :return: the html file that matches the state
    """
    task_path = os.path.basename(task)
    output_folder = os.path.join("temp", "personalcareMASST", task_path)
    # TODO: Update this to be the right file
    html_file = os.path.join(output_folder, "fastMASST_microbe.html")
    if os.path.isfile(html_file):
        return html_file
    elif os.path.isfile(os.path.join(output_folder, "fastMASST_matches.tsv")):
        return os.path.join("html_results", "success_no_matches_metadata.html")
    else:
        return os.path.join("html_results", "error_result.html")




if __name__ == "__main__":
    app.run_server(debug=True, port=5000, host="0.0.0.0")
