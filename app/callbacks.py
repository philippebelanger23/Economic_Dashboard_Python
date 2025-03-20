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
        Output({"type": "transform-selector", "index": MATCH}, "value"),
        Output({"type": "graph-type-selector", "index": MATCH}, "value"),
        Input("indicator-group-selector", "value"),
        Input({"type": "indicator-selector", "index": MATCH}, "value"),
        Input({"type": "indicator-selector", "index": MATCH}, "id"),
    )
    def update_indicator_and_defaults(group, selected_indicator, selector_id):
        ctx = callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # If triggered by group selector
        if triggered_id == "indicator-group-selector":
            group_indicators = INDICATOR_GROUPS.get(group, [])
            if not group_indicators:
                return [], None, "raw", "line"

            options = [
                {
                    "label": INDICATORS[i]["description"],
                    "value": i,
                    "title": INDICATORS[i]["description"],
                }
                for i in group_indicators
            ]
            idx = selector_id['index'] - 1
            default_indicator = (
                group_indicators[idx]
                if idx < len(group_indicators)
                else group_indicators[0]
            )
            
            # Get default transform and graph type from INDICATORS
            default_transform = INDICATORS[default_indicator].get("default_transform", "raw")
            default_graph_type = INDICATORS[default_indicator].get("default_graph_type", "line")
            
            return options, default_indicator, default_transform, default_graph_type
            
        # If triggered by indicator selector
        else:
            if not selected_indicator:
                raise PreventUpdate
                
            # Keep existing options and selected indicator
            group_indicators = INDICATOR_GROUPS.get(group, [])
            options = [
                {
                    "label": INDICATORS[i]["description"],
                    "value": i,
                    "title": INDICATORS[i]["description"],
                }
                for i in group_indicators
            ]
            
            # Get default transform and graph type for the newly selected indicator
            default_transform = INDICATORS[selected_indicator].get("default_transform", "raw")
            default_graph_type = INDICATORS[selected_indicator].get("default_graph_type", "line")
            
            return options, selected_indicator, default_transform, default_graph_type

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
            Input("date-picker", "start_date"),
            Input("date-picker", "end_date"),
            Input("date-range-slider", "value"),
        ],
    )
    def update_summary(indicators, start_date, end_date, slider_range):
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
                    columns=[{"name": i, "id": i} for i in ["Indicator", "Raw", "MoM %", "QoQ %", "YoY %"]],
                    data=[],
                ),
            )

        table_data = []
        for ind in indicators:
            if not ind:  # Skip if indicator is None
                continue

            # Get raw value and all transformations
            raw_col = colname(ind, "raw")
            mom_col = colname(ind, "mom")
            qoq_col = colname(ind, "qoq")
            yoy_col = colname(ind, "yoy")

            if raw_col not in data.columns:
                continue

            # Get latest values for each transformation
            raw_value = data[raw_col].iloc[-1]
            mom_value = data[mom_col].iloc[-1] if mom_col in data.columns and len(data) > 1 else None
            qoq_value = data[qoq_col].iloc[-1] if qoq_col in data.columns and len(data) > 3 else None
            yoy_value = data[yoy_col].iloc[-1] if yoy_col in data.columns and len(data) > 12 else None

            # Truncate long indicator names with ...
            indicator_name = INDICATORS[ind]["description"]
            max_length = 20  # Adjust this value based on your preference
            truncated_indicator = (indicator_name[:max_length] + "...") if len(indicator_name) > max_length else indicator_name

            table_data.append({
                "Indicator": truncated_indicator,
                "Raw": f"{raw_value:,.2f}".replace(",", " "),  # Format with thousand separator using space
                "MoM %": f"{mom_value:.2f}" if mom_value is not None else "N/A",
                "QoQ %": f"{qoq_value:.2f}" if qoq_value is not None else "N/A",
                "YoY %": f"{yoy_value:.2f}" if yoy_value is not None else "N/A",
            })

        # Get the last day of the previous month for "Last Updated" date
        today = datetime.today()
        if today.month == 1:  # January
            last_month_end = datetime(today.year - 1, 12, 31)
        else:
            # Find the last day by getting the first day of current month and subtracting one day
            last_month_end = datetime(today.year, today.month, 1) - pd.Timedelta(days=1)
            
        last_date = last_month_end.strftime("%Y-%m-%d")

        summary_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ["Indicator", "Raw", "MoM %", "QoQ %", "YoY %"]],
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
            style_cell_conditional=[
                {"if": {"column_id": "Indicator"}, "textAlign": "left"},
                {"if": {"column_id": "Raw"}, "textAlign": "center"},
                {"if": {"column_id": "MoM %"}, "textAlign": "center"},
                {"if": {"column_id": "QoQ %"}, "textAlign": "center"},
                {"if": {"column_id": "YoY %"}, "textAlign": "center"},
            ],
            style_header={
                "backgroundColor": "rgb(230, 230, 230)",
                "fontWeight": "bold",
            },
            style_data_conditional=[
                {
                    "if": {"column_id": "MoM %", "filter_query": "{MoM %} < 0 && {MoM %} != 'N/A'"},
                    "color": "red",
                },
                {
                    "if": {"column_id": "QoQ %", "filter_query": "{QoQ %} < 0 && {QoQ %} != 'N/A'"},
                    "color": "red",
                },
                {
                    "if": {"column_id": "YoY %", "filter_query": "{YoY %} < 0 && {YoY %} != 'N/A'"},
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
        [
            Input("refresh-all-feeds", "n_clicks"),
            Input("articles-per-feed", "value")
        ],
        prevent_initial_call=False
    )
    def update_all_rss_news(n_clicks, articles_per_feed):
        feeds = list(RSS_FEED_URLS.keys())
        all_news_lists = []
        
        for feed_key in feeds:
            articles = fetch_rss_feed(RSS_FEED_URLS[feed_key], num_articles=articles_per_feed)
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
                    for article in articles  # No need to slice since fetch_rss_feed already limits
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
        # Get the summary data
        last_updated, error_message, summary_table = update_summary(
            indicators, start_date, end_date, slider_range
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

def create_rotation_volume_stats(sectors, rel_strength, rel_momentum, volume_ratios, quadrant_colors):
    stats = []
    
    # Sort sectors by overall strength (combination of momentum and strength)
    overall_scores = rel_strength + rel_momentum
    sorted_indices = np.argsort(overall_scores)[::-1]  # Descending order
    
    for idx in sorted_indices:
        sector = sectors[idx]
        strength = rel_strength[idx]
        momentum = rel_momentum[idx]
        volume = volume_ratios[idx]
        
        # Determine quadrant and color
        if momentum > 100 and strength > 100:
            quadrant = "Leading"
            color = quadrant_colors["leading"]
        elif momentum > 100 and strength <= 100:
            quadrant = "Improving"
            color = quadrant_colors["improving"]
        elif momentum <= 100 and strength <= 100:
            quadrant = "Lagging"
            color = quadrant_colors["lagging"]
        else:
            quadrant = "Weakening"
            color = quadrant_colors["weakening"]
        
        # Create volume indicator
        volume_indicator = "↑" if volume > 1 else "↓"
        volume_color = "#2ecc71" if volume > 1 else "#e74c3c"
        
        stats.append(
            html.Div([
                html.Strong(f"{sector}: ", style={"color": color}),
                html.Span([
                    f"{quadrant} ",
                    html.Span(f"({volume_indicator} {abs(volume-1):+.1%})", 
                             style={"color": volume_color}),
                ]),
            ], className="mb-1")
        )
    
    return stats

def create_performance_stats(sectors, returns, volatility, sharpe_ratios):
    stats = []
    
    # Sort sectors by Sharpe ratio
    sorted_indices = np.argsort(sharpe_ratios)[::-1]  # Descending order
    
    for idx in sorted_indices:
        sector = sectors[idx]
        ret = returns[idx]
        vol = volatility[idx]
        sharpe = sharpe_ratios[idx]
        
        # Color based on Sharpe ratio
        if sharpe > 1:
            color = "#2ecc71"  # Green
        elif sharpe > 0:
            color = "#f1c40f"  # Yellow
        else:
            color = "#e74c3c"  # Red
        
        stats.append(
            html.Div([
                html.Strong(f"{sector}: ", style={"color": color}),
                html.Span(f"Return: {ret:+.1%}, Vol: {vol:.1%}, Sharpe: {sharpe:.2f}"),
            ], className="mb-1")
        )
    
    return stats

def create_valuation_stats(sectors, pe_ratios, growth_rates, peg_ratios, market_caps):
    stats = []
    
    # Sort sectors by PEG ratio (lower is better)
    sorted_indices = np.argsort(peg_ratios)  # Ascending order
    
    for idx in sorted_indices:
        sector = sectors[idx]
        pe = pe_ratios[idx]
        growth = growth_rates[idx]
        peg = peg_ratios[idx]
        mcap = market_caps[idx]
        
        # Color based on PEG ratio
        if peg < 1:
            color = "#2ecc71"  # Green - undervalued
        elif peg < 2:
            color = "#f1c40f"  # Yellow - fair valued
        else:
            color = "#e74c3c"  # Red - overvalued
        
        stats.append(
            html.Div([
                html.Strong(f"{sector}: ", style={"color": color}),
                html.Span([
                    f"P/E: {pe:.1f}, Growth: {growth:+.1%}, ",
                    html.Strong(f"PEG: {peg:.2f}"),
                    f" (${mcap/1000:.1f}B)",
                ]),
            ], className="mb-1")
        )
    
    return stats

def create_rotation_quadrant(sectors, show_labels, quadrant_colors, selected_period, rel_strength, rel_momentum):
    # Create the scatter plot
    fig = go.Figure()

    # Add quadrant lines
    fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=100, line_dash="dash", line_color="gray", opacity=0.5)

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

    # Add scatter plot
    fig.add_trace(
        go.Scatter(
            x=rel_strength,
            y=rel_momentum,
            mode="markers+text",
            marker=dict(
                size=15,
                color=colors,
            ),
            text=sectors,
            textposition=["top center" if y > 100 else "bottom center" for y in rel_momentum],
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "Relative Strength: %{x:.1f}<br>" +
                "Relative Momentum: %{y:.1f}<br>" +
                "<extra></extra>"
            ),
        )
    )

    # Add quadrant labels if enabled
    if show_labels:
        # Calculate positions based on data range
        x_range = max(rel_strength) - min(rel_strength)
        y_range = max(rel_momentum) - min(rel_momentum)
        label_offset_x = x_range * 0.05
        label_offset_y = y_range * 0.05
        
        for pos, label, color in [
            ({"x": 100 + label_offset_x, "y": 100 + label_offset_y}, "LEADING", quadrant_colors["leading"]),
            ({"x": 100 - label_offset_x, "y": 100 + label_offset_y}, "IMPROVING", quadrant_colors["improving"]),
            ({"x": 100 - label_offset_x, "y": 100 - label_offset_y}, "LAGGING", quadrant_colors["lagging"]),
            ({"x": 100 + label_offset_x, "y": 100 - label_offset_y}, "WEAKENING", quadrant_colors["weakening"]),
        ]:
            fig.add_annotation(
                x=pos["x"],
                y=pos["y"],
                text=f"<b>{label}</b>",
                showarrow=False,
                font=dict(size=14, color=color),
            )

    fig.update_layout(
        title=f"Sector Rotation ({selected_period})",
        xaxis=dict(
            title="Relative Strength",
            showgrid=True,
            gridcolor="lightgray",
            zeroline=False,
            autorange=True,
        ),
        yaxis=dict(
            title="Relative Momentum",
            showgrid=True,
            gridcolor="lightgray",
            zeroline=False,
            autorange=True,
        ),
        plot_bgcolor="white",
        showlegend=False,
    )

    return fig

def create_volume_analysis(sectors, selected_period, volume_ratios):
    # Sort sectors by volume ratio
    sorted_indices = np.argsort(volume_ratios)
    sorted_sectors = [sectors[i] for i in sorted_indices]
    sorted_ratios = volume_ratios[sorted_indices]
    
    # Color based on whether volume is above or below average
    colors = ['#2ecc71' if ratio > 1 else '#e74c3c' for ratio in sorted_ratios]

    fig = go.Figure()
    
    # Add horizontal bars
    fig.add_trace(
        go.Bar(
            x=sorted_ratios,
            y=sorted_sectors,
            orientation='h',
            marker_color=colors,
            hovertemplate=(
                "<b>%{y}</b><br>" +
                "Volume Ratio: %{x:.2f}x<br>" +
                "<extra></extra>"
            ),
        )
    )

    # Add reference line at 1.0 (average)
    fig.add_vline(x=1, line_dash="dash", line_color="gray")

    fig.update_layout(
        title=f"Volume Analysis ({selected_period})",
        xaxis=dict(
            title="Volume Ratio (Current/50d Avg)",
            showgrid=True,
            gridcolor="lightgray",
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
        ),
        plot_bgcolor="white",
        showlegend=False,
    )

    return fig

def create_performance_scatter(sectors, selected_period, returns, volatility, market_caps, sharpe_ratios):
    # Create color scale based on Sharpe ratio
    colors = [
        f'rgb({int(255 * (1 - ratio))}, {int(255 * ratio)}, 0)'
        for ratio in np.clip((sharpe_ratios - min(sharpe_ratios)) / (max(sharpe_ratios) - min(sharpe_ratios)), 0, 1)
    ]

    fig = go.Figure()

    # Add scatter plot
    fig.add_trace(
        go.Scatter(
            x=volatility,
            y=returns,
            mode="markers+text",
            marker=dict(
                size=np.sqrt(market_caps/100),  # Scale market caps for reasonable bubble sizes
                color=colors,
                showscale=True,
                colorbar=dict(
                    title="Sharpe Ratio",
                ),
            ),
            text=sectors,
            textposition="top center",
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "Return: %{y:.1%}<br>" +
                "Volatility: %{x:.1%}<br>" +
                "<extra></extra>"
            ),
        )
    )

    # Add reference lines at market averages
    fig.add_hline(y=np.mean(returns), line_dash="dash", line_color="gray")
    fig.add_vline(x=np.mean(volatility), line_dash="dash", line_color="gray")

    fig.update_layout(
        title=f"Risk-Return Analysis ({selected_period})",
        xaxis=dict(
            title="Volatility (Annualized)",
            showgrid=True,
            gridcolor="lightgray",
            zeroline=False,
            tickformat=".0%",
        ),
        yaxis=dict(
            title="Return",
            showgrid=True,
            gridcolor="lightgray",
            zeroline=False,
            tickformat=".0%",
        ),
        plot_bgcolor="white",
    )

    return fig

def create_valuation_bubble(sectors, selected_period, pe_ratios, growth_rates, market_caps, peg_ratios):
    # Create color scale based on PEG ratio (lower is better)
    colors = [
        f'rgb({int(255 * ratio)}, {int(255 * (1 - ratio))}, 0)'
        for ratio in np.clip((peg_ratios - min(peg_ratios)) / (max(peg_ratios) - min(peg_ratios)), 0, 1)
    ]

    fig = go.Figure()

    # Add bubble plot
    fig.add_trace(
        go.Scatter(
            x=pe_ratios,
            y=growth_rates,
            mode="markers+text",
            marker=dict(
                size=np.sqrt(market_caps/100),  # Scale market caps for reasonable bubble sizes
                color=colors,
                showscale=True,
                colorbar=dict(
                    title="PEG Ratio",
                ),
            ),
            text=sectors,
            textposition="top center",
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "P/E Ratio: %{x:.1f}<br>" +
                "Growth Rate: %{y:.1%}<br>" +
                "<extra></extra>"
            ),
        )
    )

    # Add reference lines at market averages
    fig.add_hline(y=np.mean(growth_rates), line_dash="dash", line_color="gray")
    fig.add_vline(x=np.mean(pe_ratios), line_dash="dash", line_color="gray")

    fig.update_layout(
        title=f"Valuation Analysis ({selected_period})",
        xaxis=dict(
            title="P/E Ratio",
            showgrid=True,
            gridcolor="lightgray",
            zeroline=False,
        ),
        yaxis=dict(
            title="Growth Rate",
            showgrid=True,
            gridcolor="lightgray",
            zeroline=False,
            tickformat=".0%",
        ),
        plot_bgcolor="white",
    )

    return fig

def create_unified_stats_table(
    sectors,
    returns, volatility, sharpe_ratios,
    market_caps,
    quadrant_colors
):
    # Create table header with centered text
    header = html.Thead(html.Tr([
        html.Th("Sector", style={"width": "20%", "text-align": "center"}),
        html.Th("Return", style={"width": "20%", "text-align": "center"}),
        html.Th("Volatility", style={"width": "20%", "text-align": "center"}),
        html.Th("Sharpe Ratio", style={"width": "20%", "text-align": "center"}),
    ]))

    rows = []
    for i, sector in enumerate(sectors):
        # Performance data
        ret = returns[i]
        vol = volatility[i]
        sharpe = sharpe_ratios[i]
        
        row = html.Tr([
            # Sector name (centered)
            html.Td(html.Strong(sector), style={"text-align": "center"}),
            
            # Return (centered)
            html.Td(f"{ret:.1%}", style={"text-align": "center"}),
            
            # Volatility (centered)
            html.Td(f"{vol:.1%}", style={"text-align": "center"}),
            
            # Sharpe ratio (centered)
            html.Td(f"{sharpe:.2f}", style={"text-align": "center"}),
        ])
        rows.append(row)
    
    # Create table body
    body = html.Tbody(rows)
    
    # Create table with Bootstrap styling
    table = dbc.Table(
        [header, body],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        style={"fontSize": "0.85rem"},
    )
    
    return table