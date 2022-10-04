# -*- coding: utf-8 -*-
import dash
import werkzeug.utils
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import os
import urllib.parse
from flask import Flask, send_file, request

import urllib

from flask_caching import Cache
from app import app

dash_app = dash.Dash(
    name="dashinterface",
    server=app,
    url_base_pathname="/microbemasst/",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)

dash_app.title = 'microbeMASST'

cache = Cache(dash_app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'temp/flask-cache',
    'CACHE_DEFAULT_TIMEOUT': 0,
    'CACHE_THRESHOLD': 1000000
})

NAVBAR = dbc.Navbar(
    children=[
        dbc.NavbarBrand(
            html.Img(src="https://gnps-cytoscape.ucsd.edu/static/img/GNPS_logo.png", width="120px"),
            href="https://gnps.ucsd.edu"
        ),
        dbc.Nav(
            [
                dbc.NavItem(dbc.NavLink("microbeMASST Dashboard - Version 1.0", href="/microbemasst")),
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
            html.H5(children='GNPS Data Selection'),
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Spectrum USI"),
                    dbc.Input(id='usi1', placeholder="Enter GNPS USI", value=""),
                ],
                className="mb-3",
            ),
            dbc.Row([
                dbc.Col([
                    dbc.Button("Copy Link", color="info", id="copy_link_button", n_clicks=0),
                ]),
                dbc.Col([
                    html.A(dbc.Button("View MASST Search", color="info", n_clicks=0),
                        id="link_to_masst", href="", target="_blank"),
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
            "Simone Zuffa PhD - UC San Diego",
            html.Br(),
        ]
    )
]

EXAMPLES_DASHBOARD = [
    dbc.CardHeader(html.H5("Examples")),
    dbc.CardBody(
        [
            html.A('Stenothricin', 
                    href="/microbemasst?usi1=mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436027"),
            
        ]
    )
]

BODY = dbc.Container(
    [
        dcc.Location(id='url', refresh=False),
        dbc.Row([
            dbc.Col(
                dbc.Card(LEFT_DASHBOARD),
                className="col-6"
            ),
            dbc.Col(
                [
                    dbc.Card(CONTRIBUTORS_DASHBOARD),
                    # html.Br(),
                    # dbc.Card(EXAMPLES_DASHBOARD)
                ],
                className="col-6"
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
    return param_dict.get(key, [default])[0]

@dash_app.callback([
                Output('usi1', 'value'), 
              ],
              [
                  Input('url', 'search')
              ])
def determine_task(search):
    
    try:
        query_dict = urllib.parse.parse_qs(search[1:])
    except:
        query_dict = {}

    usi1 = _get_url_param(query_dict, "usi1", 'mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00000085687')

    return [usi1]




@dash_app.callback([
                Output('output', 'children')
              ],
              [
                  Input('usi1', 'value'),
                #   Input('prec_mz_tol', 'value'),
                #   Input('mz_tol', 'value'),
                #   Input('min_cos', 'value'),
                #   Input('min_matched_signals', 'value'),
                #   Input('use_analog', 'value'),
                #   Input('analog_mass_below', 'value'),
                #   Input('analog_mass_above', 'value')
            ])
# def draw_output(usi1,
#              prec_mz_tol,
#              ms2_mz_tol,
#              min_cos,
#              min_matched_signals,
#              use_analog,
#              analog_mass_below,
#              analog_mass_above):
def draw_output(usi1):
    # For MicrobeMASST code from robin
    # import sys
    # sys.path.insert(0, "microbe_masst/code/")
    # import microbe_masst

    import uuid
    mangling = str(uuid.uuid4())
    output_temp = os.path.join("temp", "microbemasst", mangling)
    os.makedirs(output_temp, exist_ok=True)

    out_file = "../../{}/fastMASST".format(output_temp)

    prec_mz_tol = 0.05
    ms2_mz_tol = 0.05
    min_cos = 0.7
    min_matched_signals = 6
    use_analog = False
    analog_mass_below = 100
    analog_mass_above = 150

    cmd = 'cd microbe_masst/code/ && python masst_client.py \
    --usi_or_lib_id "{}" \
    --out_file "{}" \
    --precursor_mz_tol {} \
    --mz_tol {} \
    --min_cos {} \
    --min_matched_signals {} \
    --analog {} \
    --analog_mass_below {} \
    --analog_mass_above {} \
    '.format(usi1,
             out_file,
             prec_mz_tol,
             ms2_mz_tol,
             min_cos,
             min_matched_signals,
             use_analog,
             analog_mass_below,
             analog_mass_above
             )
    import sys
    print(cmd, file=sys.stderr, flush=True)
    os.system(cmd)
    
    return [html.Iframe(src="/microbemasst/results?task={}".format(mangling), width="100%", height="900px")]

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

    link_url = "https://metabolomics-usi.ucsd.edu/dashinterface"
    link = html.A("View Spectrum Mirror Plot in Metabolomics Resolver", href=link_url + "?" + url_params, target="_blank")
    svg_url = "https://metabolomics-usi.ucsd.edu/svg/mirror/?{}".format(url_params)

    image_obj = html.Img(src=svg_url)

    return [[link, html.Br(), image_obj]]


@dash_app.callback([
                Output('query_link', 'href'),
              ],
                [
                    Input('usi1', 'value'),
                ])
def draw_url(usi1):
    params = {}
    params["usi1"] = usi1

    url_params = urllib.parse.urlencode(params)

    return [request.host_url + "/microbemasst?" + url_params]


@dash_app.callback([
                Output('link_to_masst', 'href'),
              ],
                [
                    Input('usi1', 'value'),
                ])
def draw_url(usi1):
    params = {}
    params["usi1"] = usi1

    url_params = urllib.parse.urlencode(params)

    return ["https://fastlibrarysearch.ucsd.edu/fastsearch/?" + url_params]


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
@app.route("/microbemasst/results")
def results():
    html_file = microbe_masst_path(request.args.get("task"))
    return send_file(html_file)

def microbe_masst_path(task):
    task_path = os.path.basename(task)
    output_folder = os.path.join("temp", "microbemasst", task_path, "fastMASST_microbe.html")
    return output_folder


if __name__ == "__main__":
    app.run_server(debug=True, port=5000, host="0.0.0.0")
