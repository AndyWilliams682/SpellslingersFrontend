# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc
from plotters import *
from data_processing import pull_spreadsheet_data, get_turn_order_data, get_deck_data, get_color_data
import numpy as np


# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__)

# Remapping the integers to color strings
PHILOSOPHY_MAP = {'': -1, 'C': 0, 'W': 1, 'U': 2, 'B': 3, 'R': 4, 'G': 5, 'WUBRG': 6}

# Pulling data on startup to avoid pulling it during any callbacks and causing delays
MATCH_DF, DECK_DF = pull_spreadsheet_data()
SEASONS = MATCH_DF['Season'].unique()
LATEST_SEASON = SEASONS.max()
SEASONS = np.append(SEASONS, 'All')


# DATA
def final_data_stuff(season='All'):
    match_df = MATCH_DF.copy()

    if season != 'All':
        match_df = match_df[match_df['Season'] == season]

    turn_order_df = get_turn_order_data(match_df)
    deck_data = get_deck_data(match_df, DECK_DF)
    player_color_data = get_color_data(deck_data)

    # Deck data grouped by player
    player_df = deck_data.groupby(['Player', 'Variable'], sort=False, as_index=False)['Value'].sum()
    player_df = player_df.sort_values(['Player', 'Variable'], ascending=[True, False])

    # Color data grouped by color, representative of the entire playerbase
    overall_color_df = player_color_data.groupby(['Identity', 'Variable'],
                                                 sort=False, as_index=False)['Value'].sum()
    overall_color_df = overall_color_df.sort_values(['Identity', 'Variable'], ascending=[True, False])
    overall_color_df['Identity'] = overall_color_df['Identity'].map({v: k for k, v in PHILOSOPHY_MAP.items()})

    return match_df, player_df, turn_order_df, overall_color_df


match_data, player_data, turn_order_data, overall_color_data = final_data_stuff()


# PLOT
figs = generate_charts(match_data, player_data, turn_order_data, overall_color_data)


# APP / LAYOUT
app.layout = html.Div([
    html.H1(children='Spellslingers'),
    dcc.Dropdown(
                SEASONS,
                LATEST_SEASON,
                id='season-dropdown',
            ),
    dcc.RadioItems(
                ['Wins', 'Win/Loss', 'Full Detail'],
                'Wins',
                id='placement-detail-option',
                labelStyle={'display': 'inline-block', 'marginTop': '5px'}
            ),
    html.Div([
        dcc.Graph(
            id='player-placement-chart',
            figure=figs['player-placement-chart']
        ),
        dcc.Graph(
            id='player-turn-order-chart',
            figure=figs['player-turn-order-chart']
        ),
        dcc.Graph(
            id='player-participation-chart',
            figure=figs['player-participation-chart']
        ),
        dcc.Graph(
            id='turn-order-placement-chart',
            figure=figs['turn-order-placement-chart']
        ),
        dcc.Graph(
            id='turn-count-chart',
            figure=figs['turn-count-chart']
        ),
        dcc.Graph(
            id='color-participation-chart',
            figure=figs['color-participation-chart']
        ),
        dcc.Graph(
            id='color-placement-chart',
            figure=figs['color-placement-chart']
        ),
        dcc.Graph(
            id='location-chart',
            figure=figs['location-chart']
        )
    ],
        style={'width': '49%', 'padding': '0px 20px 20px 20px'}
    )
])


@app.callback(
    output={'player-placement-chart': Output('player-placement-chart', 'figure'),
            'player-turn-order-chart': Output('player-turn-order-chart', 'figure'),
            'player-participation-chart': Output('player-participation-chart', 'figure'),
            'turn-order-placement-chart': Output('turn-order-placement-chart', 'figure'),
            'turn-count-chart': Output('turn-count-chart', 'figure'),
            'color-participation-chart': Output('color-participation-chart', 'figure'),
            'color-placement-chart': Output('color-placement-chart', 'figure'),
            'location-chart': Output('location-chart', 'figure')},
    inputs={'season': Input('season-dropdown', 'value'),
            'placement_option': Input('placement-detail-option', 'value')})
def new_update_charts(season, placement_option):
    # The structure of this could be improved, but I am lazy
    new_match_data, new_player_data, new_turn_order_data, new_overall_color_data = final_data_stuff(season)
    return generate_charts(new_match_data, new_player_data, new_turn_order_data, new_overall_color_data,
                           placement_option=placement_option)


if __name__ == '__main__':
    app.run_server(debug=True)
