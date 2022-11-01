import pandas as pd
import math
import numpy as np
from dash import Dash, html, dcc, Input, Output
import plotly.graph_objects as go
import json

app = Dash(__name__)
server = app.server

theme = {
    "background": "#fdf6e3",
    "layer": "#eee8d5",
    "on-bg-primary": "#657b83",
    "on-bg-secondary": "#93a1a1",
    "on-layer-primary": "#586e75",
    "on-layer-secondary": "#839496",
    "interactive": "#268bd2",
}

app.layout = html.Div(children=[
    # Page title
    html.H1(children='SRA Leaderboard'),
    
    # Select controls
    html.Div(children=[
        html.Div(children=[
            html.Label('Leaderboard'),
            dcc.Dropdown(
                ['Hot Stint', 'Hot Lap'],
                'Hot Stint',
                id='leaderboard-select'
            )
        ], className='select-container', style={'flex': 1}),
        html.Div(children=[
            html.Label('Track'),
            dcc.Dropdown(
                ['paul_ricard', 'barcelona', 'brands_hatch', 'cota', 'donington', 'hungaroring', 'imola', 'indianapolis', 'kyalami', 'laguna_seca', 'misano', 'monza', 'mount_panorama', 'nurburgring', 'oulton_park', 'silverstone', 'snetterton', 'spa', 'suzuka', 'watkins_glen', 'zandvoort', 'zolder'], 'paul_ricard',
                id='track-select',
            )
        ], className='select-container', style={'flex': 1}),
        html.Div(children=[
            html.Label('Sector'),
            dcc.Dropdown(
                options={
                    's1_delta': '1', 
                    's2_delta': '2', 
                    's3_delta': '3',
                },
                id='sector-select'
            )
        ], className='select-container', style={'flex': 1}),
        html.Div(children=[
            html.Label('Car'),
            dcc.Dropdown(
                id='car-select',
            )
        ], className='select-container', style={'flex': 1}),
        html.Div(children=[
            html.Label('Driver'),
            dcc.Dropdown(
                id='driver-select',
            )
        ], className='select-container', style={'flex': 1}),
    ], style={'display': 'flex', 'flex-direction': 'row'}),

    # Charts
    dcc.Graph(id='leaderboard-hist'),
    dcc.Graph(id='leaderboard-table'),

    # Data
    dcc.Store(id='base-data'),
    dcc.Store(id='leaderboard-data'),
    dcc.Store(id='filtered-data')
])


# Get leaderboard for selected track
@app.callback(
    Output('base-data', 'data'),
    Input('leaderboard-select', 'value'),
    Input('track-select', 'value'),
)
def get_leaderboard(selected_leaderboard, track="paul_ricard"):
    if selected_leaderboard == 'Hot Stint':
        url = 'https://www.simracingalliance.com/leaderboards/hot_stint/' + track + '/?unique_drivers=1'
    elif selected_leaderboard == 'Hot Lap':
        url = 'https://www.simracingalliance.com/leaderboards/hot_lap/' + track + '/?season=4'
    leaderboard = pd.read_html(url)[0]

    if 'Date' in leaderboard.columns:
        leaderboard = leaderboard.drop('Date', axis=1)

    leaderboard.columns = ['rank', 'name', 'car', 'lap_string', 's1', 's2', 's3']

    for s in ['s1', 's2', 's3']:
        leaderboard[s] = leaderboard[s].astype(float)
    
    
    leaderboard['lap_time'] = leaderboard['s1'] + leaderboard['s2'] + leaderboard['s3']
    leaderboard['lap_delta'] = leaderboard['lap_time'] - min(leaderboard['lap_time'])
    leaderboard['s1_delta'] = leaderboard['s1'] - leaderboard['s1'].min()
    leaderboard['s2_delta'] = leaderboard['s2'] - leaderboard['s2'].min()
    leaderboard['s3_delta'] = leaderboard['s3'] - leaderboard['s3'].min()
    leaderboard['lap_string'] = leaderboard['lap_string'].str[0:8]
    leaderboard = leaderboard.sort_values('lap_delta')
    return leaderboard.to_json(orient='split')


# Filter leaderboard based on car and sector selections
@app.callback(
    Output('leaderboard-data', 'data'),
    Output('filtered-data', 'data'),
    Input('base-data', 'data'),
    Input('sector-select', 'value'),
    Input('car-select', 'value'),
)
def filter_data(base_data, selected_sector, selected_car):
    leaderboard = pd.read_json(base_data, orient='split')

    col = 'lap_delta'
    if selected_sector:
        col = selected_sector
        leaderboard = leaderboard.sort_values(col)
    
    filtered_leaderboard = leaderboard
    if selected_car:
        filtered_leaderboard = filtered_leaderboard[filtered_leaderboard['car']==selected_car]
    filtered_leaderboard['filtered_delta'] = filtered_leaderboard[col] - min(filtered_leaderboard[col])
    filtered_leaderboard = filtered_leaderboard.reset_index(drop=True)
    return leaderboard.to_json(orient='split'), filtered_leaderboard.to_json(orient='split')


# Get options for dropdowns
@app.callback(
    Output('car-select', 'options'),
    Output('driver-select', 'options'),
    Input('leaderboard-data', 'data'),
    Input('filtered-data', 'data')
)
def set_options(leaderboard_data, filtered_data):
    leaderboard = pd.read_json(leaderboard_data, orient='split')
    filtered_leaderboard = pd.read_json(filtered_data, orient='split')
    car_options = leaderboard['car'].unique()
    driver_options = filtered_leaderboard['name'].unique()
    return car_options, driver_options


# Create table
@app.callback(
    Output('leaderboard-table', 'figure'),
    Input('filtered-data', 'data'),
)
def generate_table(filtered_data):
    filtered_leaderboard = pd.read_json(filtered_data, orient='split')

    # Add plus signs to delta columns
    lap_delta = '+' + filtered_leaderboard['lap_delta'].round(3).astype(str)
    lap_delta[0] = filtered_leaderboard.loc[0, 'lap_delta'].round(3)
    filtered_delta = '+' + filtered_leaderboard['filtered_delta'].round(3).astype(str)
    filtered_delta[0] = filtered_leaderboard.loc[0, 'filtered_delta'].round(3)

    # Generate table
    leaderboard_table = go.Figure(
        data=go.Table(
            header=dict(
                values=['Rank', 'Name', 'Car', 'Sector 1', 'Sector 2', 'Sector 3', 'Lap time', 'Lap Delta', 'Filtered Delta'],
                align=['left', 'left', 'left', 'right', 'right', 'right', 'right'],
                fill_color=theme['on-layer-primary'],
                height=32,
                font=dict(
                    size=14,
                    color=theme['layer'],
                    family='Helvetica Bold'
                )
            ),
            cells=dict(
                values=[
                    filtered_leaderboard['rank'],
                    filtered_leaderboard['name'],
                    filtered_leaderboard['car'],
                    round(filtered_leaderboard['s1'], 3),
                    round(filtered_leaderboard['s2'], 3),
                    round(filtered_leaderboard['s3'], 3),
                    filtered_leaderboard['lap_string'],
                    lap_delta,
                    filtered_delta
                ],
                align=['left', 'left', 'left', 'right', 'right', 'right', 'right'],
                fill_color=theme['layer'],
                height=32,
                font=dict(
                    size=14,
                    color=theme['on-layer-primary'],
                    family='Helvetica'
                )
            ),
            columnwidth=[1, 3, 2, 1, 1, 1, 1, 1, 1],
        )
    )
    leaderboard_table.update_layout(
        plot_bgcolor = theme['layer'],
        paper_bgcolor=theme['background'],
        height = len(filtered_leaderboard) * 32 + 64,
        margin=dict(t=0, r=0, b=0, l=0)
    )

    return leaderboard_table


# Create histogram
@app.callback(
    Output('leaderboard-hist', 'figure'),
    Input('leaderboard-data', 'data'),
    Input('filtered-data', 'data'),
    Input('sector-select', 'value'),
    Input('driver-select', 'value')
)
def generate_histogram(leaderboard_data, filtered_data, selected_sector, selected_driver):
    leaderboard = pd.read_json(leaderboard_data, orient='split')
    filtered_leaderboard = pd.read_json(filtered_data, orient='split')
    
    col = 'lap_delta'
    if selected_sector:
        col = selected_sector

    x_max = round(max(leaderboard[col]*2))/2
    nbins = int(x_max*2)+1

    total_colors = nbins*[theme['on-layer-secondary']]
    filter_colors = nbins*[theme['on-layer-primary']]
    if selected_driver:
        try:
            driver_delta = filtered_leaderboard[filtered_leaderboard['name']==selected_driver][col].values[0]
            highlight_index = int(round(driver_delta*2))   
            filter_colors[highlight_index] = theme['interactive']
        except:
            None

    fig = go.Figure()

    total_hist = go.Histogram(
        x = leaderboard[col],
        xbins=dict(
            start=0,
            size=0.5,
        ),
        marker=dict(
            color=total_colors,
        )
    )

    # Filtered histogram
    filtered_hist = go.Histogram(
        x = filtered_leaderboard[col],
        xbins=dict(
            start=0,
            size=0.5,
        ),
        marker=dict(
            color=filter_colors,
        )
    )

    fig.add_trace(total_hist)
    fig.add_trace(filtered_hist)

    fig.update_xaxes(
        title="Delta vs Leader (s)",
        dtick=0.5,
        titlefont=dict(
            size=14,
            color=theme['on-bg-primary']
        ),
        tickfont=dict(
            size=12,
            color=theme['on-bg-secondary']
        )
    )

    fig.update_yaxes(
        title="Number of Drivers",
        gridcolor=theme['background'],
        zeroline=False,
        titlefont=dict(
            size=14,
            color=theme['on-bg-primary']
        ),
        tickfont=dict(
            size=12,
            color=theme['on-bg-secondary']
        )
    )

    fig.update_layout(
        barmode='overlay',
        showlegend=False,
        bargap=0.025,
        plot_bgcolor = theme['layer'],
        paper_bgcolor=theme['background'],
        margin=dict(t=0, r=0, b=0, l=0)
        
    )

    #fig.add_trace(time_table)
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)