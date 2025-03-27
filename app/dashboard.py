"""
Economic Indicators Dashboard - Main Application.

This module initializes the Dash application, sets up the layout,
and registers necessary callbacks for the dashboard functionality.
"""
import sys
import os
from pathlib import Path

# Ensure proper module imports by adding the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Third-party imports
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc

# Local imports
from components.sidebar import sidebar
from components.graphs import content, register_sector_callbacks
from app.callbacks import register_callbacks

# Initialize the Dash app with Bootstrap styling
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Set up the app layout with responsive container
app.layout = html.Div(
    [
        # Store component for maintaining state
        dcc.Store(id="funds-flow-selected-period", data="12W"),
        
        # Main container with sidebar and content
        dbc.Container(
            [
                dbc.Row(
                    [
                        # Sidebar (3/12 of width)
                        dbc.Col(sidebar, width=3, id="sidebar"),
                        
                        # Main content area (9/12 of width)
                        dbc.Col(
                            dcc.Loading(
                                id="loading",
                                type="default",
                                children=content
                            ),
                            width=9,
                            id="content",
                        ),
                    ],
                    className="dbc-row",
                ),
                
                # Error message container
                html.Div(
                    id="error-message",
                    style={"color": "red", "text-align": "center"}
                ),
            ],
            fluid=True,
            id="main-container",
        )
    ]
)

# Register all callbacks
register_callbacks(app)  # Register main app callbacks
register_sector_callbacks(app)  # Register sector analysis callbacks

# Run server if executed directly
if __name__ == "__main__":
    app.run_server(debug=True)
