import pandas as pd
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly',
          'https://www.googleapis.com/auth/drive.metadata.readonly']
SPREADSHEET_ID = '1Wza6TLXqAQ_MHwARc7K43SqCHBgb6ti-yRdY9gbHgoU'
MATCH_DATA_RANGE = 'Game Data!A2:Q'
DECK_DATA_RANGE = 'Decks!B:Q'

MAX_PLAYERS = 4
# Mapping strings to integers for sorting purposes, then using strings again in the plots
COLOR_MAP = {' ': -1, 'C': 0, 'W': 1, 'U': 2, 'B': 3, 'R': 4, 'G': 5, 'M': 6}
TURN_ORDER_MAP = {0: 'Went First',
                  1: 'Went Second',
                  2: 'Went Third',
                  3: 'Went Fourth'}


def pull_spreadsheet_data():
    """This function interacts with external data sources (Google Sheets API or a csv). Light reformatting is done
    to replicate what the database might spit out when it's working.
    Returns match information in match_sheet, and deck information in deck_sheet, both as DataFrames"""
    try:
        google_creds = Credentials.from_authorized_user_file('google_token.json', SCOPES)
        service = build('sheets', 'v4', credentials=google_creds)
        sheet = service.spreadsheets()

        match_sheet = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=MATCH_DATA_RANGE).execute()
        # Use for arg dateTimeRenderOption?
        match_sheet = pd.DataFrame(match_sheet.get('values', []))

        raw_deck_sheet = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=DECK_DATA_RANGE).execute()
        raw_deck_sheet = pd.DataFrame(raw_deck_sheet.get('values', []))

    except FileNotFoundError:
        # Download both the Game Data and Deck Data as individual csv files
        match_sheet = pd.read_csv('Game Data.csv').astype(str).replace('nan', None)
        raw_deck_sheet = pd.read_csv('Deck Data.csv', header=None).astype(str).replace('nan', None)

    # Column names redone to match the database fields
    match_sheet.columns = ['Season', 'Num', 'Date', 'Location', 'Turns',
                           'player1_name', 'player1_deck', 'player1_placement',
                           'player2_name', 'player2_deck', 'player2_placement',
                           'player3_name', 'player3_deck', 'player3_placement',
                           'player4_name', 'player4_deck', 'player4_placement']

    # Could optionally remove all entries where season = '' or a special IGNORE value
    match_sheet = match_sheet[match_sheet['Num'] != '45.5'].reset_index(drop=True)

    columns_with_int = ['Turns', 'player1_placement', 'player2_placement', 'player3_placement', 'player4_placement']
    match_sheet[columns_with_int] = match_sheet[columns_with_int].apply(pd.to_numeric)

    # Merged cells in the deck data messes with the import, need to reset the columns and apply a MultiIndex
    raw_deck_sheet.columns = raw_deck_sheet.iloc[1]
    players = raw_deck_sheet.iloc[0][raw_deck_sheet.iloc[0].str.len() > 0]
    raw_deck_sheet.columns = pd.MultiIndex.from_product([players, ['Name', 'Identity']])
    raw_deck_sheet = raw_deck_sheet.drop([0, 1]).reset_index(drop=True)

    # Reformatted version of the raw_deck_sheet
    deck_sheet = pd.DataFrame(columns=['Deck', 'Player', 'Identity'])

    for player in players:
        player_decks = raw_deck_sheet[player][raw_deck_sheet[player]['Name'].str.len() > 0]
        player_decks.columns = ['Deck', 'Identity']
        player_decks['Player'] = player
        deck_sheet = pd.concat([deck_sheet, player_decks])

    deck_sheet = deck_sheet.reset_index(drop=True)

    return match_sheet, deck_sheet


def get_turn_order_data(match_data):
    """This function groups the match data by Turn Order for the purposes of determining the relationship between turn
    order and placement.
    Outputs a DataFrame:
        Turn Order: A number representing whether the player went first, second, third, or fourth
        Variable: A metric that can be tracked, such as Wins, Matches, and so on
        Value: Some quantitative measure of the Variable, usually an amount (such as 10 matches played by a player)"""
    df = pd.DataFrame(columns=['Turn Order', 'Variable', 'Value'], dtype=int)

    # Wide-form dataframe needs to be converted to long-form by collapsing columns
    for n in range(MAX_PLAYERS):
        col = f'player{n + 1}_placement'
        went_nth = match_data[col].value_counts().reset_index().astype(int)

        went_nth.columns = ['Variable', 'Value']
        went_nth['Turn Order'] = n
        # Placements are shifted by three [4, 5, 6, 7] to avoid overlap with the turn order numbers [0, 1, 2, 3]
        went_nth['Variable'] += 3
        df = pd.concat([df, went_nth])

    # Reverse ordering for the variables because they need to be reversed for the stacked bar charts for some reason
    df = df.sort_values(['Turn Order', 'Variable'], ascending=[True, False]).reset_index(drop=True)
    # Once the dataframe is sorted, we can replace the integers with the strings we want to see in plots
    df['Turn Order'] = df['Turn Order'].map(TURN_ORDER_MAP)

    return df


def get_deck_data(match_sheet_data, deck_sheet_data):
    """This function groups the match data by Deck for the purposes of determining a variety of metrics for each deck.
    This also allows for a Player column to easily filter this dataframe by Player.
    Outputs a DataFrame:
        Deck: Names of decks as strings
        Player: The respective creators of each deck, as strings
        Identity: Color Identity of the deck, used for later determining the same metrics grouped by color
        Variable: A metric that can be tracked, such as Wins, Matches, and so on
        Value: Some quantitative measure of the Variable, usually an amount (such as 10 matches played by a player)"""
    df = pd.DataFrame(columns=['Deck', 'Variable', 'Value'])
    placements = pd.DataFrame()
    matches_played = pd.DataFrame()

    for n in range(MAX_PLAYERS):
        slot = f'player{n + 1}'
        went_nth = match_sheet_data[slot + '_deck'].value_counts()

        matches_played = pd.concat([matches_played, went_nth], axis=1).sum(axis=1)

        went_nth = went_nth.reset_index()
        went_nth.columns = ['Deck', 'Value']
        went_nth['Variable'] = n
        df = pd.concat([df, went_nth])

        went_nth_placed = match_sheet_data.groupby(slot + '_deck')[slot + '_placement'].value_counts()
        placements = pd.concat([placements, went_nth_placed], axis=1).fillna(0).sum(axis=1)

    placements = placements.reset_index()
    placements.columns = ['Deck', 'Variable', 'Value']
    placements['Variable'] += 3  # Differentiating from the turn order numbers (0, 1, 2, 3) -> (4, 5, 6, 7)
    df = pd.concat([df, placements])

    matches_played = matches_played.reset_index()
    matches_played.columns = ['Deck', 'Value']
    matches_played['Variable'] = 'Matches'
    df = pd.concat([df, matches_played])

    df['Player'] = df['Deck'].map(deck_sheet_data.set_index('Deck')['Player'])
    df['Identity'] = df['Deck'].map(deck_sheet_data.set_index('Deck')['Identity'])

    # Extra entry with no assigned Deck/Player/Identity, to capture the total number of matches played
    total_matches = pd.DataFrame({'Deck': '', 'Variable': 'Matches', 'Value': match_sheet_data['Season'].count(),
                                  'Identity': ' ', 'Player': ''}, index=[df.index[-1] + 1])
    df = pd.concat([df, total_matches])

    # Reverse ordering for the variables because they need to be reversed for the stacked bar charts for some reason
    df = df.sort_values(['Player', 'Deck', 'Variable'], ascending=[True, True, False])

    return df


def get_color_data(deck_data):
    """This function splits and then regroups the grouped deck data into metrics for each mono-color (and WUBRG)
    Outputs a DataFrame:
        Player: A player as a string
        Identity: Color Identity of a player's decks, later split into just the individual mono-colors
        Variable: A metric that can be tracked, such as Wins, Matches, and so on
        Value: Some quantitative measure of the Variable, usually an amount (such as 10 matches played by a player)"""
    # This line should probably be moved to the other function
    deck_data['Identity'] = deck_data['Identity'].replace('WUBRG', 'M')
    color_data = deck_data.copy()
    color_data['Identity'] = deck_data['Identity'].apply(list)
    color_data = color_data.explode('Identity')
    color_data['Identity'] = color_data['Identity'].map(COLOR_MAP)
    color_data = color_data.groupby(['Player', 'Identity', 'Variable'], as_index=False)['Value'].sum()

    # Reverse ordering for the variables because they need to be reversed for the stacked bar charts for some reason
    color_data = color_data.sort_values(['Player', 'Identity', 'Variable'], ascending=[True, True, False])

    return color_data


if __name__ == '__main__':
    # Can check if the file has been changed using Drive API, but it's nearly as slow as pulling the data
    # google_creds = Credentials.from_authorized_user_file('google_token.json', SCOPES)
    # service = build('drive', 'v3', credentials=google_creds)
    # results = service.files().get(fileId=SPREADSHEET_ID, fields='modifiedTime').execute()

    matches, decks = pull_spreadsheet_data()
    get_turn_order_data(matches)
    deck_df = get_deck_data(matches, decks)
    get_color_data(deck_df)
