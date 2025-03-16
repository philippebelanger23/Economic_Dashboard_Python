# components/graphs.py
import dash_bootstrap_components as dbc
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output, State
from components.rss_news import rss_news
from data.mappings import INDICATOR_GROUPS
import numpy as np
import pandas as pd
import plotly.graph_objects as go

def create_sector_analysis_layout():
    return dbc.Row([
        # Main content column (100% width)
        dbc.Col([
            # Top row with two graphs
            dbc.Row([
                # Sector Rotation Quadrant (Top Left)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Sector Rotation Quadrant"),
                        dbc.CardBody(
                            dcc.Graph(
                                id="sector-rotation-quadrant",
                                style={"height": "35vh"},
                                config={
                                    "displayModeBar": False,
                                    "displaylogo": False,
                                },
                            )
                        )
                    ])
                ], width=6),
                
                # Relative Performance (Top Right)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Relative Performance"),
                        dbc.CardBody(
                            dcc.Graph(
                                id="relative-performance",
                                style={"height": "35vh"},
                                config={
                                    "displayModeBar": False,
                                    "displaylogo": False,
                                },
                            )
                        )
                    ])
                ], width=6),
            ], className="mb-4"),

            # Bottom row with two graphs
            dbc.Row([
                # Sector Heatmap (Bottom Left)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Sector Rotation Heatmap"),
                        dbc.CardBody(
                            dcc.Graph(
                                id="sector-heatmap",
                                style={"height": "35vh"},
                                config={
                                    "displayModeBar": False,
                                    "displaylogo": False,
                                },
                            )
                        )
                    ])
                ], width=6),
                
                # Relative Valuation (Bottom Right)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Relative Valuation"),
                        dbc.CardBody(
                            dcc.Graph(
                                id="relative-valuation",
                                style={"height": "35vh"},
                                config={
                                    "displayModeBar": False,
                                    "displaylogo": False,
                                },
                            )
                        )
                    ])
                ], width=6),
            ], className="mb-3"),
        ], width=12),
    ])

# Create the content layout
content = dbc.Container(
    [
        dcc.Tabs(
            id="dashboard-tabs",
            value="tab-economics",
            children=[
                dcc.Tab(
                    label="Economics",
                    value="tab-economics",
                    children=[
                        dbc.Row(
                            id="graph-container",
                            style={"margin-top": "20px"},
                        )
                    ],
                ),
                dcc.Tab(
                    label="Sector Analysis",
                    value="tab-funds-flow",
                    children=[
                        dbc.Row(
                            create_sector_analysis_layout(),
                            style={"margin-top": "20px"},
                        )
                    ],
                ),
                dcc.Tab(
                    label="News",
                    value="tab-news",
                    children=[
                        dbc.Row(
                            rss_news,
                            style={"margin-top": "20px"},
                        )
                    ],
                ),
            ],
        ),
    ],
    fluid=True,
)

def register_sector_callbacks(app):
    """Register only sector-specific callbacks"""
    @app.callback(
        [
            Output("sector-rotation-quadrant", "figure"),
            Output("sector-heatmap", "figure"),
            Output("relative-valuation", "figure"),
            Output("relative-performance", "figure"),
            Output("sector-stats-table", "children"),
        ],
        [
            Input("funds-flow-selected-period", "data"),
        ]
    )
    def update_sector_graphs(selected_period):
        # Default values for removed visualization settings
        show_labels = True
        show_trends = True
        bubble_size = "equal"
        
        # Sample sectors
        sectors = [
            "Technology", "Healthcare", "Financials", "Discretionary",
            "Comm. Services", "Industrials", "Staples",
            "Energy", "Materials", "Real Estate", "Utilities"
        ]
        
        # Use a random seed each time the callback is triggered
        # This will generate new random data whenever the date changes
        np.random.seed(None)  # Reset the seed to None to get truly random data
        
        # Generate data for all graphs
        momentum = np.random.normal(0, 1, len(sectors))
        strength = np.random.normal(0, 1, len(sectors))
        returns = np.random.normal(0.10, 0.15, len(sectors))  # For Sharpe ratio
        volatility = np.random.normal(0.20, 0.10, len(sectors))
        spy_return = 0.08  # Sample SPY return
        pe_ratios = np.random.normal(25, 10, len(sectors))
        growth_rates = np.random.normal(0.15, 0.08, len(sectors))
        market_caps = np.random.uniform(500, 15000, len(sectors))  # For bubble sizes
        
        # Calculate metrics for sidebar
        rf_rate = 0.02  # Risk-free rate
        sharpe_ratios = (returns - rf_rate) / volatility
        rel_performance = returns - spy_return
        peg_ratios = pe_ratios / (growth_rates * 100)
        
        # Create figures
        rotation_fig = create_rotation_quadrant(sectors, show_labels, {
            "leading": "#2ecc71",     # Green
            "improving": "#3498db",    # Blue
            "lagging": "#e74c3c",     # Red
            "weakening": "#f1c40f"    # Yellow
        }, selected_period, strength, momentum)
        
        heatmap_fig = create_sector_heatmap(sectors)
        valuation_fig = create_relative_valuation(sectors, pe_ratios, growth_rates)
        performance_fig = create_performance_scatter(sectors, selected_period, returns, volatility, market_caps, sharpe_ratios)
        
        # Create sidebar statistics table
        stats_table = create_unified_stats_table(
            sectors,
            returns, volatility, sharpe_ratios,
            market_caps,
            {
                "leading": "#2ecc71",     # Green
                "improving": "#3498db",    # Blue
                "lagging": "#e74c3c",     # Red
                "weakening": "#f1c40f"    # Yellow
            },
            growth_rates, pe_ratios, peg_ratios  # Pass these values to avoid regenerating them
        )
        
        return rotation_fig, heatmap_fig, valuation_fig, performance_fig, stats_table

def create_sidebar_stats(sectors, momentum, strength, sharpe_ratios, rel_performance, peg_ratios):
    # Determine quadrant for each sector
    quadrants = []
    quadrant_colors = {
        "Leading": "#2ecc71",     # Green
        "Improving": "#3498db",   # Blue
        "Lagging": "#e74c3c",     # Red
        "Weakening": "#f1c40f"    # Yellow
    }
    
    for m, s in zip(momentum, strength):
        if m > 0 and s > 0:
            quadrants.append(("Leading", quadrant_colors["Leading"]))
        elif m > 0 and s <= 0:
            quadrants.append(("Improving", quadrant_colors["Improving"]))
        elif m <= 0 and s <= 0:
            quadrants.append(("Lagging", quadrant_colors["Lagging"]))
        else:
            quadrants.append(("Weakening", quadrant_colors["Weakening"]))
    
    # Create table header
    header = html.Thead(html.Tr([
        html.Th("Sector", style={"width": "20%"}),
        html.Th("Position", style={"width": "20%"}),
        html.Th("Sharpe", style={"width": "20%"}),
        html.Th("vs SPY", style={"width": "20%"}),
        html.Th("PEG", style={"width": "20%"}),
    ]))
    
    # Create table rows
    rows = []
    for i, sector in enumerate(sectors):
        quadrant, color = quadrants[i]
        row = html.Tr([
            # Sector name
            html.Td(sector),
            # Position (Quadrant)
            html.Td(quadrant, style={"color": color}),
            # Sharpe Ratio
            html.Td(f"{sharpe_ratios[i]:.2f}"),
            # Relative Performance vs SPY
            html.Td(
                f"{rel_performance[i]:+.1%}",
                style={"color": "#2ecc71" if rel_performance[i] > 0 else "#e74c3c"}
            ),
            # PEG Ratio
            html.Td(
                f"{peg_ratios[i]:.2f}",
                style={"color": "#2ecc71" if peg_ratios[i] < 1 else "#e74c3c"}
            ),
        ])
        rows.append(row)
    
    # Create table body
    body = html.Tbody(rows)
    
    # Create complete table with Bootstrap styling
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

def create_rotation_quadrant(sectors, show_labels, quadrant_colors, selected_period, strength, momentum):
    # Add descriptive annotation above the title
    annotation = dict(
        text="Pictures flow of money across sectors",
        xref="paper", yref="paper",
        x=-0.05, y=1.25,  # Position at top-left
        showarrow=False,
        font=dict(size=12, color="gray"),
        align="left",
    )
    
    fig = go.Figure()
    
    # Add quadrant lines
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    
    # Add scatter plot
    fig.add_trace(go.Scatter(
        x=strength,
        y=momentum,
        mode="markers+text",
        text=sectors,
        textposition="top center",
        marker=dict(
            size=12,
            color=momentum,
            colorscale="RdYlGn",
            showscale=True,
        ),
    ))
    
    # Add SPY marker at the intersection of quadrant lines
    fig.add_trace(go.Scatter(
        x=[0],
        y=[0],
        mode="markers+text",
        text=["SPY"],
        textposition="bottom right",
        marker=dict(
            size=12,
            color="gray",
            symbol="circle",
        ),
        hovertemplate=(
            "<b>SPY</b><br>" +
            "Relative Strength: 0<br>" +
            "Momentum: 0<br>" +
            "<extra></extra>"
        ),
        name="SPY"
    ))
    
    fig.update_layout(
        xaxis_title="Relative Strength",
        yaxis_title="Momentum",
        showlegend=False,
        plot_bgcolor="white",
        margin=dict(t=70),  # Increase top margin for higher annotation
        annotations=[annotation]
    )
    
    return fig

def create_sector_heatmap(sectors):
    # Add descriptive annotation above the title
    annotation = dict(
        text="Shows how sectors perform vs SPY across different timeframes",
        xref="paper", yref="paper",
        x=-0.05, y=1.25,  # Position at top-left
        showarrow=False,
        font=dict(size=12, color="gray"),
        align="left",
    )
    
    # Generate sample data for different timeframes
    timeframes = ["1W", "1M", "3M", "6M", "12M"]
    data = np.random.normal(0, 1, (len(sectors), len(timeframes)))
    
    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=timeframes,
        y=sectors,
        colorscale="RdYlGn",
        colorbar_title="Rel. Perf",
    ))
    
    fig.update_layout(
        xaxis_title="Timeframe",
        yaxis_title="Sectors",
        plot_bgcolor="white",
        margin=dict(t=70),  # Increase top margin for higher annotation
        annotations=[annotation]
    )
    
    return fig

def create_relative_valuation(sectors, pe_ratios, growth_rates):
    # Add descriptive annotation above the title
    annotation = dict(
        text="Compares P/E ratio vs growth rate",
        xref="paper", yref="paper",
        x=-0.05, y=1.25,  # Position at top-left
        showarrow=False,
        font=dict(size=12, color="gray"),
        align="left",
    )
    
    # Generate sample data
    market_caps = np.random.uniform(500, 15000, len(sectors))
    peg_ratios = pe_ratios / (growth_rates * 100)
    
    fig = go.Figure()
    
    # Add bubble plot
    fig.add_trace(go.Scatter(
        x=pe_ratios,
        y=growth_rates,
        mode="markers+text",
        text=sectors,
        textposition="top center",
        marker=dict(
            size=np.sqrt(market_caps/100),
            color=peg_ratios,
            colorscale="RdYlGn_r",  # Reversed so red = high PEG (expensive)
            showscale=True,
            colorbar=dict(title="PEG Ratio"),
        ),
        hovertemplate=(
            "<b>%{text}</b><br>" +
            "P/E Ratio: %{x:.1f}<br>" +
            "Growth Rate: %{y:.1%}<br>" +
            "<extra></extra>"
        ),
    ))
    
    # Calculate average values for reference lines
    avg_pe = np.mean(pe_ratios)
    avg_growth = np.mean(growth_rates)
    
    # Add reference lines at market averages
    fig.add_hline(y=avg_growth, line_dash="dash", line_color="gray")
    fig.add_vline(x=avg_pe, line_dash="dash", line_color="gray")
    
    # Add SPY marker at the intersection of reference lines
    fig.add_trace(go.Scatter(
        x=[avg_pe],
        y=[avg_growth],
        mode="markers+text",
        text=["SPY"],
        textposition="bottom right",
        marker=dict(
            size=12,
            color="gray",
            symbol="circle",
        ),
        hovertemplate=(
            "<b>SPY</b><br>" +
            "P/E Ratio: %{x:.1f}<br>" +
            "Growth Rate: %{y:.1%}<br>" +
            "<extra></extra>"
        ),
        name="SPY"
    ))
    
    fig.update_layout(
        xaxis_title="P/E Ratio",
        yaxis_title="Growth Rate",
        yaxis_tickformat=".0%",
        showlegend=False,
        plot_bgcolor="white",
        margin=dict(t=70),  # Increase top margin for higher annotation
        annotations=[annotation]
    )
    
    return fig

def create_performance_scatter(sectors, selected_period, returns, volatility, market_caps, sharpe_ratios):
    # Add descriptive annotation above the title
    annotation = dict(
        text="Compares Risk-Adjusted Returns",
        xref="paper", yref="paper",
        x=-0.05, y=1.25,  # Position at top-left
        showarrow=False,
        font=dict(size=12, color="gray"),
        align="left",
    )
    
    fig = go.Figure()
    
    # Add scatter plot - swapped X and Y axes
    fig.add_trace(go.Scatter(
        x=volatility,  # Now volatility is on X-axis
        y=returns,     # Now returns is on Y-axis
        mode="markers+text",
        text=sectors,
        textposition="top center",
        marker=dict(
            size=np.sqrt(market_caps/100),
            color=sharpe_ratios,
            colorscale="RdYlGn",
            showscale=True,
        ),
        hovertemplate=(
            "<b>%{text}</b><br>" +
            "Volatility: %{x:.1%}<br>" +  # Updated hover template
            "Return: %{y:.1%}<br>" +
            "Sharpe: %{marker.color:.2f}<br>" +  # Added Sharpe ratio to hover
            "<extra></extra>"
        ),
    ))
    
    fig.update_layout(
        xaxis_title="Volatility",
        yaxis_title="Return",
        xaxis_tickformat=".0%",  # Format X-axis (volatility) as percentage
        yaxis_tickformat=".0%",  # Format Y-axis (returns) as percentage
        showlegend=False,
        plot_bgcolor="white",
        margin=dict(t=70),  # Increase top margin for higher annotation
        annotations=[annotation]
    )
    
    return fig

def create_unified_stats_table(sectors, returns, volatility, sharpe_ratios, market_caps, quadrant_colors, growth_rates, pe_ratios, peg_ratios):
    # Determine quadrant for each sector based on returns and volatility
    quadrants = []
    for ret, vol in zip(returns, volatility):
        if ret > np.mean(returns) and vol < np.mean(volatility):
            quadrants.append(("Leading", quadrant_colors["leading"]))
        elif ret > np.mean(returns) and vol >= np.mean(volatility):
            quadrants.append(("Improving", quadrant_colors["improving"]))
        elif ret <= np.mean(returns) and vol >= np.mean(volatility):
            quadrants.append(("Lagging", quadrant_colors["lagging"]))
        else:
            quadrants.append(("Weakening", quadrant_colors["weakening"]))

    # Calculate vs SPY metrics
    spy_return = 0.08  # Sample SPY return
    rel_performance = returns - spy_return

    # Create table header with centered text
    header = html.Thead(html.Tr([
        html.Th("Sector", style={"width": "20%", "text-align": "center"}),
        html.Th("Rotation", style={"width": "20%", "text-align": "center"}),
        html.Th("Sharpe", style={"width": "20%", "text-align": "center"}),
        html.Th("vs SPY", style={"width": "20%", "text-align": "center"}),
        html.Th("PEG", style={"width": "20%", "text-align": "center"}),
    ]))
    
    # Create table rows with centered data
    rows = []
    for i, sector in enumerate(sectors):
        quadrant, color = quadrants[i]
        row = html.Tr([
            # Sector name (centered)
            html.Td(sector, style={"text-align": "center"}),
            # Rotation (Quadrant) (centered)
            html.Td(quadrant, style={"color": color, "text-align": "center"}),
            # Sharpe Ratio (centered)
            html.Td(f"{sharpe_ratios[i]:.2f}", style={"text-align": "center"}),
            # vs SPY (centered)
            html.Td(
                f"{rel_performance[i]:+.1%}",
                style={
                    "color": "#2ecc71" if rel_performance[i] > 0 else "#e74c3c",
                    "text-align": "center"
                }
            ),
            # PEG Ratio (centered)
            html.Td(
                f"{peg_ratios[i]:.2f}",
                style={
                    "color": "#2ecc71" if peg_ratios[i] < 1 else "#e74c3c",
                    "text-align": "center"
                }
            ),
        ])
        rows.append(row)
    
    # Create table body
    body = html.Tbody(rows)
    
    # Create complete table with Bootstrap styling
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