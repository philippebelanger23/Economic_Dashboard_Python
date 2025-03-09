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
                                # Top row with two graphs
                                dbc.Col(
                                    [
                                        # Sector Rotation Quadrant (Top Left)
                                        dcc.Graph(
                                            id="sector-rotation-quadrant",
                                            style={"height": "40vh"},
                                            config={
                                                "displayModeBar": True,
                                                "displaylogo": False,
                                                "modeBarButtonsToRemove": [
                                                    "lasso2d",
                                                    "select2d",
                                                ],
                                            },
                                        ),
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        # Volume Analysis (Top Right)
                                        dcc.Graph(
                                            id="volume-analysis",
                                            style={"height": "40vh"},
                                            config={
                                                "displayModeBar": True,
                                                "displaylogo": False,
                                            },
                                        ),
                                    ],
                                    width=6,
                                ),
                            ],
                            style={"margin-top": "10px"},
                        ),
                        dbc.Row(
                            [
                                # Bottom row with two graphs
                                dbc.Col(
                                    [
                                        # Relative Performance (Bottom Left)
                                        dcc.Graph(
                                            id="relative-performance",
                                            style={"height": "40vh"},
                                            config={
                                                "displayModeBar": True,
                                                "displaylogo": False,
                                            },
                                        ),
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        # Relative Valuation (Bottom Right)
                                        dcc.Graph(
                                            id="relative-valuation",
                                            style={"height": "40vh"},
                                            config={
                                                "displayModeBar": True,
                                                "displaylogo": False,
                                            },
                                        ),
                                    ],
                                    width=6,
                                ),
                            ],
                            style={"margin-top": "10px"},
                        ),
                    ],
                ),
                dcc.Tab(
                    label="News",
                    value="tab-news",
                    children=[rss_news],
                ),
            ],
        ),
    ],
    fluid=True,
)