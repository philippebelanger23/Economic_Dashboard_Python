# components/rss_news.py
import dash_bootstrap_components as dbc
from dash import dcc, html
from data.data_fetcher import fetch_rss_feed
from config.settings import RSS_FEED_URLS

# Configurable margins
MARGIN_BETWEEN_CARDS = "10px"

def create_news_card(feed_key):
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H6(feed_key, className="mb-0", style={"fontSize": "0.9rem"}),
                style={"padding": "5px"},
                className="bg-light",
            ),
            dbc.CardBody(
                html.Ul(
                    id={"type": "news-list", "feed": feed_key},
                    style={
                        "padding": "0",
                        "margin": "0",
                        "list-style-type": "none",
                        "fontSize": "0.8rem"
                    },
                ),
                style={
                    "padding": "8px",
                    "height": "auto"  # Let content determine the height
                },
            ),
        ],
        style={
            "height": "auto",
            "display": "flex",
            "flexDirection": "column"
        },
        className="shadow-sm",  # Removed h-100 to allow natural height
    )

# Create a grid of news cards (3 columns, 2 rows)
news_cards = []
row = []
for i, feed_key in enumerate(RSS_FEED_URLS.keys(), 1):
    row.append(dbc.Col(create_news_card(feed_key), width=4))
    if i % 3 == 0:
        news_cards.append(dbc.Row(row, style={"margin-bottom": MARGIN_BETWEEN_CARDS}))
        row = []

# Add any remaining cards
if row:
    news_cards.append(dbc.Row(row, style={"margin-bottom": MARGIN_BETWEEN_CARDS}))

# Define the RSS container with all feeds
rss_news = html.Div(
    [
        html.H5("Global Economic News Feeds", className="text-center mb-3"),
        html.Div(news_cards)
    ],
    style={"padding": "10px"}
)
