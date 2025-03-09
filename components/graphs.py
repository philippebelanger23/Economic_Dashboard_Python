# components/graphs.py
import dash_bootstrap_components as dbc
from dash import dcc, html
from components.rss_news import rss_news
from data.mappings import INDICATOR_GROUPS

content = dbc.Container(
    [
        dcc.Tabs(
            id="dashboard-tabs",
            value="tab-economics",  # Default active tab
            children=[
                dcc.Tab(
                    label="Economics",
                    value="tab-economics",
                    children=[
                        dbc.Row(
                            id="graph-container",
                            style={"margin-top": "10px"},
                        )
                    ],
                ),
                dcc.Tab(
                    label="Sector Analysis",
                    value="tab-funds-flow",
                    children=[
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        # Main quadrant graph
                                        dcc.Graph(
                                            id="funds-flow-quadrant",
                                            style={"height": "70vh"},
                                            config={
                                                "displayModeBar": True,
                                                "displaylogo": False,
                                                "modeBarButtonsToRemove": [
                                                    "lasso2d",
                                                    "select2d",
                                                ],
                                            },
                                        ),
                                        # Legend and stats below the graph
                                        dbc.Card(
                                            dbc.CardBody([
                                                html.H6("Quadrant Statistics", className="text-center"),
                                                html.Div(id="funds-flow-stats"),
                                            ]),
                                            className="mt-3",
                                        ),
                                    ],
                                    width=12,
                                ),
                            ],
                            style={"margin-top": "10px"},
                        )
                    ],
                ),
                dcc.Tab(
                    label="News Feed",
                    value="tab-news",
                    children=[
                        dbc.Row(
                            [
                                dbc.Col(rss_news, width=12),
                            ],
                            style={"margin-top": "10px"},
                        )
                    ],
                ),
            ],
            style={"margin-top": "10px"},
        )
    ],
    fluid=True,
)