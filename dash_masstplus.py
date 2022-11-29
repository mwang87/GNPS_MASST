# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_table
import plotly.express as px
import plotly.graph_objects as go 
from dash.dependencies import Input, Output, State
import os
from zipfile import ZipFile
import urllib.parse
from flask import Flask, send_from_directory

import pandas as pd
import requests
import uuid
import werkzeug

import numpy as np
from tqdm import tqdm
import urllib
import json

from collections import defaultdict
import uuid

from flask_caching import Cache
import tasks

from app import app

dash_app = dash.Dash(
    name="dashinterface",
    server=app,
    url_base_pathname="/masstplus/",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)

dash_app.title = 'MASST+'

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
            href="https://www.cs.ucr.edu/~mingxunw/"
        ),
        dbc.Nav(
            [
                dbc.NavItem(dbc.NavLink("MASST+ Dashboard - Version 0.1", href="/masst_plus")),
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
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Analog Search"),
                    dbc.Select(
                        id="analog_search",
                        options=[
                            {"label": "Yes", "value": "Yes"},
                            {"label": "No", "value": "No"},
                        ],
                        value="No"
                    )
                ],
                className="mb-3",
            ),
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
            "Tyler Yasaka - CMU",
            html.Br(),
            "Mingxun Wang PhD - UC San Diego",
            html.Br(),
            "Hosein Mohimani - CMU",
            html.Br(),
            # html.H5("Citation"),
            # html.A('Mingxun Wang, Jeremy J. Carver, Vanessa V. Phelan, Laura M. Sanchez, Neha Garg, Yao Peng, Don Duy Nguyen et al. "Sharing and community curation of mass spectrometry data with Global Natural Products Social Molecular Networking." Nature biotechnology 34, no. 8 (2016): 828. PMID: 27504778', 
            #         href="https://www.nature.com/articles/nbt.3597")
        ]
    )
]

EXAMPLES_DASHBOARD = [
    dbc.CardHeader(html.H5("Examples")),
    dbc.CardBody(
        [
            html.A('Basic', 
                    href="/masstplus?usi1=mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943&analog=Yes"),
            html.Br(),
            html.A('Malyngamide',
                    href="/masstplus?usi1=mzspec:GNPS:TASK-a9c32880f76b4786a5a89682ed101d8f-spectra/specs_ms.mgf:scan:29"),
            html.Br(),
            html.A('Test Analog Search 1',
                    href="/masstplus/?usi1=mzspec:MSV000084314:updates/2020-10-08_mwang87_d7c866dd/other/MGF/MSV000078787.mgf:scan:28&analog=Yes"),
            
        ]
    )
]

BODY = dbc.Container(
    [
        dcc.Location(id='url', refresh=False),
        dbc.Row([
            dbc.Col(
                dbc.Card(LEFT_DASHBOARD),
                className="col-4"
            ),
            dbc.Col(
                [
                    dbc.Card(MIDDLE_DASHBOARD),
                    html.Br(),
                    dbc.Card(CONTRIBUTORS_DASHBOARD),
                    html.Br(),
                    dbc.Card(EXAMPLES_DASHBOARD)
                ],
                className="col-8"
            ),
        ], style={"marginTop": 30}),
    ],
    fluid=True,
    className="",
)

dash_app.layout = html.Div(children=[NAVBAR, BODY])

def _get_url_param(param_dict, key, default):
    return param_dict.get(key, [default])[0]

@dash_app.callback([
                Output('usi1', 'value'), 
                Output('analog_search', 'value')
              ],
              [
                  Input('url', 'search')
              ])
def determine_task(search):
    
    try:
        query_dict = urllib.parse.parse_qs(search[1:])
    except:
        query_dict = {}

    usi1 = _get_url_param(query_dict, "usi1", 'mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/specs_ms.mgf:scan:1943')
    analog_search = _get_url_param(query_dict, "analog", 'No')

    return [usi1, analog_search]


# @app.callback([
#                 Output('plot_link', 'children')
#               ],
#               [
#                   Input('gnps_tall_table_usi', 'value'),
#                   Input('gnps_quant_table_usi', 'value'),
#                   Input('gnps_metadata_table_usi', 'value'), 
#                 Input('feature', 'value'),
#                 Input("metadata_column", "value"),
#                 Input("facet_column", "value"),
#                 Input("animation_column", "value"),
#                 Input("group_selection", "value"),
#                 Input("color_selection", "value"),
#                 Input("theme", "value"),
#                 Input("plot_type", "value"),
#                 Input("image_export_format", "value"),
#                 Input("points_toggle", "value"),
#                 Input("log_axis", "value"),
#                 Input("lat_column", "value"),
#                 Input("long_column", "value"),
#                 Input("map_animation_column", "value"),
#                 Input("map_scope", "value"),
#               ])
# def draw_link(      gnps_tall_table_usi, 
#                     gnps_quant_table_usi, 
#                     gnps_metadata_table_usi, 
#                     feature_id, 
#                     metadata_column, 
#                     facet_column, 
#                     animation_column, 
#                     group_selection, 
#                     color_selection, 
#                     theme, 
#                     plot_type, 
#                     image_export_format, 
#                     points_toggle, 
#                     log_axis,
#                     lat_column,
#                     long_column,
#                     map_animation_column,
#                     map_scope):
#     # Creating Reproducible URL for Plot
#     url_params = {}
#     url_params["gnps_tall_table_usi"] = gnps_tall_table_usi
#     url_params["gnps_quant_table_usi"] = gnps_quant_table_usi
#     url_params["gnps_metadata_table_usi"] = gnps_metadata_table_usi

#     url_params["feature"] = feature_id
#     url_params["metadata"] = metadata_column
#     url_params["facet"] = facet_column
#     url_params["groups"] = ";".join(group_selection)
#     url_params["plot_type"] = plot_type
#     url_params["color"] = color_selection
#     url_params["points_toggle"] = points_toggle
#     url_params["theme"] = theme
#     url_params["animation_column"] = animation_column

#     # Mapping Options
#     url_params["lat_column"] = lat_column
#     url_params["long_column"] = long_column
#     url_params["map_animation_column"] = map_animation_column
#     url_params["map_scope"] = map_scope
    
#     url_provenance = dbc.Button("Link to this Plot", block=True, color="primary", className="mr-1")
#     provenance_link_object = dcc.Link(url_provenance, href="/?" + urllib.parse.urlencode(url_params) , target="_blank")

#     return [provenance_link_object]


@dash_app.callback([
                Output('output', 'children')
              ],
              [
                  Input('usi1', 'value'),
                  Input('analog_search', 'value')
            ])
def draw_output(usi1, analog_search):
    result = tasks.task_searchmasst.delay(usi1, analog_search)
    result_list = result.get()

    if len(result_list) == 0:
        return ["No Matches"]

    table_obj = dash_table.DataTable(
        id='table',
        columns=[{"name": i, "id": i} for i in result_list[0]],
        data=result_list,
        sort_action="native",
        filter_action="native",
        page_size=10,
        export_format="csv",
        row_selectable='single',
        css=[{'selector': '.row', 'rule': 'margin: 0'}],
        style_table={
            'overflowX': 'auto'
        }
    )

    return [table_obj]

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


# API
@app.route("/api")
def api():
    return "Up"

if __name__ == "__main__":
    app.run_server(debug=True, port=5000, host="0.0.0.0")
