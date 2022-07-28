import plotly.express as px


# The 'title' key appends that string to whatever the x-axis is (e.g. Player Placements)
PLACEMENT_MAPS = {'Win/Loss': {4: 'Win', 5: 'Loss', 6: 'Loss', 7: 'Loss', 'title': ' Placements'},
                  'Full Detail': {4: 'Gold', 5: 'Silver', 6: 'Bronze', 7: 'Iron', 'title': ' Placements'}}
COLOR_MAP = {'Loss': 'gray',
             'Win': 'gold',
             'Iron': 'gray',
             'Bronze': 'brown',
             'Silver': 'silver',
             'Gold': 'gold',
             'Went Fourth': '#8D52CE',
             'Went Third': '#00CC96',
             'Went Second': '#C84731',
             'Went First': '#4D55C1',
             'WUBRG': 'white',
             'G': '#006633',
             'R': '#7E001E',
             'B': '#420161',
             'U': '#264490',
             'W': '#E49604'}
TURN_ORDER_MAP = {0: 'Went First',
                  1: 'Went Second',
                  2: 'Went Third',
                  3: 'Went Fourth',
                  'title': ' Turn Order Distribution'}
PARTICIPATION_MAP = {'Matches': 'Matches',
                     'title': ' Participation'}


def bar_chart(df, x, var_filter):
    """Creates a bar chart from the DataFrame df.
    df: The long-form dataframe with relevant information
    x: Usually the first column in df (not always), which the data is grouped by (like Player)
    var_filter: A filter for the variables pertinent to this graph (Placements, Turn Orders, Matches Played, etc)"""

    # Copying the original dataframe to avoid any persistent changes (and an annoying warning)
    filtered = df.copy().loc[df['Variable'].isin(var_filter.keys())]

    # The matches played cannot simply be summed (as there are 2-4 players in each game)
    # There is a total matches entry in the dataframe at index 0 due to how things are sorted that is used
    if var_filter == {'Matches': 'Matches', 'title': ' Participation'}:
        # I think the total gets indexed to zero consistently
        y = 100 * filtered['Value'] / filtered['Value'][0]
        y = y.drop(0)
        filtered = filtered.drop(0)

        color = None
        if x == 'Identity':
            color = x

    else:
        filtered['Variable'] = filtered['Variable'].map(var_filter)
        # This is done post-mapping to catch any duplications (This primarily occurs when mapping to Win/Loss/Loss/Loss)
        filtered = filtered.groupby([x, 'Variable'], sort=False, as_index=False)['Value'].sum()
        color = 'Variable'
        y = 100 * filtered['Value'] / filtered.groupby(x)['Value'].transform('sum')

    title = x + var_filter['title']

    fig = px.bar(filtered, x=x, y=y, color=color, title=title, color_discrete_map=COLOR_MAP, text='Value',
                 labels={'y': 'Percentage (%)'}, category_orders={'Variable': list(COLOR_MAP.keys())})

    if x != 'Identity' or var_filter != {'Matches': 'Matches', 'title': ' Participation'}:
        # Placement charts need their legends reversed to match the actual stacking
        fig.update_layout(legend_traceorder='reversed')

    return fig


def turn_count_hist(df):
    return px.histogram(df, x='Turns', title='Turns per Match')


def location_pie(df):
    return px.pie(df, values='Location', names=df.index, title='Location Distribution')


def win_pie(df, names):
    color_map = None
    color = None
    if names == 'Identity':
        color_map = COLOR_MAP
        color = 'Identity'

    filtered = df.copy().loc[df['Variable'] == 4]  # 4 always represents a Win in the Variable column

    fig = px.pie(filtered, values='Value', names=names, title=names + ' Win Distribution',
                 color=color, color_discrete_map=color_map, category_orders={names: list(COLOR_MAP.keys())[::-1]})
    fig.update_traces(textposition='inside', textinfo='percent+label')

    return fig


def placement_chart(df, x, placement_option):
    """This function is used for the dynamic placement charts as they can be either pie or bar charts"""
    if placement_option == 'Wins':
        return win_pie(df, x)

    else:
        return bar_chart(df, x, PLACEMENT_MAPS[placement_option])


def generate_charts(match_data, player_data, turn_order_data, overall_color_data, placement_option='Wins'):
    """This function generates the plots and stores as values in a dict, with the HTML element ids as keys"""
    figs = {'player-placement-chart': placement_chart(player_data, x='Player',
                                                      placement_option=placement_option),
            'player-turn-order-chart': bar_chart(player_data, x='Player', var_filter=TURN_ORDER_MAP),
            'player-participation-chart': bar_chart(player_data, x='Player', var_filter=PARTICIPATION_MAP),
            'turn-order-placement-chart': placement_chart(turn_order_data, x='Turn Order',
                                                          placement_option=placement_option),
            'turn-count-chart': turn_count_hist(match_data),
            'color-participation-chart': bar_chart(overall_color_data, x='Identity', var_filter=PARTICIPATION_MAP),
            'color-placement-chart': placement_chart(overall_color_data, x='Identity',
                                                     placement_option=placement_option),
            'location-chart': location_pie(match_data['Location'].value_counts())}

    return figs
