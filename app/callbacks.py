# app/callbacks.py (corrected version)
# Standard library imports
import json
import math
import dash_table
from datetime import datetime
from dash import html

# Third-party imports
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output, ALL, MATCH, State
from dash.exceptions import PreventUpdate
import numpy as np

# Local imports
from config.settings import RECESSIONS_FILE, RSS_FEED_URLS
from data.data_fetcher import fetch_rss_feed, get_all_next_release_dates
from data.data_processing import get_economic_data
from data.mappings import INDICATORS, INDICATOR_GROUPS
from components.sidebar import (
    create_economics_sidebar,
    create_funds_flow_sidebar,
    create_news_sidebar,
)

# -------------------
# Global Data Loading
# -------------------
economic_data = get_economic_data()

with open(RECESSIONS_FILE, "r") as f:
    recessions = json.load(f)

with open("data/events.json", "r") as f:
    key_events = json.load(f)

next_release_dates = get_all_next_release_dates()

# -------------------
# Helper Functions
# -------------------
def months_to_date(months):
    start_date = pd.to_datetime("1990-01-01")
    year = 1990 + (months // 12)
    month = (months % 12) + 1
    date = pd.to_datetime(f"{year}-{month:02d}-01")
    return date

def colname(ind, trans, for_display=False):
    base = INDICATORS.get(ind, {}).get("description", ind) if for_display else ind
    if trans == "raw":
        return base
    elif trans == "mom":
        return f"{base} MoM (%)"
    elif trans == "qoq":
        return f"{base} QoQ (%)"
    else:  # yoy
        return f"{base} YoY (%)"

def create_graph(data, col, graph_type):
    """Create a Plotly graph for the given data column and graph type.

    Args:
        data (pandas.DataFrame): DataFrame containing the data.
        col (str): Column name to plot.
        graph_type (str): Type of graph ('line', 'bar', 'area').

    Returns:
        plotly.graph_objs.Figure: The generated Plotly figure.
    """
    display_col = colname(
        col.split()[0] if "YoY" in col else col,
        "yoy" if "YoY" in col else "raw",
        for_display=True,
    )
    # Wrap title by inserting <br> after a certain number of characters or words
    max_chars_per_line = 50
    wrapped_title = ""
    current_line = ""
    for word in f"{display_col} Over Time".split():
        if len(current_line) + len(word) > max_chars_per_line:
            wrapped_title += current_line + "<br>"
            current_line = word
        else:
            current_line += (" " if current_line else "") + word
    wrapped_title += current_line

    if graph_type == "line":
        fig = px.line(
            data,
            x=data.index,
            y=col,
            title=wrapped_title,
            line_shape="spline"  # Smooths the line with rounded corners
        )
    elif graph_type == "bar":
        fig = px.bar(data, x=data.index, y=col, title=wrapped_title)
    else:  # area
        fig = px.area(data, x=data.index, y=col, title=wrapped_title)

    fig.update_traces(
        hovertemplate="<b>%{y:.2f}</b><br>Date: %{x|%Y-%m-%d}<extra></extra>",
        line=dict(width=2, shape="spline")  # Ensure smooth line and set width
    )
    fig.update_layout(
        title_font=dict(size=18, weight="bold"),
        title_x=0.5,
        xaxis_title="",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, autorange=True),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig

def add_annotations(fig, indicator, show_recessions, show_events, start_dt, end_dt):
    series_id = INDICATORS.get(indicator, {}).get("id", None)
    next_release = next_release_dates.get(series_id, "Unknown") if series_id else "Unknown"

    fig.add_annotation(
        text=f"Next Release: {next_release}",
        xref="paper",
        yref="paper",
        x=1,
        y=-0.1,
        showarrow=False,
        font={"size": 10, "color": "gray"},
    )
    fig.update_layout(margin={"b": 80})

    if show_recessions:
        for rec in recessions:
            peak, trough = rec.get("peak", ""), rec.get("trough", "")
            if peak and trough:
                rs, re = pd.to_datetime(peak), pd.to_datetime(trough)
                if re >= start_dt and rs <= end_dt:
                    fig.add_vrect(
                        x0=max(rs, start_dt),
                        x1=min(re, end_dt),
                        fillcolor="grey",
                        opacity=0.2,
                        layer="below",
                        line_width=0,
                    )
    if show_events:
        for event in key_events:
            event_date = pd.to_datetime(event["date"])
            if start_dt <= event_date <= end_dt:
                event_date_ms = int(event_date.timestamp() * 1000)
                fig.add_vline(
                    x=event_date_ms,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=event["event"],
                    annotation_position="top",
                    annotation={"font_size": 10, "font_color": "red"},
                )
    return fig

# -------------------
# Callbacks
# -------------------
def register_callbacks(app):
    @app.callback(
        Output("graph-container", "children"),
        Input("indicator-group-selector", "value"),
    )
    def update_graph_layout(group):
        num_graphs = len(INDICATOR_GROUPS.get(group, []))
        if num_graphs == 0:
            return [html.Div("No indicators available for this group.")]

        if num_graphs % 2 == 0:
            graphs_per_row = num_graphs // 2
            first_row_count = graphs_per_row
            second_row_count = graphs_per_row
        else:
            first_row_count = math.ceil(num_graphs / 2)
            second_row_count = num_graphs - first_row_count

        num_rows = 1 if num_graphs <= first_row_count else 2
        first_row_width = 12 // first_row_count if first_row_count > 0 else 12
        second_row_width = 12 // second_row_count if second_row_count > 0 else 12

        available_height = 80
        graph_height = available_height / num_rows

        graph_cards = []
        for i in range(1, num_graphs + 1):
            default_indicator = (
                INDICATOR_GROUPS[group][i - 1]
                if i <= len(INDICATOR_GROUPS[group])
                else INDICATOR_GROUPS[group][0]
            )
            card = dbc.Card(
                [
                    dbc.CardHeader(
                        dbc.Row(
                            [
                                dbc.Col(
                                    dcc.Dropdown(
                                        id={"type": "indicator-selector", "index": i},
                                        value=default_indicator,
                                        clearable=False,
                                        style={"width": "100%"},
                                    ),
                                    width=6,
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id={"type": "transform-selector", "index": i},
                                        options=[
                                            {"label": "Raw", "value": "raw"},
                                            {"label": "MoM %", "value": "mom"},
                                            {"label": "QoQ %", "value": "qoq"},
                                            {"label": "YoY %", "value": "yoy"},
                                        ],
                                        value="raw",
                                        clearable=False,
                                        style={"width": "100%"},
                                    ),
                                    width=3,
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id={"type": "graph-type-selector", "index": i},
                                        options=[
                                            {"label": "Line", "value": "line"},
                                            {"label": "Bar", "value": "bar"},
                                            {"label": "Area", "value": "area"},
                                        ],
                                        value="line",
                                        clearable=False,
                                        style={"width": "100%"},
                                    ),
                                    width=3,
                                ),
                            ],
                            align="center",
                        ),
                        style={"padding": "5px"},
                    ),
                    dbc.CardBody(
                        [
                            dcc.Graph(
                                id={"type": "indicator", "index": i},
                                config={"displayModeBar": False},
                                style={
                                    "height": f"{graph_height}vh",
                                    "width": "100%",
                                    "margin": "0",
                                },
                            ),
                            dcc.Store(id={"type": "zoom-store", "index": i}, data=None),
                        ],
                        style={"padding": "5px"},
                    ),
                ],
                id=f"graph{i}-card",
                style={"margin": "0", "padding": "0"},
            )

            col_width = first_row_width if i <= first_row_count else second_row_width
            graph_cards.append(dbc.Col(card, width=col_width))

        rows = []
        if first_row_count > 0:
            rows.append(dbc.Row(graph_cards[:first_row_count], className="g-1"))
        if second_row_count > 0:
            rows.append(dbc.Row(graph_cards[first_row_count:], className="g-1"))

        return rows

    @app.callback(
        Output({"type": "zoom-store", "index": MATCH}, "data"),
        Input({"type": "indicator", "index": MATCH}, "relayoutData"),
        State({"type": "zoom-store", "index": MATCH}, "data"),
    )
    def update_zoom_state(relayout_data, previous_zoom):
        if relayout_data is None:
            return previous_zoom

        if "autosize" in relayout_data and relayout_data["autosize"]:
            return None

        print(f"Relayout data: {relayout_data}")

        if "xaxis.range[0]" in relayout_data and "xaxis.range[1]" in relayout_data:
            return {
                "xaxis.range": [
                    relayout_data["xaxis.range[0]"],
                    relayout_data["xaxis.range[1]"],
                ]
            }
        if "xaxis.range" in relayout_data and len(relayout_data["xaxis.range"]) == 2:
            return {
                "xaxis.range": [
                    relayout_data["xaxis.range"][0],
                    relayout_data["xaxis.range"][1],
                ]
            }

        return previous_zoom

    @app.callback(
        Output({"type": "indicator", "index": MATCH}, "figure"),
        Input({"type": "indicator-selector", "index": MATCH}, "value"),
        Input({"type": "transform-selector", "index": MATCH}, "value"),
        Input({"type": "graph-type-selector", "index": MATCH}, "value"),
        Input("date-picker", "start_date"),
        Input("date-picker", "end_date"),
        Input("toggle-recessions", "value"),
        Input("toggle-events", "value"),
        Input("date-range-slider", "value"),
        State({"type": "zoom-store", "index": MATCH}, "data"),
    )
    def update_individual_graph(
        indicator,
        transform,
        graph_type,
        start_date,
        end_date,
        toggle_recessions,
        toggle_events,
        slider_range,
        zoom_state,
    ):
        today = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
        start_months, end_months = slider_range
        start_dt = months_to_date(start_months)
        end_dt = months_to_date(end_months)
        end_dt = min(end_dt, today)

        picker_start = pd.to_datetime(start_date)
        picker_end = pd.to_datetime(end_date)
        start_dt = max(start_dt, picker_start)
        end_dt = min(end_dt, picker_end)

        data = economic_data.loc[start_dt:end_dt]
        if data.empty:
            return {}

        col = colname(indicator, transform)
        if col not in data.columns:
            return {}

        fig = create_graph(data, col, graph_type)
        fig = add_annotations(
            fig, indicator, toggle_recessions, toggle_events, start_dt, end_dt
        )

        if zoom_state and "xaxis.range" in zoom_state:
            x_start, x_end = zoom_state["xaxis.range"]
            fig.update_xaxes(range=[x_start, x_end])
            fig.update_yaxes(autorange=True)
        else:
            fig.update_yaxes(autorange=True)

        print(f"Final y-axis layout: {fig.layout.yaxis}")

        return fig

    @app.callback(
        Output({"type": "indicator-selector", "index": MATCH}, "options"),
        Output({"type": "indicator-selector", "index": MATCH}, "value"),
        Input("indicator-group-selector", "value"),
        Input({"type": "indicator-selector", "index": MATCH}, "id"),
    )
    def update_indicator_options(group, selector_id):
        group_indicators = INDICATOR_GROUPS.get(group, [])
        if not group_indicators:
            return [], None

        options = [
            {
                "label": INDICATORS[i]["description"],
                "value": i,
                "title": INDICATORS[i]["description"],
            }
            for i in group_indicators
        ]
        idx = selector_id['index'] - 1
        default = (
            group_indicators[idx]
            if idx < len(group_indicators)
            else group_indicators[0]
        )
        return options, default

    @app.callback(
        Output("date-picker", "start_date"),
        Output("date-picker", "end_date"),
        Input("date-range-slider", "value"),
        prevent_initial_call=True
    )
    def update_date_picker(slider_range):
        today = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
        start_months, end_months = slider_range
        start_date = months_to_date(start_months).strftime("%Y-%m-%d")
        end_date = min(months_to_date(end_months), today).strftime("%Y-%m-%d")
        return start_date, end_date

    @app.callback(
        Output("date-range-display", "children"), Input("date-range-slider", "value")
    )
    def update_date_range_display(slider_range):
        start_months, end_months = slider_range
        start_date = months_to_date(start_months)
        end_date = months_to_date(end_months)
        start_str = start_date.strftime("%Y-%m")
        end_str = end_date.strftime("%Y-%m")
        return f"Selected Range: {start_str} to {end_str}"

    @app.callback(
        Output("last-updated", "children"),
        Output("error-message", "children"),
        Output("summary-stats", "children"),
        [
            Input({"type": "indicator-selector", "index": ALL}, "value"),
            Input({"type": "transform-selector", "index": ALL}, "value"),
            Input("date-picker", "start_date"),
            Input("date-picker", "end_date"),
            Input("date-range-slider", "value"),
        ],
    )
    def update_summary(indicators, transformations, start_date, end_date, slider_range):
        today = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
        print("economic_data columns:", economic_data.columns.tolist())
        start_months, end_months = slider_range
        start_dt = months_to_date(start_months)
        end_dt = months_to_date(end_months)
        end_dt = min(end_dt, today)

        picker_start = pd.to_datetime(start_date)
        picker_end = pd.to_datetime(end_date)
        start_dt = max(start_dt, picker_start)
        end_dt = min(end_dt, picker_end)

        data = economic_data.loc[start_dt:end_dt].dropna()
        if data.empty:
            return (
                "No data available",
                "Error: No data for selected range",
                dash_table.DataTable(
                    columns=[{"name": i, "id": i} for i in ["Indicator", "Value", "Δ MoM", "Δ YoY"]],
                    data=[],
                ),
            )

        cols = [colname(ind, trans) for ind, trans in zip(indicators, transformations)]
        missing_cols = [c for c in cols if c and c not in data.columns]
        if missing_cols:
            return (
                "No data available",
                f"Error: Missing columns {missing_cols}",
                dash_table.DataTable(
                    columns=[{"name": i, "id": i} for i in ["Indicator", "Value", "Δ MoM", "Δ YoY"]],
                    data=[],
                ),
            )

        last_date = data.index.max().strftime("%Y-%m-%d")

        table_data = []
        for ind, trans, col in zip(indicators, transformations, cols):
            if col in data.columns:
                latest_value = data[col].iloc[-1]
                mom_col = colname(ind, "mom")
                yoy_col = colname(ind, "yoy")
                change_mom = data[mom_col].iloc[-1] if mom_col in data.columns and len(data) > 1 else 0
                change_yoy = data[yoy_col].iloc[-1] if yoy_col in data.columns and len(data) > 12 else 0

                # Truncate long indicator names with ...
                indicator_name = INDICATORS[ind]["description"]
                max_length = 20  # Adjust this value based on your preference
                truncated_indicator = (indicator_name[:max_length] + "...") if len(indicator_name) > max_length else indicator_name

                table_data.append({
                    "Indicator": truncated_indicator,
                    "Value": f"{latest_value:.2f}",
                    "Δ MoM": f"{change_mom:.2f}%",
                    "Δ YoY": f"{change_yoy:.2f}%",
                })

        summary_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ["Indicator", "Value", "Δ MoM", "Δ YoY"]],
            data=table_data,
            style_table={},
            style_cell={
                "textAlign": "left",
                "padding": "5px",
                "fontSize": "14px",
                "whiteSpace": "normal",  # Allow text to wrap
                "overflow": "hidden",    # Hide overflow
                "textOverflow": "ellipsis",  # Add ... for truncated text
                "maxWidth": "150px",     # Set a max width for the Indicator column
            },
            style_header={
                "backgroundColor": "rgb(230, 230, 230)",
                "fontWeight": "bold",
            },
            style_data_conditional=[
                {
                    "if": {"filter_query": "{Δ MoM} < 0"},
                    "color": "red",
                },
                {
                    "if": {"filter_query": "{Δ YoY} < 0"},
                    "color": "red",
                },
            ],
        )

        return f"Last Updated: {last_date}", "", summary_table

    @app.callback(
        Output("date-range-slider", "value"),
        [
            Input("btn-last-3mo", "n_clicks"),
            Input("btn-last-6mo", "n_clicks"),
            Input("btn-last-12mo", "n_clicks"),
            Input("btn-last-24mo", "n_clicks")
        ],
        [State("date-range-slider", "value")],
        prevent_initial_call=True
    )
    def update_date_range_from_buttons(n_clicks_3mo, n_clicks_6mo, n_clicks_12mo, n_clicks_24mo, current_range):
        ctx = callback_context
        if not ctx.triggered:
            return current_range

        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        today = datetime.today()
        current_month = (today.year - 1990) * 12 + today.month - 1  # Months since 1990

        if triggered_id == "btn-last-3mo" and n_clicks_3mo:
            end_month = current_month
            start_month = max(0, end_month - 3)
        elif triggered_id == "btn-last-6mo" and n_clicks_6mo:
            end_month = current_month
            start_month = max(0, end_month - 6)
        elif triggered_id == "btn-last-12mo" and n_clicks_12mo:
            end_month = current_month
            start_month = max(0, end_month - 12)
        elif triggered_id == "btn-last-24mo" and n_clicks_24mo:
            end_month = current_month
            start_month = max(0, end_month - 24)
        else:
            return current_range

        return [start_month, end_month]

    @app.callback(
        Output({"type": "news-list", "feed": ALL}, "children"),
        [Input({"type": "refresh-button", "feed": ALL}, "n_clicks")],
        prevent_initial_call=False
    )
    def update_all_rss_news(n_clicks):
        feeds = list(RSS_FEED_URLS.keys())
        all_news_lists = []
        
        for feed_key in feeds:
            articles = fetch_rss_feed(RSS_FEED_URLS[feed_key])
            if not articles:
                news_list = [html.Li("Failed to load articles.", style={"color": "red"})]
            else:
                news_list = [
                    html.Li(
                        [
                            html.Div(
                                [
                                    html.A(
                                        article["title"],
                                        href=article["link"],
                                        target="_blank",
                                        style={
                                            "font-weight": "bold",
                                            "color": "#007bff",
                                            "text-decoration": "none",
                                        },
                                        className="rss-title",
                                    ),
                                    html.Div(
                                        f"Published: {article['pub_date']}",
                                        style={"font-size": "12px", "color": "gray", "margin-top": "2px"},
                                    ),
                                    html.Div(
                                        article["summary"],
                                        style={"font-size": "14px", "color": "#333", "margin-top": "4px"},
                                    ),
                                ],
                                style={"margin-bottom": "10px"},
                            )
                        ]
                    )
                    for article in articles
                ]
            all_news_lists.append(news_list)
        
        return all_news_lists

    @app.callback(
        Output("summary-stats-container", "children"),
        [
            Input({"type": "indicator-selector", "index": ALL}, "value"),
            Input({"type": "transform-selector", "index": ALL}, "value"),
            Input("date-picker", "start_date"),
            Input("date-picker", "end_date"),
            Input("date-range-slider", "value"),
        ],
    )
    def update_summary_tab(indicators, transformations, start_date, end_date, slider_range):
        # Reuse the existing update_summary logic
        last_updated, error_message, summary_table = update_summary(
            indicators, transformations, start_date, end_date, slider_range
        )
        return [
            html.P(last_updated, style={"text-align": "center", "margin-bottom": "10px"}),
            html.Div(error_message, style={"color": "red", "text-align": "center", "margin-bottom": "10px"}) if error_message else "",
            summary_table,
        ]

    @app.callback(
        Output("sidebar-content", "children"),
        Input("dashboard-tabs", "value")
    )
    def update_sidebar(selected_tab):
        if selected_tab == "tab-economics":
            return create_economics_sidebar()
        elif selected_tab == "tab-funds-flow":
            return create_funds_flow_sidebar()
        elif selected_tab == "tab-news":
            return create_news_sidebar()
        return create_economics_sidebar()  # Default to economics sidebar

    @app.callback(
        Output("funds-flow-selected-period", "data"),
        Output("funds-flow-period-info", "children"),
        [
            Input("btn-period-4w", "n_clicks"),
            Input("btn-period-8w", "n_clicks"),
            Input("btn-period-12w", "n_clicks"),
            Input("btn-period-26w", "n_clicks"),
            Input("btn-period-39w", "n_clicks"),
            Input("btn-period-52w", "n_clicks"),
        ],
        State("funds-flow-selected-period", "data"),
        prevent_initial_call=False
    )
    def update_funds_flow_period(n4w, n8w, n12w, n26w, n39w, n52w, current_period):
        ctx = callback_context
        if not ctx.triggered:
            # Return default values on initial load
            default_period = "12W"
            return default_period, "12 Weeks (3 Months)"
            
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        period_mapping = {
            "btn-period-4w": "4W",
            "btn-period-8w": "8W",
            "btn-period-12w": "12W",
            "btn-period-26w": "26W",
            "btn-period-39w": "39W",
            "btn-period-52w": "52W",
        }
        
        selected_period = period_mapping.get(button_id, current_period or "12W")
        
        # Create a more descriptive text for the display
        period_descriptions = {
            "4W": "4 Weeks (1 Month)",
            "8W": "8 Weeks (2 Months)",
            "12W": "12 Weeks (3 Months)",
            "26W": "26 Weeks (6 Months)",
            "39W": "39 Weeks (9 Months)",
            "52W": "52 Weeks (1 Year)",
        }
        
        period_info = period_descriptions.get(selected_period, selected_period)
        
        return selected_period, period_info
        
    @app.callback(
        Output("funds-flow-container", "children"),
        [
            Input("dashboard-tabs", "value"),
            Input("funds-flow-selected-period", "data")
        ]
    )
    def update_funds_flow(current_tab, selected_period):
        # Only proceed if we're on the funds flow tab
        if current_tab != "tab-funds-flow":
            raise PreventUpdate
            
        # Handle the case when no period is selected
        if not selected_period:
            selected_period = "12W"  # Default to 12 weeks
            
        # Return a placeholder message with the selected period
        return html.Div(
            [
                html.H3("Funds Flow Analysis", className="text-center mb-4"),
                html.H5(f"Selected Period: {selected_period}", className="text-center mb-3"),
                html.P("The visualization for this tab is being built.", className="text-center")
            ],
            style={"padding": "20px", "margin-top": "50px"}
        )

    @app.callback(
        [
            Output("btn-period-4w", "color"),
            Output("btn-period-8w", "color"),
            Output("btn-period-12w", "color"),
            Output("btn-period-26w", "color"),
            Output("btn-period-39w", "color"),
            Output("btn-period-52w", "color"),
            Output("btn-period-4w", "outline"),
            Output("btn-period-8w", "outline"),
            Output("btn-period-12w", "outline"),
            Output("btn-period-26w", "outline"),
            Output("btn-period-39w", "outline"),
            Output("btn-period-52w", "outline"),
        ],
        Input("funds-flow-selected-period", "data")
    )
    def update_period_button_styles(selected_period):
        colors = ["primary"] * 6
        outlines = [True] * 6
        
        if not selected_period:
            selected_period = "12W"
        
        button_indices = {
            "4W": 0, "8W": 1, "12W": 2,
            "26W": 3, "39W": 4, "52W": 5
        }
        
        if selected_period in button_indices:
            idx = button_indices[selected_period]
            outlines[idx] = False
        
        return (
            colors[0], colors[1], colors[2], colors[3], colors[4], colors[5],
            outlines[0], outlines[1], outlines[2], outlines[3], outlines[4], outlines[5]
        )

    @app.callback(
        [
            Output("funds-flow-quadrant", "figure"),
            Output("funds-flow-stats", "children"),
        ],
        [
            Input("funds-flow-selected-period", "data"),
            Input("funds-flow-momentum-type", "value"),
            Input("funds-flow-show-labels", "value"),
            Input("funds-flow-show-trends", "value"),
            Input("funds-flow-bubble-size", "value"),
        ]
    )
    def update_funds_flow_quadrant(
        selected_period,
        momentum_type,
        show_labels,
        show_trends,
        bubble_size,
    ):
        # For now, create sample data (replace with real data later)
        np.random.seed(None)  # Allow random data each time
        n_points = 11  # 11 sectors in S&P 500
        
        # Sample data
        sectors = [
            "Techn.", "Healthcare", "Financials", "Cons. Disc.",
            "Comm. Services", "Industrials", "Cons. Staples",
            "Energy", "Materials", "Real Estate", "Utilities"
        ]
        
        # Generate different data based on analysis type
        base_spread = 10  # Reduced spread for tighter data clustering around 100
        if momentum_type == "rotation":
            rel_strength = 100 + np.random.normal(0, base_spread/2, n_points)
            rel_momentum = 100 + np.random.normal(0, base_spread/2, n_points)
            x_title = "Relative Strength"
            y_title = "Relative Momentum"
            title_prefix = "Sector Rotation"
        elif momentum_type == "performance":
            rel_strength = 100 + np.random.normal(2, base_spread/3, n_points)  # Slight positive bias
            rel_momentum = 100 + np.random.normal(1, base_spread/3, n_points)
            x_title = "Standard Error"
            y_title = "Relative Return"
            title_prefix = "SPY Performance"
        else:  # valuation
            rel_strength = 100 + np.random.normal(-1, base_spread/3, n_points)  # Slight negative bias
            rel_momentum = 100 + np.random.normal(0, base_spread/3, n_points)
            x_title = "Relative P/E"
            y_title = "Relative Growth"
            title_prefix = "SPY Valuation"
        
        # Ensure values stay within desired range (90-110)
        rel_strength = np.clip(rel_strength, 90, 110)
        rel_momentum = np.clip(rel_momentum, 90, 110)
        
        # Calculate dynamic range based on actual data spread
        min_x = min(rel_strength)
        max_x = max(rel_strength)
        min_y = min(rel_momentum)
        max_y = max(rel_momentum)
        
        # Calculate the range needed for each axis independently
        x_range = max(abs(max_x - 100), abs(100 - min_x))
        y_range = max(abs(max_y - 100), abs(100 - min_y))
        
        # Add minimal padding
        x_padding = x_range * 0.05  # 5% padding
        y_padding = y_range * 0.05  # 5% padding
        
        # Calculate final ranges with padding, but cap at 10 units from 100
        x_range_final = min(max(x_range + x_padding, 5), 10)
        y_range_final = min(max(y_range + y_padding, 5), 10)
        
        # Calculate grid line spacing - use smaller increments
        x_dtick = 2  # Show grid lines every 2 units
        y_dtick = 2  # Show grid lines every 2 units
        
        # For label positioning, use consistent range for alignment
        label_range = 10  # Fixed range for labels
        label_offset = label_range * 0.85  # Move closer to the edges
        
        sizes = np.random.uniform(20, 50, n_points) if bubble_size == "equal" else np.random.uniform(20, 100, n_points)
        
        # Create the scatter plot
        fig = go.Figure()

        # Add quadrant lines at 100
        fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(x=100, line_dash="dash", line_color="gray", opacity=0.5)

        # Define colors for each quadrant
        quadrant_colors = {
            "leading": "#2ecc71",     # Green
            "improving": "#3498db",    # Blue
            "lagging": "#e74c3c",     # Red
            "weakening": "#f1c40f"    # Yellow
        }

        # Assign colors based on quadrant position
        colors = []
        for x, y in zip(rel_strength, rel_momentum):
            if x > 100 and y > 100:
                colors.append(quadrant_colors["leading"])
            elif x < 100 and y > 100:
                colors.append(quadrant_colors["improving"])
            elif x < 100 and y < 100:
                colors.append(quadrant_colors["lagging"])
            else:
                colors.append(quadrant_colors["weakening"])

        # Add the scatter plot
        fig.add_trace(
            go.Scatter(
                x=rel_strength,
                y=rel_momentum,
                mode="markers+text",
                marker=dict(
                    size=sizes,
                    color=colors,
                ),
                text=sectors,
                textposition=["top center" if y > 100 else "bottom center" for y in rel_momentum],  # Dynamic text position
                hovertemplate=(
                    "<b>%{text}</b><br>" +
                    f"{x_title}: %{{x:.1f}}<br>" +
                    f"{y_title}: %{{y:.1f}}<br>" +
                    "<extra></extra>"
                ),
            )
        )

        # Calculate label positions - place them in the corners
        if show_labels:
            # Calculate horizontal positions at 25% and 75% of the range from center
            left_x = 100 - (x_range_final * 0.75)  # 25% from left edge (or 75% from center)
            right_x = 100 + (x_range_final * 0.75)  # 75% from left edge (or 75% from center)
            # Use the same vertical spacing as before
            top_y = 100 + (y_range_final * 0.85)
            bottom_y = 100 - (y_range_final * 0.85)
            
            quadrant_labels = [
                dict(
                    x=right_x, y=top_y,
                    text="<b>LEADING</b>",
                    showarrow=False,
                    font=dict(size=14, color=quadrant_colors["leading"], weight="bold"),
                    xanchor="right",
                    yanchor="bottom"
                ),
                dict(
                    x=left_x, y=top_y,
                    text="<b>IMPROVING</b>",
                    showarrow=False,
                    font=dict(size=14, color=quadrant_colors["improving"], weight="bold"),
                    xanchor="left",
                    yanchor="bottom"
                ),
                dict(
                    x=left_x, y=bottom_y,
                    text="<b>LAGGING</b>",
                    showarrow=False,
                    font=dict(size=14, color=quadrant_colors["lagging"], weight="bold"),
                    xanchor="left",
                    yanchor="top"
                ),
                dict(
                    x=right_x, y=bottom_y,
                    text="<b>WEAKENING</b>",
                    showarrow=False,
                    font=dict(size=14, color=quadrant_colors["weakening"], weight="bold"),
                    xanchor="right",
                    yanchor="top"
                ),
            ]
            fig.update_layout(annotations=quadrant_labels)

        # Update layout with dynamic, independent axes around 100
        fig.update_layout(
            title=f"S&P 500 {title_prefix} Analysis ({selected_period})",
            xaxis=dict(
                title=x_title,
                zeroline=False,
                showgrid=True,
                gridcolor="lightgray",
                range=[100-x_range_final*1.1, 100+x_range_final*1.1],  # Add 10% extra range
                dtick=x_dtick,  # Fewer grid lines
                griddash="dot",  # Dotted grid lines
                scaleanchor="y",  # Force square aspect ratio
                scaleratio=1,
                title_standoff=25,  # Increased space between axis and title
            ),
            yaxis=dict(
                title=y_title,
                zeroline=False,
                showgrid=True,
                gridcolor="lightgray",
                range=[100-y_range_final*1.1, 100+y_range_final*1.1],  # Add 10% extra range
                dtick=y_dtick,  # Fewer grid lines
                griddash="dot",  # Dotted grid lines
                title_standoff=25,  # Increased space between axis and title
            ),
            plot_bgcolor="white",
            showlegend=False,
            margin=dict(
                l=120,   # Further increased left margin
                r=120,   # Further increased right margin
                t=120,   # Further increased top margin
                b=120,   # Further increased bottom margin
                pad=40   # Further increased padding between plot and axis labels
            ),
            autosize=True,  # Enable autosize
            height=800,    # Fixed height
        )

        # Calculate statistics with colored text
        stats = []
        for quadrant, (condition_x, condition_y, label, color) in enumerate([
            (rel_strength > 100, rel_momentum > 100, "Leading", quadrant_colors["leading"]),
            (rel_strength < 100, rel_momentum > 100, "Improving", quadrant_colors["improving"]),
            (rel_strength < 100, rel_momentum < 100, "Lagging", quadrant_colors["lagging"]),
            (rel_strength > 100, rel_momentum < 100, "Weakening", quadrant_colors["weakening"]),
        ]):
            mask = condition_x & condition_y
            count = np.sum(mask)
            sectors_in_quadrant = [s for s, m in zip(sectors, mask) if m]
            
            stats.append(
                html.Div([
                    html.Strong(f"{label}: {count}", style={"color": color, "font-weight": "900"}),
                    html.Div(", ".join(sectors_in_quadrant) if sectors_in_quadrant else "None"),
                ], className="mb-2")
            )

        return fig, html.Div(stats)