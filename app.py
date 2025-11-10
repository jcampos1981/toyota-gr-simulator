"""
Toyota GR Racing Simulator - Dash Application
==============================================

Simulador de carreras en tiempo real con:
- Carga de archivos de telemetría (Parquet/CSV)
- Reproducción configurable de la carrera
- Detección automática de Yellow Flags
- Predicciones ML en tiempo real
- Visualización GPS del circuito

Desarrollado para el concurso "Hack the Track" 2024
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
import pickle
from pathlib import Path
import base64
import io
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_PATH = PROJECT_ROOT / "models"

# Cargar modelos ML
model_file = MODELS_PATH / "gradient_boosting_pit_decision.pkl"
encoders_file = MODELS_PATH / "label_encoders.pkl"
feature_config_file = MODELS_PATH / "feature_config.json"

ml_model = None
label_encoders = None
feature_columns = None

# Intentar cargar modelos ML (opcional)
try:
    if model_file.exists():
        with open(model_file, 'rb') as f:
            ml_model = pickle.load(f)
        with open(encoders_file, 'rb') as f:
            label_encoders = pickle.load(f)
        with open(feature_config_file, 'r') as f:
            feature_config = json.load(f)
            feature_columns = feature_config['feature_columns']
        print("[OK] ML models loaded successfully")
except Exception as e:
    print(f"[WARNING] Could not load ML models: {e}")
    print("[INFO] Simulator will run without ML predictions")
    ml_model = None
    label_encoders = None
    feature_columns = None

# ============================================================================
# INICIALIZAR APP
# ============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Toyota GR Racing Simulator"
)

server = app.server

# ============================================================================
# VARIABLES GLOBALES PARA ESTADO
# ============================================================================

# Datos de la carrera cargados (en memoria, NO como JSON)
race_data = {
    'telemetry': None,  # DataFrame completo en memoria
    'current_index': 0,
    'is_playing': False,
    'playback_speed': 1,
    'yellow_flags': [],
    'vehicles': []
}

# DataFrame global para evitar deserialización repetida
telemetry_df_global = None

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def parse_uploaded_file(contents, filename):
    """Parse archivo subido (CSV o Parquet)"""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif filename.endswith('.parquet'):
            df = pd.read_parquet(io.BytesIO(decoded))
        else:
            return None

        # Validar columnas requeridas
        required_cols = ['timestamp', 'vehicle_id', 'telemetry_name', 'telemetry_value']
        if not all(col in df.columns for col in required_cols):
            return None

        # Convertir timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        return df
    except Exception as e:
        print(f"Error parsing file: {e}")
        return None


def detect_yellow_flags_realtime(telemetry_df, speed_threshold=50):
    """Detecta períodos de Yellow Flag en telemetría completa"""
    speed_data = telemetry_df[telemetry_df['telemetry_name'] == 'speed'].copy()

    if len(speed_data) == 0:
        return []

    # Agrupar por ventanas de 5 segundos
    speed_data['time_window'] = speed_data['timestamp'].dt.floor('5S')
    avg_speed = speed_data.groupby('time_window')['telemetry_value'].mean()

    # Detectar períodos bajo threshold
    yellow_periods = []
    in_yellow = False
    yellow_start = None

    for time_window, speed in avg_speed.items():
        if speed < speed_threshold and not in_yellow:
            in_yellow = True
            yellow_start = time_window
        elif speed >= speed_threshold and in_yellow:
            yellow_end = time_window
            duration = (yellow_end - yellow_start).total_seconds()

            if duration >= 30:  # Mínimo 30 segundos
                yellow_periods.append({
                    'start': yellow_start,
                    'end': yellow_end,
                    'duration': duration
                })

            in_yellow = False
            yellow_start = None

    return yellow_periods


def predict_pit_decision(yellow_flag_data, circuit='barber'):
    """Predice decisión de pit usando el modelo ML"""
    if ml_model is None:
        return None

    try:
        # Crear features
        yellow_duration = yellow_flag_data['duration']
        min_speed = yellow_flag_data['min_speed']
        avg_speed = yellow_flag_data['avg_speed']
        speed_variance = avg_speed - min_speed

        is_long_yellow = 1 if yellow_duration > 300 else 0
        is_short_yellow = 1 if yellow_duration < 60 else 0
        very_low_speed = 1 if avg_speed < 10 else 0

        # Encode circuit
        circuit_encoded = label_encoders['circuit'].transform([circuit])[0]
        race_encoded = 0  # Default

        # Crear array de features en el orden correcto
        features = [
            yellow_duration,
            min_speed,
            avg_speed,
            speed_variance,
            is_long_yellow,
            is_short_yellow,
            very_low_speed,
            circuit_encoded,
            race_encoded
        ]

        X = pd.DataFrame([features], columns=feature_columns)
        prediction = ml_model.predict(X)[0]
        proba = ml_model.predict_proba(X)[0]

        return {
            'decision': 'PIT' if prediction == 1 else 'NO PIT',
            'confidence': max(proba) * 100,
            'pit_probability': proba[1] * 100
        }
    except Exception as e:
        print(f"Error predicting: {e}")
        return None


def create_track_map(telemetry_df, current_index=0, yellow_flags=[]):
    """Crea mapa GPS del circuito con posición actual"""
    gps_data = telemetry_df[telemetry_df['telemetry_name'].isin(['latitude', 'longitude'])].copy()

    if len(gps_data) == 0:
        return go.Figure()

    # Pivot para obtener lat/lon por timestamp
    gps_pivot = gps_data.pivot_table(
        index=['timestamp', 'vehicle_id'],
        columns='telemetry_name',
        values='telemetry_value'
    ).reset_index()

    if 'latitude' not in gps_pivot.columns or 'longitude' not in gps_pivot.columns:
        return go.Figure()

    fig = go.Figure()

    # Línea de carrera completa (todos los vehículos)
    for vehicle_id in gps_pivot['vehicle_id'].unique():
        vehicle_gps = gps_pivot[gps_pivot['vehicle_id'] == vehicle_id]

        fig.add_trace(go.Scattermapbox(
            lat=vehicle_gps['latitude'],
            lon=vehicle_gps['longitude'],
            mode='lines',
            line=dict(width=1, color='rgba(100, 100, 100, 0.3)'),
            name=f'Vehicle {vehicle_id} - Track',
            showlegend=False
        ))

    # Posición actual de cada vehículo
    current_time = telemetry_df['timestamp'].iloc[current_index]
    current_gps = gps_pivot[gps_pivot['timestamp'] <= current_time].groupby('vehicle_id').tail(1)

    for _, row in current_gps.iterrows():
        fig.add_trace(go.Scattermapbox(
            lat=[row['latitude']],
            lon=[row['longitude']],
            mode='markers',
            marker=dict(size=12, color='red'),
            name=f"Vehicle {row['vehicle_id']}",
            text=f"Vehicle {row['vehicle_id']}"
        ))

    # Configurar mapa
    if len(current_gps) > 0:
        center_lat = current_gps['latitude'].mean()
        center_lon = current_gps['longitude'].mean()
    else:
        center_lat = gps_pivot['latitude'].mean()
        center_lon = gps_pivot['longitude'].mean()

    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            center=dict(lat=center_lat, lon=center_lon),
            zoom=14
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=500,
        paper_bgcolor='#222',
        plot_bgcolor='#222'
    )

    return fig


def create_telemetry_chart(telemetry_df, current_index, telemetry_type='speed'):
    """Crea gráfico de telemetría (velocidad, RPM, etc.)"""
    data = telemetry_df[telemetry_df['telemetry_name'] == telemetry_type].copy()

    if len(data) == 0:
        return go.Figure()

    fig = go.Figure()

    current_time = telemetry_df['timestamp'].iloc[current_index]

    # Mostrar últimos 60 segundos
    time_window_start = current_time - timedelta(seconds=60)
    windowed_data = data[(data['timestamp'] >= time_window_start) & (data['timestamp'] <= current_time)]

    for vehicle_id in windowed_data['vehicle_id'].unique():
        vehicle_data = windowed_data[windowed_data['vehicle_id'] == vehicle_id]

        fig.add_trace(go.Scatter(
            x=vehicle_data['timestamp'],
            y=vehicle_data['telemetry_value'],
            mode='lines',
            name=f'Vehicle {vehicle_id}',
            line=dict(width=2)
        ))

    # Línea vertical en posición actual
    fig.add_vline(x=current_time, line_dash="dash", line_color="red")

    fig.update_layout(
        title=f'{telemetry_type.capitalize()} - Last 60s',
        xaxis_title='Time',
        yaxis_title=telemetry_type.capitalize(),
        height=300,
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor='#222',
        plot_bgcolor='#333',
        font=dict(color='white'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    return fig


# ============================================================================
# LAYOUT
# ============================================================================

app.layout = dbc.Container([
    dcc.Store(id='race-data-store'),
    dcc.Store(id='playback-state', data={'is_playing': False, 'current_index': 0}),
    dcc.Interval(id='playback-interval', interval=500, disabled=True),  # 500ms en lugar de 100ms

    # Header
    dbc.Row([
        dbc.Col([
            html.H1("🏁 Toyota GR Racing Simulator", className='text-center mb-2'),
            html.P("Real-Time Race Replay with ML Predictions", className='text-center text-muted')
        ])
    ], className='mt-4 mb-4'),

    # File Upload Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("📁 Load Race Data")),
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select Telemetry File'),
                            html.Br(),
                            html.Small('(CSV or Parquet format)', className='text-muted')
                        ]),
                        style={
                            'width': '100%',
                            'height': '100px',
                            'lineHeight': '100px',
                            'borderWidth': '2px',
                            'borderStyle': 'dashed',
                            'borderRadius': '10px',
                            'textAlign': 'center',
                            'backgroundColor': '#333'
                        },
                        multiple=False
                    ),
                    html.Div(id='upload-status', className='mt-3')
                ])
            ])
        ])
    ], className='mb-4'),

    # Playback Controls
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("🎮 Playback Controls")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.ButtonGroup([
                                dbc.Button("⏮️ Reset", id='btn-reset', color='secondary', size='sm'),
                                dbc.Button("▶️ Play", id='btn-play', color='success', size='sm'),
                                dbc.Button("⏸️ Pause", id='btn-pause', color='warning', size='sm'),
                            ])
                        ], width=4),
                        dbc.Col([
                            html.Label("Playback Speed:", className='me-2'),
                            dcc.Slider(
                                id='speed-slider',
                                min=0.5,
                                max=10,
                                step=0.5,
                                value=1,
                                marks={0.5: '0.5x', 1: '1x', 2: '2x', 5: '5x', 10: '10x'},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], width=8)
                    ]),
                    html.Hr(),
                    html.Div(id='playback-info', className='mt-2'),
                    dbc.Progress(id='progress-bar', value=0, className='mt-2')
                ])
            ])
        ])
    ], className='mb-4'),

    # Race Visualization
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("🗺️ Race Track - Live Position")),
                dbc.CardBody([
                    dcc.Graph(id='track-map', config={'displayModeBar': False})
                ])
            ])
        ], width=8),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("🤖 ML Predictions")),
                dbc.CardBody([
                    html.Div(id='ml-predictions')
                ])
            ], className='mb-3'),
            dbc.Card([
                dbc.CardHeader(html.H4("🚩 Yellow Flags")),
                dbc.CardBody([
                    html.Div(id='yellow-flag-status')
                ])
            ])
        ], width=4)
    ], className='mb-4'),

    # Telemetry Charts
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("📊 Live Telemetry")),
                dbc.CardBody([
                    dcc.Graph(id='telemetry-speed'),
                    dcc.Graph(id='telemetry-throttle')
                ])
            ])
        ])
    ], className='mb-4'),

    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P("Toyota GR Racing Simulator | Hack the Track 2024",
                   className='text-center text-muted')
        ])
    ])
], fluid=True, style={'backgroundColor': '#1a1a1a', 'minHeight': '100vh'})

# ============================================================================
# CALLBACKS
# ============================================================================

@app.callback(
    [Output('race-data-store', 'data'),
     Output('upload-status', 'children'),
     Output('playback-state', 'data', allow_duplicate=True)],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def load_race_data(contents, filename):
    """Cargar archivo de telemetría"""
    global telemetry_df_global

    if contents is None:
        return None, "", {'is_playing': False, 'current_index': 0}

    df = parse_uploaded_file(contents, filename)

    if df is None:
        return None, dbc.Alert("Error: Invalid file format", color='danger'), {'is_playing': False, 'current_index': 0}

    # Detectar Yellow Flags
    yellow_flags = detect_yellow_flags_realtime(df)

    # OPTIMIZACIÓN: Guardar DataFrame en variable global en lugar de JSON
    telemetry_df_global = df

    # Guardar solo metadatos (NO el DataFrame completo)
    race_data_json = {
        'telemetry': 'loaded_in_memory',  # NO serializar a JSON
        'yellow_flags': yellow_flags,
        'total_records': len(df),
        'vehicles': df['vehicle_id'].unique().tolist(),
        'start_time': df['timestamp'].min().isoformat(),
        'end_time': df['timestamp'].max().isoformat()
    }

    status_msg = dbc.Alert([
        html.H5(f"✓ {filename} loaded successfully!", className='alert-heading'),
        html.P(f"Records: {len(df):,} | Vehicles: {len(race_data_json['vehicles'])} | Yellow Flags: {len(yellow_flags)}")
    ], color='success')

    return race_data_json, status_msg, {'is_playing': False, 'current_index': 0}


@app.callback(
    Output('playback-state', 'data', allow_duplicate=True),
    [Input('btn-play', 'n_clicks'),
     Input('btn-pause', 'n_clicks'),
     Input('btn-reset', 'n_clicks')],
    State('playback-state', 'data'),
    prevent_initial_call=True
)
def control_playback(play_clicks, pause_clicks, reset_clicks, current_state):
    """Controlar reproducción"""
    ctx = callback_context

    if not ctx.triggered:
        return current_state

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'btn-play':
        current_state['is_playing'] = True
    elif button_id == 'btn-pause':
        current_state['is_playing'] = False
    elif button_id == 'btn-reset':
        current_state['is_playing'] = False
        current_state['current_index'] = 0

    return current_state


@app.callback(
    Output('playback-interval', 'disabled'),
    Input('playback-state', 'data')
)
def toggle_interval(state):
    """Activar/desactivar interval según estado de reproducción"""
    return not state.get('is_playing', False)


@app.callback(
    Output('playback-state', 'data'),
    Input('playback-interval', 'n_intervals'),
    [State('playback-state', 'data'),
     State('race-data-store', 'data'),
     State('speed-slider', 'value')],
    prevent_initial_call=True
)
def update_playback_position(n_intervals, state, race_data_json, speed):
    """Actualizar posición de reproducción"""
    if race_data_json is None or not state.get('is_playing', False):
        return state

    total_records = race_data_json['total_records']
    current_index = state.get('current_index', 0)

    # Incrementar índice según velocidad (ajustado para intervalo de 500ms)
    increment = int(speed * 50)  # 50 registros por tick (500ms) = 100 registros/segundo
    new_index = current_index + increment

    if new_index >= total_records:
        state['is_playing'] = False
        state['current_index'] = total_records - 1
    else:
        state['current_index'] = new_index

    return state


@app.callback(
    [Output('track-map', 'figure'),
     Output('telemetry-speed', 'figure'),
     Output('telemetry-throttle', 'figure'),
     Output('playback-info', 'children'),
     Output('progress-bar', 'value'),
     Output('yellow-flag-status', 'children'),
     Output('ml-predictions', 'children')],
    Input('playback-state', 'data'),
    State('race-data-store', 'data')
)
def update_visualizations(state, race_data_json):
    """Actualizar todas las visualizaciones"""
    global telemetry_df_global

    if race_data_json is None or telemetry_df_global is None:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            paper_bgcolor='#222',
            plot_bgcolor='#333',
            font=dict(color='white')
        )
        return (empty_fig, empty_fig, empty_fig,
                "No data loaded", 0,
                "No data", "No data")

    # OPTIMIZACIÓN: Usar DataFrame global en lugar de deserializar JSON
    df = telemetry_df_global

    current_index = state.get('current_index', 0)
    total_records = race_data_json['total_records']

    # Mapa
    track_fig = create_track_map(df, current_index, race_data_json['yellow_flags'])

    # Telemetría
    speed_fig = create_telemetry_chart(df, current_index, 'speed')
    throttle_fig = create_telemetry_chart(df, current_index, 'throttle')

    # Info de reproducción
    current_time = df['timestamp'].iloc[current_index]
    elapsed = (current_time - df['timestamp'].min()).total_seconds()
    total_duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()

    playback_info = html.Div([
        html.Strong(f"Current Time: {current_time.strftime('%H:%M:%S')}"),
        html.Br(),
        f"Elapsed: {elapsed:.1f}s / {total_duration:.1f}s | Record: {current_index:,} / {total_records:,}"
    ])

    progress = (current_index / total_records * 100) if total_records > 0 else 0

    # Yellow Flag status
    yellow_flags = race_data_json['yellow_flags']
    in_yellow = False
    current_yellow = None

    for yf in yellow_flags:
        yf_start = pd.to_datetime(yf['start'])
        yf_end = pd.to_datetime(yf['end'])
        if yf_start <= current_time <= yf_end:
            in_yellow = True
            current_yellow = yf
            break

    if in_yellow:
        yellow_status = dbc.Alert([
            html.H5("🚩 YELLOW FLAG", className='alert-heading'),
            html.P(f"Duration: {current_yellow['duration']:.1f}s")
        ], color='warning')
    else:
        yellow_status = dbc.Alert("🟢 Green Flag - Racing", color='success')

    # ML Predictions
    if in_yellow and current_yellow and ml_model:
        # Calcular speeds durante este yellow
        yf_start = pd.to_datetime(current_yellow['start'])
        yf_end = pd.to_datetime(current_yellow['end'])

        yf_data = df[(df['timestamp'] >= yf_start) & (df['timestamp'] <= yf_end)]
        speed_data = yf_data[yf_data['telemetry_name'] == 'speed']['telemetry_value']

        if len(speed_data) > 0:
            prediction_data = {
                'duration': current_yellow['duration'],
                'min_speed': speed_data.min(),
                'avg_speed': speed_data.mean()
            }

            prediction = predict_pit_decision(prediction_data)

            if prediction:
                ml_content = dbc.Alert([
                    html.H5(f"🤖 Recommendation: {prediction['decision']}", className='alert-heading'),
                    html.P(f"Confidence: {prediction['confidence']:.1f}%"),
                    html.P(f"Pit Probability: {prediction['pit_probability']:.1f}%"),
                    dbc.Progress(value=prediction['pit_probability'], color='info', className='mt-2')
                ], color='info' if prediction['decision'] == 'PIT' else 'secondary')
            else:
                ml_content = "Calculating..."
        else:
            ml_content = "Waiting for data..."
    else:
        ml_content = dbc.Alert("No Yellow Flag - No prediction needed", color='secondary')

    return track_fig, speed_fig, throttle_fig, playback_info, progress, yellow_status, ml_content


# ============================================================================
# EJECUTAR APP
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("Toyota GR Racing Simulator")
    print("="*70)
    print("\nStarting Dash application...")
    print("Open your browser at: http://127.0.0.1:8050")
    print("\nPress Ctrl+C to stop the server")
    print("="*70 + "\n")

    # OPTIMIZACIÓN: Debug mode deshabilitado para reducir logs
    app.run(debug=False, host='127.0.0.1', port=8050)
