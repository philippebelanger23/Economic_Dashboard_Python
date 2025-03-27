# components/graphs.py
import dash_bootstrap_components as dbc
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output, State
from components.rss_news import rss_news
from data.mappings import INDICATOR_GROUPS
from data.sector_data import fetch_sector_data, calculate_sector_metrics, get_sector_analysis_data, get_market_breadth_data
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.signal import find_peaks

def create_sector_analysis_layout():
    return dbc.Row([
        # Main content column (100% width)
        dbc.Col([
            # Top row with two graphs
            dbc.Row([
                # Relative Performance vs Momentum (Top Left)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Relative Perf vs. Momentum"),
                        dbc.CardBody(
                            dcc.Graph(
                                id="relative-perf-momentum",
                                style={"height": "35vh"},
                                config={
                                    "displayModeBar": False,
                                    "displaylogo": False,
                                },
                            )
                        )
                    ])
                ], width=6),
                
                # Relative Strength vs Price Momentum (Top Right)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Relative Strength vs. Price Momentum"),
                        dbc.CardBody(
                            dcc.Graph(
                                id="strength-price-momentum",
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
                # Sector Rotation Heatmap (Bottom Left)
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
                
                # Market Breadth (Bottom Right)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Market Breadth"),
                        dbc.CardBody(
                            dcc.Graph(
                                id="sectors-above-200ma",
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
                    label="Regressions",
                    value="tab-regressions",
                    children=[
                        dbc.Row(
                            html.Div("Regressions content will go here", style={"margin-top": "20px"}),
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
            Output("relative-perf-momentum", "figure"),
            Output("strength-price-momentum", "figure"),
            Output("sector-heatmap", "figure"),
            Output("sectors-above-200ma", "figure"),
            Output("sector-stats-table", "children"),
        ],
        [
            Input("funds-flow-selected-period", "data"),
        ]
    )
    def update_sector_graphs(selected_period):
        # Fetch real sector data
        end_date = pd.Timestamp.now()
        start_date = end_date - pd.Timedelta(days=365)
        sector_data, benchmark_data = fetch_sector_data(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Get market breadth data specifically for the chart
        dates, spy_rsp_ratio = get_market_breadth_data(period=selected_period)
        
        # If market breadth data fetching failed, try alternate method
        if dates is None or spy_rsp_ratio is None:
            # Calculate SPY/RSP ratio for market breadth from the benchmark data
            if 'SPY' in benchmark_data.columns and 'RSP' in benchmark_data.columns:
                # Convert period to days
                period_days = {
                    '4W': 28, '8W': 56, '12W': 84,
                    '26W': 182, '39W': 273, '52W': 364
                }
                days = period_days.get(selected_period, 364)
                
                # Calculate ratio of SPY to RSP (higher ratio = narrower market)
                spy_rsp_ratio = benchmark_data['SPY'] / benchmark_data['RSP']
                
                # Take only the required period of data from the end
                if len(spy_rsp_ratio) > days:
                    spy_rsp_ratio = spy_rsp_ratio[-days:]
                
                # Normalize to start at 1.0
                spy_rsp_ratio = spy_rsp_ratio / spy_rsp_ratio.iloc[0]
                dates = spy_rsp_ratio.index
            else:
                # Fallback to random data if real data not available
                dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
                spy_rsp_ratio = None
        
        # Sample sectors (use real sector data if available)
        if not sector_data.empty:
            sectors = list(sector_data.columns)
        else:
            sectors = [
                "Technology", "Healthcare", "Financials", "Discretionary",
                "Comm. Services", "Industrials", "Staples",
                "Energy", "Materials", "Real Estate", "Utilities"
            ]
        
        # Rest of the function - still using random data for other graphs
        # Generate sample data
        np.random.seed(None)
        
        # Data for Relative Perf vs Momentum
        rel_perf = np.random.normal(0, 1, len(sectors))
        momentum = np.random.normal(0, 1, len(sectors))
        macd = np.random.normal(0, 0.5, len(sectors))
        roc = np.random.normal(0, 5, len(sectors))
        
        # Data for Strength vs Price Momentum
        rel_strength = np.random.normal(0, 1, len(sectors))
        price_momentum = np.random.normal(0, 1, len(sectors))
        ma = np.random.normal(0, 0.5, len(sectors))
        
        # Data for heatmap
        timeframes = ["1W", "1M", "3M", "6M", "12M"]
        heatmap_data = np.random.normal(0, 1, (len(sectors), len(timeframes)))
        
        # Data for sectors above 200MA - not used anymore, but kept for compatibility
        pct_above_200ma = np.random.uniform(30, 70, len(dates))
        
        # Create figures
        perf_momentum_fig = create_relative_perf_momentum(sectors, rel_perf, momentum, macd, roc)
        strength_momentum_fig = create_strength_price_momentum(sectors, rel_strength, price_momentum, ma)
        heatmap_fig = create_sector_heatmap(sectors, timeframes, heatmap_data)
        above_200ma_fig = create_sectors_above_200ma(dates, pct_above_200ma, spy_rsp_ratio)
        
        # Generate additional data needed for stats table
        growth_rates = np.random.normal(0.15, 0.08, len(sectors))
        pe_ratios = np.random.normal(25, 10, len(sectors))
        peg_ratios = pe_ratios / (growth_rates * 100)
        
        # Create stats table
        stats_table = create_unified_stats_table(
            sectors=sectors,
            returns=rel_perf,
            volatility=momentum,
            sharpe_ratios=macd,
            market_caps=np.random.uniform(500, 15000, len(sectors)),
            quadrant_colors={
                "leading": "#2ecc71",
                "improving": "#3498db",
                "lagging": "#e74c3c",
                "weakening": "#f1c40f"
            },
            growth_rates=growth_rates,
            pe_ratios=pe_ratios,
            peg_ratios=peg_ratios
        )
        
        return perf_momentum_fig, strength_momentum_fig, heatmap_fig, above_200ma_fig, stats_table

def create_relative_perf_momentum(sectors, rel_perf, momentum, macd, roc):
    fig = go.Figure()
    
    # Add scatter plot with bubbles
    fig.add_trace(go.Scatter(
        x=macd,          # MACD Momentum on Relative Strength
        y=rel_perf,      # Relative Performance vs. SPY
        mode="markers+text",
        text=sectors,
        textposition="top center",
        marker=dict(
            size=np.abs(roc) * 5,  # Reduced multiplier from 10 to 5
            sizemode='area',
            sizeref=0.1,  # Fixed size reference for more consistent sizing
            sizemin=8,    # Minimum bubble size
            color=rel_perf,
            colorscale="RdYlGn",
            showscale=False,  # Hide the color bar
            line=dict(color='white', width=1)  # Add white border for better visibility
        ),
        hovertemplate=(
            "<b>%{text}</b><br>" +
            "MACD Momentum: %{x:.2f}<br>" +
            "Rel Perf vs SPY: %{y:.1%}<br>" +
            "ROC: %{customdata:.1f}%<br>" +
            "<extra></extra>"
        ),
        customdata=roc,
    ))
    
    # Add quadrant lines
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Add quadrant labels
    fig.add_annotation(x=max(macd)*0.5, y=max(rel_perf)*0.5, text="<b>LEADING</b>", showarrow=False, font=dict(size=10, color="green"))
    fig.add_annotation(x=min(macd)*0.5, y=max(rel_perf)*0.5, text="<b>IMPROVING</b>", showarrow=False, font=dict(size=10, color="blue"))
    fig.add_annotation(x=min(macd)*0.5, y=min(rel_perf)*0.5, text="<b>LAGGING</b>", showarrow=False, font=dict(size=10, color="red"))
    fig.add_annotation(x=max(macd)*0.5, y=min(rel_perf)*0.5, text="<b>WEAKENING</b>", showarrow=False, font=dict(size=10, color="orange"))
    
    fig.update_layout(
        title=dict(
            text="Tracks which sectors are leading/lagging and where money is flowing",
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        xaxis=dict(
            title="MACD Momentum on Relative Strength",
            title_font=dict(size=12),
            showgrid=True,
            gridcolor='lightgray',
            zeroline=True,
            zerolinecolor='gray',
            zerolinewidth=1
        ),
        yaxis=dict(
            title="Relative Performance vs. SPY",
            title_font=dict(size=12),
            showgrid=True,
            gridcolor='lightgray',
            zeroline=True,
            zerolinecolor='gray',
            zerolinewidth=1,
            tickformat=".1%"
        ),
        plot_bgcolor="white",
        showlegend=False,
        margin=dict(t=50, l=50, r=50, b=50),
    )
    
    return fig

def create_strength_price_momentum(sectors, rel_strength, price_momentum, ma):
    fig = go.Figure()
    
    # Calculate 3-month relative strength change (for bubble size)
    rel_strength_change = np.random.normal(0, 0.15, len(sectors))  # Simulated 3-month change
    
    # Add scatter plot with bubbles
    fig.add_trace(go.Scatter(
        x=ma,              # 50MA vs 200MA momentum
        y=rel_strength,    # Relative Strength Ratio
        mode="markers+text",
        text=sectors,
        textposition="top center",
        marker=dict(
            size=np.abs(rel_strength_change) * 5,  # Match first graph's multiplier
            sizemode='area',
            sizeref=0.1,  # Fixed size reference for more consistent sizing
            sizemin=8,    # Minimum bubble size
            color=rel_strength,
            colorscale="RdYlGn",
            showscale=False,  # Hide the color bar
            line=dict(color='white', width=1)  # Add white border for better visibility
        ),
        hovertemplate=(
            "<b>%{text}</b><br>" +
            "MA Momentum: %{x:.2f}<br>" +
            "Relative Strength: %{y:.2f}<br>" +
            "3M RS Change: %{customdata:.1%}<br>" +
            "<extra></extra>"
        ),
        customdata=rel_strength_change,
    ))
    
    # Add quadrant lines
    fig.add_hline(y=1, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Add quadrant labels
    fig.add_annotation(x=max(ma)*0.5, y=max(rel_strength)*0.5, text="<b>LEADING</b>", showarrow=False, font=dict(size=10, color="green"))
    fig.add_annotation(x=min(ma)*0.5, y=max(rel_strength)*0.5, text="<b>IMPROVING</b>", showarrow=False, font=dict(size=10, color="blue"))
    fig.add_annotation(x=min(ma)*0.5, y=min(rel_strength)*0.5, text="<b>LAGGING</b>", showarrow=False, font=dict(size=10, color="red"))
    fig.add_annotation(x=max(ma)*0.5, y=min(rel_strength)*0.5, text="<b>WEAKENING</b>", showarrow=False, font=dict(size=10, color="orange"))
    
    fig.update_layout(
        title=dict(
            text="Detects trend continuation vs. trend reversals",
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        xaxis=dict(
            title="50-day MA vs 200-day MA Momentum",
            title_font=dict(size=12),
            showgrid=True,
            gridcolor='lightgray',
            zeroline=True,
            zerolinecolor='gray',
            zerolinewidth=1
        ),
        yaxis=dict(
            title="Relative Strength Ratio (Sector/SPY)",
            title_font=dict(size=12),
            showgrid=True,
            gridcolor='lightgray',
            zeroline=True,
            zerolinecolor='gray',
            zerolinewidth=1,
        ),
        plot_bgcolor="white",
        showlegend=False,
        margin=dict(t=50, l=50, r=50, b=50),
    )
    
    return fig

def create_sector_heatmap(sectors, timeframes, data):
    # Data represents relative performance vs SPY
    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=timeframes,
        y=sectors,
        colorscale="RdYlGn",     # Red for underperformance, green for outperformance vs SPY
        showscale=False,         # Hide the color scale
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "Timeframe: %{x}<br>" +
            "Rel. Perf: %{z:.1%}<br>" +
            "<extra></extra>"
        ),
    ))
    
    fig.update_layout(
        title=dict(
            text="Shows rotation trends over different timeframes",
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        xaxis=dict(
            title="Timeframe",
            title_font=dict(size=12),
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            title="Sectors",
            title_font=dict(size=12),
            tickfont=dict(size=10),
        ),
        plot_bgcolor="white",
        margin=dict(t=50, l=50, r=50, b=50),
    )
    
    return fig

def create_sectors_above_200ma(dates, pct_above_200ma, spy_rsp_ratio=None):
    # Use real SPY/RSP ratio data if provided, otherwise fallback to simulation
    if spy_rsp_ratio is None:
        # For SPY/RSP ratio simulation
        # When ratio increases, it means large caps are leading (narrow market)
        # When ratio decreases, it means equal weight is leading (broad market)
        np.random.seed(None)
        spy_rsp_ratio = 1 + np.cumsum(np.random.normal(0, 0.001, len(dates)))  # Simulate ratio around 1.0
    
    # Apply smoothing to the data to reduce spikiness (using rolling mean)
    if len(spy_rsp_ratio) > 5:  # Only smooth if enough data points
        smoothed_ratio = pd.Series(spy_rsp_ratio).rolling(window=5, center=True, min_periods=1).mean().values
    else:
        smoothed_ratio = spy_rsp_ratio
    
    # Calculate the maximum deviation from 1.0 to set symmetric axis range
    max_deviation = max(
        abs(max(smoothed_ratio) - 1.0),
        abs(min(smoothed_ratio) - 1.0)
    )
    y_min = 1.0 - max_deviation
    y_max = 1.0 + max_deviation
    
    fig = go.Figure()
    
    # Add baseline at 1.0 first (no fill)
    fig.add_trace(go.Scatter(
        x=dates,
        y=[1.0] * len(dates),
        mode='lines',
        line=dict(color='rgba(0,0,0,0)'),  # Invisible line
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Add the main line plot for values above 1.0 (no fill)
    fig.add_trace(go.Scatter(
        x=dates,
        y=np.maximum(smoothed_ratio, 1.0),
        mode='lines',
        line=dict(
            color='black',
            width=1.5,
            shape='spline',  # Add spline curve for smoothness
            smoothing=1.3     # Increase smoothing factor
        ),
        fill='tonexty',
        fillcolor='rgba(0, 0, 0, 0)',  # Transparent fill for values above 1.0
        showlegend=False
    ))
    
    # Add the line plot for values below 1.0 (red fill)
    fig.add_trace(go.Scatter(
        x=dates,
        y=np.minimum(smoothed_ratio, 1.0),
        mode='lines',
        line=dict(
            color='black',
            width=1.5,
            shape='spline',  # Add spline curve for smoothness
            smoothing=1.3     # Increase smoothing factor
        ),
        fill='tonexty',
        fillcolor='rgba(255, 0, 0, 0.4)',  # Red fill for values below 1.0
        showlegend=False
    ))
    
    # Add the line plot for values above 1.0 (green fill)
    fig.add_trace(go.Scatter(
        x=dates,
        y=smoothed_ratio,
        mode='lines',
        line=dict(
            color='black',
            width=1.5,
            shape='spline',  # Add spline curve for smoothness
            smoothing=1.3     # Increase smoothing factor
        ),
        fill='tonexty',
        fillcolor='rgba(123, 228, 161, 0.8)',  # RGB from color picker (123, 228, 161)
        showlegend=False,
        hovertemplate=(
            "Date: %{x|%Y-%m-%d}<br>" +
            "SPY/RSP: %{y:.3f}<br>" +
            "<extra></extra>"
        )
    ))
    
    fig.update_layout(
        title=dict(
            text="Market Breadth",
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        xaxis=dict(
            title="Time",
            title_font=dict(size=12),
            showgrid=True,
            gridcolor='lightgray',
            zeroline=False
        ),
        yaxis=dict(
            title="Breadth (SPY/RSP)",
            title_font=dict(size=12),
            showgrid=True,
            gridcolor='lightgray',
            zeroline=False,
            tickformat=".3f",
            range=[y_min, y_max],  # Set symmetric range around 1.0
            dtick=0.01  # Set tick interval to 0.01
        ),
        plot_bgcolor="white",
        showlegend=False,
        margin=dict(t=50, l=50, r=50, b=50),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12
        ),
    )
    
    return fig

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

def create_unified_stats_table(
    sectors,
    returns,
    volatility,
    sharpe_ratios,
    market_caps,
    quadrant_colors,
    growth_rates,
    pe_ratios,
    peg_ratios
):
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