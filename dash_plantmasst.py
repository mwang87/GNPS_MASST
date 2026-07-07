# -*- coding: utf-8 -*-
import sys
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
import pandas as pd
from dash import dash_table

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

# ---- PlantMASST Explorer: pre-computed at module load ----
_REPO_DIR = os.path.dirname(os.path.abspath(__file__))
_df_files = pd.read_csv(os.path.join(_REPO_DIR, "microbe_masst", "trees", "plant_masst_tree", "plant_masst_table.csv"))
_df_files["Taxa_NCBI"] = pd.to_numeric(_df_files["Taxa_NCBI"], errors="coerce")
_df_files = _df_files.dropna(subset=["Taxa_NCBI"])
_df_files["Taxa_NCBI"] = _df_files["Taxa_NCBI"].astype(int)

_df_lineage = pd.read_csv(os.path.join(_REPO_DIR, "microbe_masst", "lineages", "plant_masst_lineages.csv"))

FILE_LISTS = {
    taxid: grp[["Filename", "MassIVE", "file_usi"]].to_dict("records")
    for taxid, grp in _df_files.groupby("Taxa_NCBI")
}

_file_counts = _df_files.groupby("Taxa_NCBI").size().reset_index(name="file_count")

_LINEAGE_RANKS = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]
_lineage_filled = _df_lineage.copy()
for _col in _LINEAGE_RANKS:
    _lineage_filled[_col] = _lineage_filled[_col].fillna("Unknown")

_summary_filled = _file_counts.merge(
    _lineage_filled[["Taxa_NCBI"] + _LINEAGE_RANKS], on="Taxa_NCBI", how="left",
)
for _col in _LINEAGE_RANKS:
    _summary_filled[_col] = _summary_filled[_col].fillna("Unknown")

_summary_filled = _summary_filled[_summary_filled["kingdom"] != "Unknown"].reset_index(drop=True)

SPECIES_BY_TAXID = _summary_filled.set_index("Taxa_NCBI")["species"].to_dict()
GENUS_BY_TAXID = _summary_filled.set_index("Taxa_NCBI")["genus"].to_dict()

# Taxonomic levels the Explorer table can be grouped by, finest to coarsest.
LEVEL_COLUMNS = ["Taxa_NCBI", "species", "genus", "family", "order", "class", "phylum", "kingdom"]
LEVEL_LABELS = {
    "Taxa_NCBI": "TaxID",
    "species": "Species",
    "genus": "Genus",
    "family": "Family",
    "order": "Order",
    "class": "Class",
    "phylum": "Phylum",
    "kingdom": "Kingdom",
}
DEFAULT_LEVEL = "Taxa_NCBI"

_NCBI_TAXONOMY_URL = "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id="


def _build_level(level):
    """Build Explorer table records grouped at `level`, along with a
    row_id -> [taxids] map (for the file modal) and a plain export dataframe.
    Columns finer than `level` collapse to a placeholder since they no
    longer map 1:1 to a single row.
    """
    idx = LEVEL_COLUMNS.index(level)
    finer_cols = LEVEL_COLUMNS[:idx]
    coarser_cols = [c for c in LEVEL_COLUMNS[idx + 1:] if c != "Taxa_NCBI"]

    if level == "Taxa_NCBI":
        grouped = _summary_filled.copy()
        grouped["_taxids"] = grouped["Taxa_NCBI"].apply(lambda t: [t])
    else:
        agg = {"file_count": "sum", "Taxa_NCBI": lambda s: list(s)}
        for c in coarser_cols:
            agg[c] = "first"
        grouped = _summary_filled.groupby(level, dropna=False).agg(agg).reset_index()
        grouped = grouped.rename(columns={"Taxa_NCBI": "_taxids"})

    grouped = grouped.sort_values("file_count", ascending=False).reset_index(drop=True)

    records = []
    export_rows = []
    row_taxids = {}
    row_label = {}
    for i, row in grouped.iterrows():
        rid = f"{level}::{i}"
        row_taxids[rid] = [int(t) for t in row["_taxids"]]
        row_label[rid] = row[level]

        rec = {"id": rid, "file_count": int(row["file_count"])}
        export_row = {"file_count": int(row["file_count"])}
        for c in LEVEL_COLUMNS:
            if c == "Taxa_NCBI":
                if level == "Taxa_NCBI":
                    taxid = int(row["Taxa_NCBI"])
                    rec[c] = "[{0}]({1}{0})".format(taxid, _NCBI_TAXONOMY_URL)
                    export_row[c] = taxid
                else:
                    rec[c] = "—"
                    export_row[c] = ""
                continue
            if c in finer_cols:
                rec[c] = "—"
                export_row[c] = ""
            else:
                rec[c] = row[c]
                export_row[c] = row[c]
        records.append(rec)
        export_rows.append(export_row)

    export_df = pd.DataFrame(export_rows, columns=LEVEL_COLUMNS + ["file_count"])
    return records, row_taxids, row_label, export_df


LEVEL_TABLES = {}
LEVEL_ROW_TAXIDS = {}
LEVEL_ROW_LABELS = {}
LEVEL_EXPORT_DFS = {}
for _level in LEVEL_COLUMNS:
    _records, _row_taxids, _row_label, _export_df = _build_level(_level)
    LEVEL_TABLES[_level] = _records
    LEVEL_ROW_TAXIDS[_level] = _row_taxids
    LEVEL_ROW_LABELS[_level] = _row_label
    LEVEL_EXPORT_DFS[_level] = _export_df

EXPLORER_SUMMARY_RECORDS = LEVEL_TABLES[DEFAULT_LEVEL]
EXPLORER_EXPORT_DF = LEVEL_EXPORT_DFS[DEFAULT_LEVEL]

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
            html.Img(src="https://wang-bioinformatics-lab.github.io/GNPS2_Documentation/img/logo/GNPS2_logo_blue-grey-black.png", width="120px"),
            href="https://www.cs.ucr.edu/~mingxunw/"
        ),
        dbc.Nav(
            [
                dbc.NavItem(html.Img(src="https://wang-bioinformatics-lab.github.io/GNPS2_Documentation/img/logo/plantMASST_logo.svg", height="40px"), className="me-2"),
                dbc.NavItem(dbc.NavLink("plantMASST Dashboard - Version 2026.07.01", href="/plantmasst")),
                dbc.NavItem(dbc.NavLink("Documentation", href="https://wang-bioinformatics-lab.github.io/GNPS2_Documentation/plantmasst/", target="_blank")),
                dbc.NavItem(dbc.NavLink("Contribute to plantMASST", href="https://wang-bioinformatics-lab.github.io/GNPS2_Documentation/plantmasst/#contributing-to-plantmasst", target="_blank"))
            ],
        navbar=True)
    ],
    color="light",
    dark=False,
    sticky="top",
    style={"paddingLeft": "2rem"},
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


def create_example_link(lib_id, use_peaks=False):
    """Create a link that will load example data via callback when clicked."""
    # Encode the lib_id and use_peaks flag in the URL hash
    hash_dict = {
        "example_lib_id": lib_id,
        "use_peaks": use_peaks
    }
    return f"/plantmasst#{urllib.parse.quote(json.dumps(hash_dict))}"


def fetch_example_data(lib_id, use_peaks=False):
    """Fetch spectrum data from API - only called when example is clicked."""
    if not use_peaks:
        return {
            "usi1": f"mzspec:GNPS:GNPS-LIBRARY:accession:{lib_id}",
            "peaks": "",
            "precursor_mz": "",
            "charge": ""
        }
    else:
        url = f"https://metabolomics-usi.gnps2.org/json/?usi1=mzspec:GNPS:GNPS-LIBRARY:accession:{lib_id}"
        print("Fetching example data from", url, file=sys.stderr)
        response = requests.get(url)
        data = response.json()

        spectrum_details = data.get("peaks", [])
        peaks_list = "\n".join(f"{mz}, {intensity}" for mz, intensity in spectrum_details)

        charge = data.get('precursor_charge')
        precursor_mz = data.get('precursor_mz')

        return {
            "usi1": "",
            "peaks": peaks_list,
            "precursor_mz": precursor_mz,
            "charge": charge
        }

# Name, ID
examples_data = [
    ("Moroidin", "CCMSLIB00005435899"),
    ("Piperlongumine", "CCMSLIB00010117596"),
    ("Sanjoinine A", "CCMSLIB00016358467"),
    ("cyFLLY", "CCMSLIB00016358468"),
    ("cyFLLY-dc", "CCMSLIB00016358469"),
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
        peaks_examples.append(html.A(text, href=create_example_link(lib_id, use_peaks=True))),
        peaks_examples.append(html.Br())

usi_examples = []
for text, lib_id in examples_data:
        usi_examples.append(html.A(text, href=create_example_link(lib_id, use_peaks=False))),
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

EXPLORER_TABLE = dash_table.DataTable(
    id="explorer-table",
    columns=[
        {"name": "TaxID (NCBI)", "id": "Taxa_NCBI", "presentation": "markdown"},
        {"name": "Species",      "id": "species"},
        {"name": "Genus",        "id": "genus"},
        {"name": "Family",       "id": "family"},
        {"name": "Order",        "id": "order"},
        {"name": "Class",        "id": "class"},
        {"name": "Phylum",       "id": "phylum"},
        {"name": "Kingdom",      "id": "kingdom"},
        {"name": "File Count",   "id": "file_count", "type": "numeric"},
    ],
    data=EXPLORER_SUMMARY_RECORDS,
    sort_action="native",
    filter_action="native",
    filter_options={"case": "insensitive"},
    page_action="native",
    page_size=25,
    style_table={"overflowX": "auto"},
    style_cell={
        "textOverflow": "ellipsis",
        "overflow": "hidden",
        "maxWidth": "220px",
        "padding": "5px",
        "fontSize": "13px",
    },
    style_header={
        "backgroundColor": "#e8f5e9",
        "fontWeight": "bold",
        "borderBottom": "2px solid #4caf50",
    },
    style_data_conditional=[
        {
            "if": {"column_id": "file_count"},
            "cursor": "pointer",
            "color": "#1565c0",
            "textDecoration": "underline",
            "fontWeight": "600",
        }
    ],
    tooltip_duration=None,
    markdown_options={"link_target": "_blank"},
)

EXPLORER_MODAL = dbc.Modal(
    [
        dbc.ModalHeader(
            html.H5(id="file-modal-title", className="modal-title"),
            close_button=True,
        ),
        dbc.ModalBody(
            html.Div([
                html.Small(
                    "Select rows then click Launch to run Classical Networking on those files.",
                    className="text-muted mb-2 d-block",
                ),
                dash_table.DataTable(
                    id="modal-file-table",
                    columns=[
                        {"name": "Filename", "id": "Filename"},
                        {"name": "MassIVE",  "id": "MassIVE"},
                        {"name": "File USI", "id": "file_usi"},
                    ],
                    data=[],
                    row_selectable="multi",
                    selected_rows=[],
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    style_table={"overflowX": "auto"},
                    style_cell={
                        "textOverflow": "ellipsis",
                        "overflow": "hidden",
                        "maxWidth": "400px",
                        "fontSize": "12px",
                        "padding": "4px",
                    },
                ),
            ])
        ),
        dbc.ModalFooter([
            dbc.Button("Select All", id="modal-select-all", color="secondary", size="sm", n_clicks=0, className="me-2"),
            dbc.Button(
                "Launch Classical Networking / Library Search Workflow",
                id="modal-networking-btn",
                href="#",
                target="_blank",
                external_link=True,
                color="success",
                size="sm",
                disabled=True,
                className="me-auto",
            ),
            dbc.Button("Close", id="file-modal-close", color="secondary", n_clicks=0),
        ]),
    ],
    id="file-modal",
    size="xl",
    is_open=False,
    scrollable=True,
)

BODY = dbc.Container(
    [
        dcc.Location(id='url', refresh=False),
        EXPLORER_MODAL,
        dbc.Tabs(
            [
                dbc.Tab(
                    label="Search",
                    tab_id="tab-search",
                    children=[
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Card(LEFT_DASHBOARD),
                                    className="col-9"
                                ),
                                dbc.Col(
                                    [
                                        dbc.Card(CONTRIBUTORS_DASHBOARD),
                                        html.Br(),
                                        dbc.Card(EXAMPLES_DASHBOARD),
                                    ],
                                    className="col-3",
                                ),
                            ],
                            style={"marginTop": 30},
                        ),
                        html.Br(),
                        dbc.Row([dbc.Card(MIDDLE_DASHBOARD)]),
                    ],
                ),
                dbc.Tab(
                    label="plantMASST Explorer",
                    tab_id="tab-explorer",
                    children=[
                        html.Br(),
                        dbc.Card(
                            [
                                dbc.CardHeader(html.H5("plantMASST Explorer — Browse by Taxon")),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    html.P(
                                                        "Browse all plant taxa represented in the plantMASST database. "
                                                        "Click any value in the File Count column to see the list of "
                                                        "files associated with that taxon.",
                                                        className="mb-0",
                                                    ),
                                                ),
                                                dbc.Col(
                                                    dbc.InputGroup(
                                                        [
                                                            dbc.InputGroupText("Group counts by"),
                                                            dbc.Select(
                                                                id="explorer-level-select",
                                                                options=[
                                                                    {"label": LEVEL_LABELS[c], "value": c}
                                                                    for c in LEVEL_COLUMNS
                                                                ],
                                                                value=DEFAULT_LEVEL,
                                                            ),
                                                        ],
                                                        size="sm",
                                                    ),
                                                    width="auto",
                                                ),
                                                dbc.Col(
                                                    dbc.Button(
                                                        "Download Table (TSV)",
                                                        id="explorer-download-btn",
                                                        color="primary",
                                                        size="sm",
                                                        n_clicks=0,
                                                    ),
                                                    width="auto",
                                                ),
                                                dbc.Col(
                                                    dbc.Button(
                                                        "Download Filtered Table (TSV)",
                                                        id="explorer-download-filtered-btn",
                                                        color="secondary",
                                                        size="sm",
                                                        n_clicks=0,
                                                    ),
                                                    width="auto",
                                                    className="ms-auto text-end",
                                                ),
                                            ],
                                            className="align-items-center mb-2",
                                        ),
                                        dcc.Download(id="explorer-download"),
                                        dcc.Download(id="explorer-download-filtered"),
                                        EXPLORER_TABLE,
                                    ]
                                ),
                            ]
                        ),
                    ],
                ),
            ],
            id="main-tabs",
            active_tab="tab-search",
            style={"marginTop": "20px"},
        ),
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

    # Check if this is an example link being clicked
    if "example_lib_id" in query_dict:
        lib_id = query_dict.get("example_lib_id")
        use_peaks = query_dict.get("use_peaks", False)
        # Fetch the example data only when clicked
        example_data = fetch_example_data(lib_id, use_peaks)
        usi1 = example_data.get("usi1", '')
        peaks = example_data.get("peaks", '')
        precursor_mz = example_data.get("precursor_mz", '')
        charge = example_data.get("charge", '')
    else:
        # Normal parameter extraction
        usi1 = _get_url_param(query_dict, "usi1", 'mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00000085687')
        peaks = _get_url_param(query_dict, "peaks", '')
        precursor_mz = _get_url_param(query_dict, "precursor_mz", '')
        charge = _get_url_param(query_dict, "charge", '')
    
    max_peaks = _get_url_param(query_dict, "max_peaks", None)
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
                Output('loading-output-23', 'children')
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

@dash_app.callback(
    [
        Output("file-modal", "is_open"),
        Output("modal-file-table", "data"),
        Output("file-modal-title", "children"),
        Output("modal-file-table", "selected_rows"),
        Output("modal-file-table", "filter_query"),
        Output("explorer-table", "active_cell"),
    ],
    [
        Input("explorer-table", "active_cell"),
        Input("file-modal-close", "n_clicks"),
        Input("file-modal", "is_open"),
    ],
    prevent_initial_call=True,
)
def toggle_file_modal(active_cell, close_clicks, is_open):
    triggered = ctx.triggered_id

    if triggered == "file-modal-close":
        # Clear active_cell/filter so clicking the same cell again after
        # closing will register as a change and re-open the modal fresh.
        return False, dash.no_update, dash.no_update, [], "", None

    if triggered == "file-modal":
        # is_open changed without going through file-modal-close: this is the
        # built-in header "x" button, a backdrop click, or Escape, none of
        # which run our Python callback on their own. Treat a resulting
        # False the same as an explicit close so state doesn't go stale.
        if is_open:
            return (dash.no_update,) * 6
        return dash.no_update, dash.no_update, dash.no_update, [], "", None

    if triggered == "explorer-table" and active_cell and active_cell.get("column_id") == "file_count":
        rid = active_cell["row_id"]
        level = rid.split("::", 1)[0]
        taxids = LEVEL_ROW_TAXIDS.get(level, {}).get(rid, [])
        label = LEVEL_ROW_LABELS.get(level, {}).get(rid, "")

        if level == "Taxa_NCBI":
            taxid = taxids[0] if taxids else label
            extra = SPECIES_BY_TAXID.get(taxid) or GENUS_BY_TAXID.get(taxid) or ""
            extra = "" if extra == "Unknown" else extra
            title = f"Files for TaxID {taxid}" + (f" — {extra}" if extra else "")
        else:
            title = f"Files for {LEVEL_LABELS.get(level, level)}: {label}"

        files = []
        for taxid in taxids:
            files.extend(FILE_LISTS.get(taxid, []))

        return True, files, title, [], "", dash.no_update

    return (dash.no_update,) * 6


@dash_app.callback(
    Output("explorer-table", "data"),
    Input("explorer-level-select", "value"),
)
def update_explorer_level(level):
    return LEVEL_TABLES.get(level, LEVEL_TABLES[DEFAULT_LEVEL])


@dash_app.callback(
    Output("explorer-download", "data"),
    Input("explorer-download-btn", "n_clicks"),
    prevent_initial_call=True,
)
def download_explorer_table(n_clicks):
    return dcc.send_data_frame(
        EXPLORER_EXPORT_DF.to_csv, "plantmasst_explorer_table.tsv", sep="\t", index=False
    )


@dash_app.callback(
    Output("explorer-download-filtered", "data"),
    Input("explorer-download-filtered-btn", "n_clicks"),
    State("explorer-level-select", "value"),
    prevent_initial_call=True,
)
def download_explorer_filtered_table(n_clicks, level):
    export_df = LEVEL_EXPORT_DFS.get(level, LEVEL_EXPORT_DFS[DEFAULT_LEVEL])
    filename = f"plantmasst_explorer_table_{level.lower()}.tsv"
    return dcc.send_data_frame(export_df.to_csv, filename, sep="\t", index=False)


@dash_app.callback(
    Output("modal-file-table", "selected_rows"),
    Input("modal-select-all", "n_clicks"),
    [State("modal-file-table", "derived_virtual_indices"),
     State("modal-file-table", "data"),
     State("modal-file-table", "selected_rows")],
    prevent_initial_call=True,
)
def toggle_select_all(n_clicks, virtual_indices, data, selected_rows):
    # derived_virtual_indices holds the indices (into data) of rows that
    # currently pass the table's filter; fall back to all rows if unfiltered.
    visible_indices = virtual_indices if virtual_indices is not None else list(range(len(data or [])))
    if visible_indices and set(selected_rows or []) != set(visible_indices):
        return list(visible_indices)
    return []


@dash_app.callback(
    [Output("modal-networking-btn", "href"),
     Output("modal-networking-btn", "disabled")],
    Input("modal-file-table", "selected_rows"),
    State("modal-file-table", "data"),
    prevent_initial_call=True,
)
def update_networking_link(selected_rows, data):
    if not selected_rows or not data:
        return "#", True
    usis = []
    for i in selected_rows:
        if i >= len(data):
            continue
        row = data[i]
        usi = row["file_usi"]
        # Append the file extension (from the Filename column) to the USI so
        # the downstream USI hash points at the actual file.
        ext = os.path.splitext(row.get("Filename", ""))[1]
        if ext and not usi.endswith(ext):
            usi += ext
        usis.append(usi)
    if not usis:
        return "#", True
    usi_string = "\\n".join(usis)
    fragment = '{{"usi": "{}"}}'.format(usi_string).replace('"', '%22').replace(' ', '%20')
    return "https://gnps2.org/workflowinput?workflowname=classical_networking_workflow#" + fragment, False


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
