"""
Toyota GR Racing Simulator - VERSIÓN LIGERA
==============================================

Simulador optimizado con:
- Tablas de valores en lugar de gráficas pesadas
- Actualización cada segundo (1000ms)
- Uso mínimo de memoria y CPU
- Alertas de Yellow Flags en tiempo real
- Archivos temporales en H: drive

Desarrollado para el concurso "Hack the Track" 2024
"""

# CONFIGURAR H: DRIVE PARA TEMPORALES ANTES DE IMPORTAR
import os
import sys
from pathlib import Path

# Configurar directorios temporales en H: drive
TEMP_DIR = Path("H:/Toyota Project/temp")
TEMP_DIR.mkdir(exist_ok=True)

os.environ['TEMP'] = str(TEMP_DIR)
os.environ['TMP'] = str(TEMP_DIR)
os.environ['TMPDIR'] = str(TEMP_DIR)
os.environ['MPLCONFIGDIR'] = str(TEMP_DIR)
os.environ['PYTHON_EGG_CACHE'] = str(TEMP_DIR)

print(f"[CONFIG] Archivos temporales configurados en: {TEMP_DIR}")

import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import pickle
import base64
import io
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_PATH = PROJECT_ROOT / "models"

# Cargar modelos ML
ml_model = None
label_encoders = None

# Variable global para mantener la última recomendación ML
last_ml_recommendation = None
feature_columns = None

try:
    model_file = MODELS_PATH / "gradient_boosting_pit_decision.pkl"
    encoders_file = MODELS_PATH / "label_encoders.pkl"
    feature_config_file = MODELS_PATH / "feature_config.json"

    if model_file.exists():
        with open(model_file, 'rb') as f:
            ml_model = pickle.load(f)
        with open(encoders_file, 'rb') as f:
            label_encoders = pickle.load(f)

        import json
        with open(feature_config_file, 'r') as f:
            feature_config = json.load(f)
            feature_columns = feature_config['feature_columns']

        print("[OK] ML models loaded successfully")
        print(f"[OK] Features: {len(feature_columns)}")
except Exception as e:
    print(f"[INFO] ML model not available: {e}")
    ml_model = None

# ============================================================================
# INICIALIZAR APP
# ============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Toyota GR Racing Simulator - Lightweight"
)

server = app.server

# DataFrame global
telemetry_df_global = None

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def parse_uploaded_file(contents, filename):
    """Parse archivo subido"""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        if filename.endswith('.parquet'):
            df = pd.read_parquet(io.BytesIO(decoded))
        elif filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        else:
            return None

        # Validar columnas
        required_cols = ['timestamp', 'vehicle_id', 'telemetry_name', 'telemetry_value']
        if not all(col in df.columns for col in required_cols):
            return None

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        return df
    except Exception as e:
        print(f"Error parsing file: {e}")
        return None


def detect_yellow_flags(df):
    """Detecta Yellow Flags"""
    speed_data = df[df['telemetry_name'] == 'speed'].copy()
    if len(speed_data) == 0:
        return []

    speed_data['time_window'] = speed_data['timestamp'].dt.floor('5S')
    avg_speed = speed_data.groupby('time_window')['telemetry_value'].mean()

    yellow_periods = []
    in_yellow = False
    yellow_start = None

    for time_window, speed in avg_speed.items():
        if speed < 50 and not in_yellow:
            in_yellow = True
            yellow_start = time_window
        elif speed >= 50 and in_yellow:
            yellow_end = time_window
            duration = (yellow_end - yellow_start).total_seconds()

            if duration >= 30:
                yellow_periods.append({
                    'start': yellow_start,
                    'end': yellow_end,
                    'duration': duration
                })

            in_yellow = False

    return yellow_periods


def get_current_data_snapshot(df, current_index, window_size=10):
    """Obtiene snapshot de datos actuales"""
    if df is None or current_index >= len(df):
        return pd.DataFrame()

    # Últimos N registros
    start_idx = max(0, current_index - window_size)
    snapshot = df.iloc[start_idx:current_index + 1].copy()

    return snapshot


def predict_pit_decision(yellow_flag_data, circuit='indianapolis'):
    """Predice decisión de pit usando ML"""
    if ml_model is None or label_encoders is None or feature_columns is None:
        return None

    try:
        # Extraer features
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

        # Crear features array
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
            'pit_probability': proba[1] * 100 if len(proba) > 1 else 0
        }
    except Exception as e:
        print(f"Error predicting: {e}")
        return None


# ============================================================================
# LAYOUT
# ============================================================================

app.layout = dbc.Container([
    dcc.Store(id='race-data-store'),
    dcc.Store(id='playback-state', data={'is_playing': False, 'current_index': 0}),
    dcc.Interval(id='playback-interval', interval=1000, disabled=True),  # 1 segundo

    # Header
    dbc.Row([
        dbc.Col([
            html.H2("Toyota GR Racing Simulator - LIGHTWEIGHT", className='text-center mb-2'),
            html.P("Optimized version for low resource consumption", className='text-center text-muted')
        ])
    ], className='mt-3 mb-3'),

    # File Upload
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Load Telemetry Data")),
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Drag file or ',
                            html.A('Select'),
                            html.Br(),
                            html.Small('(Parquet o CSV)', className='text-muted')
                        ]),
                        style={
                            'width': '100%',
                            'height': '80px',
                            'lineHeight': '80px',
                            'borderWidth': '2px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'backgroundColor': '#333'
                        },
                        multiple=False
                    ),
                    html.Div(id='upload-status', className='mt-2')
                ])
            ])
        ])
    ], className='mb-3'),

    # SECCIÓN DE MONITOREO (con ID para scroll automático)
    html.Div(id='monitoring-section', children=[
        # Controls
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("Playback Controls", className='mb-0'), style={'padding': '8px'}),
                    dbc.CardBody([
                        dbc.ButtonGroup([
                            dbc.Button("▶ Play", id='btn-play', color='success', size='sm'),
                            dbc.Button("⏸ Pause", id='btn-pause', color='warning', size='sm'),
                            dbc.Button("⏮ Reset", id='btn-reset', color='secondary', size='sm'),
                        ], className='mb-2'),
                        html.Div([
                            html.Small("Speed:", className='me-2'),
                            dcc.Slider(
                                id='speed-slider',
                                min=1,
                                max=25,
                                step=1,
                                value=1,
                                marks={1: '1x', 5: '5x', 10: '10x', 15: '15x', 20: '20x', 25: '25x'},
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                        ])
                    ], style={'padding': '10px'})
                ])
            ], width=12)
        ], className='mb-3'),

        # Hidden elements for callbacks (info now shown in Live Telemetry)
        html.Div(id='playback-info', style={'display': 'none'}),
        dbc.Progress(id='progress-bar', value=0, style={'display': 'none'}),
        html.Div(id='yellow-flag-status', style={'display': 'none'}),
        html.Div(id='ml-predictions', style={'display': 'none'}),

        # Telemetry Cards (Professional Dashboard)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("🏎️ LIVE TELEMETRY - Professional Monitoring", className='mb-0 text-center',
                                          style={'fontWeight': 'bold', 'color': '#00d4ff'}),
                                  style={'padding': '12px', 'backgroundColor': '#1a1a2e'}),
                    dbc.CardBody([
                        html.Div(id='telemetry-tables')
                    ], style={'padding': '15px'})
                ])
            ])
        ], className='mb-3'),
    ]),

    # Resumen de Yellow Flags (al finalizar la simulación)
    dbc.Row([
        dbc.Col([
            html.Div(id='yellow-flags-summary')
        ])
    ], className='mb-3'),

    # Footer
    html.Hr(),
    html.P("Toyota GR Racing Simulator - Lightweight",
           className='text-center text-muted small')

], fluid=True, style={'backgroundColor': '#1a1a1a', 'minHeight': '100vh'})

# ============================================================================
# CALLBACKS
# ============================================================================

# Clientside callback para scroll automático al presionar Play
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            const element = document.getElementById('monitoring-section');
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
        return '';
    }
    """,
    Output('playback-info', 'className'),  # Dummy output
    Input('btn-play', 'n_clicks'),
    prevent_initial_call=True
)

@app.callback(
    [Output('race-data-store', 'data'),
     Output('upload-status', 'children'),
     Output('playback-state', 'data', allow_duplicate=True)],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def load_race_data(contents, filename):
    """Cargar archivo"""
    global telemetry_df_global

    if contents is None:
        return None, "", {'is_playing': False, 'current_index': 0}

    df = parse_uploaded_file(contents, filename)

    if df is None:
        return None, dbc.Alert("Error: Formato inválido", color='danger'), {'is_playing': False, 'current_index': 0}

    # Detectar Yellow Flags
    yellow_flags = detect_yellow_flags(df)

    # Guardar en memoria
    telemetry_df_global = df

    race_data_json = {
        'telemetry': 'loaded_in_memory',
        'yellow_flags': yellow_flags,
        'total_records': len(df),
        'vehicles': df['vehicle_id'].unique().tolist(),
        'start_time': df['timestamp'].min().isoformat(),
        'end_time': df['timestamp'].max().isoformat()
    }

    status_msg = dbc.Alert([
        html.H6(f"✓ {filename} loaded", className='alert-heading'),
        html.Small(f"Records: {len(df):,} | Vehicles: {len(race_data_json['vehicles'])} | Yellow Flags: {len(yellow_flags)}")
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
    """Activar/desactivar interval"""
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
    """Actualizar posición"""
    if race_data_json is None or not state.get('is_playing', False):
        return state

    total_records = race_data_json['total_records']
    current_index = state.get('current_index', 0)

    # Avanzar N registros por segundo según velocidad
    increment = int(speed * 100)  # 100 registros por segundo base
    new_index = current_index + increment

    if new_index >= total_records:
        state['is_playing'] = False
        state['current_index'] = total_records - 1
    else:
        state['current_index'] = new_index

    return state


@app.callback(
    [Output('telemetry-tables', 'children'),
     Output('playback-info', 'children'),
     Output('progress-bar', 'value'),
     Output('yellow-flag-status', 'children'),
     Output('ml-predictions', 'children'),
     Output('yellow-flags-summary', 'children')],
    Input('playback-state', 'data'),
    State('race-data-store', 'data')
)
def update_displays(state, race_data_json):
    """Actualizar todas las visualizaciones"""
    global telemetry_df_global

    if race_data_json is None or telemetry_df_global is None:
        return "No data loaded", "No data", 0, "No data", "No data", ""

    df = telemetry_df_global
    current_index = state.get('current_index', 0)
    total_records = race_data_json['total_records']

    # Info de reproducción
    current_time = df['timestamp'].iloc[current_index]
    elapsed = (current_time - df['timestamp'].min()).total_seconds()
    total_duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()

    progress = (current_index / total_records * 100) if total_records > 0 else 0

    # Datos actuales de cada vehículo (FORMATO HORIZONTAL)
    current_data = df[df.index <= current_index].groupby(['vehicle_id', 'telemetry_name']).tail(1)

    # Calcular posiciones de carrera basado en progreso (índice actual)
    vehicle_progress = df[df.index <= current_index].groupby('vehicle_id')['timestamp'].max()
    vehicle_positions = vehicle_progress.rank(method='min', ascending=False).astype(int).to_dict()

    # Calcular número de vuelta del líder
    leader_id = vehicle_progress.idxmax() if len(vehicle_progress) > 0 else None

    current_lap = 1  # Valor por defecto
    if leader_id is not None:
        # Obtener lap_distance del líder
        leader_data = df[(df.index <= current_index) & (df['vehicle_id'] == leader_id)]
        leader_lap_dist_data = leader_data[leader_data['telemetry_name'] == 'lap_distance']

        if len(leader_lap_dist_data) > 0:
            # Contar cuántas veces lap_distance "resetea" a un valor bajo (nueva vuelta)
            lap_distances = leader_lap_dist_data['telemetry_value'].values

            # Detectar resets: cuando lap_distance disminuye significativamente
            lap_count = 1
            for i in range(1, len(lap_distances)):
                if lap_distances[i] < lap_distances[i-1] - 1000:  # Reset detectado
                    lap_count += 1
            current_lap = lap_count

    playback_info = html.Div([
        html.Strong(f"Time: {current_time.strftime('%H:%M:%S')}", style={'fontSize': '14px'}),
        html.Br(),
        html.Strong(f"🏁 Lap: {current_lap}", style={'fontSize': '16px', 'color': '#00d4ff'}),
        html.Br(),
        html.Small(f"Elapsed: {elapsed:.1f}s / {total_duration:.1f}s | Record: {current_index:,} / {total_records:,}")
    ])

    # ============================================================================
    # DASHBOARD PROFESIONAL: Solo seguimiento de 2do y 3er lugar
    # ============================================================================

    # DETECTAR longitud del circuito automáticamente
    lap_dist_all = df[df['telemetry_name'] == 'lap_distance']['telemetry_value']
    track_length = lap_dist_all.max() if len(lap_dist_all) > 0 else 4000

    # CALCULAR YELLOW FLAG STATUS (antes del loop de vehículos)
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

    # Determinar mensaje y color de Yellow Flag
    if in_yellow:
        yf_text = "🚩 YELLOW"
        yf_color = '#ffc107'
        yf_bg = '#3a2a1a'
        yf_duration_text = f"{current_yellow['duration']:.0f}s"
    else:
        yf_text = "🟢 GREEN"
        yf_color = '#4caf50'
        yf_bg = '#1a3a2a'
        yf_duration_text = "Racing"

    # MOSTRAR TODOS los vehículos disponibles
    vehicles_to_monitor = []
    for vehicle_id, pos in vehicle_positions.items():
        vehicles_to_monitor.append((vehicle_id, pos))

    # Ordenar por posición
    vehicles_to_monitor.sort(key=lambda x: x[1])

    # GENERAR RECOMENDACIONES ML POR VEHÍCULO (si hay Yellow Flag)
    ml_recommendations_by_vehicle = {}

    if in_yellow and current_yellow and ml_model is not None:
        yf_start = pd.to_datetime(current_yellow['start'])
        yf_end = pd.to_datetime(current_yellow['end'])

        for vehicle_id in df['vehicle_id'].unique():
            yf_data = df[(df['timestamp'] >= yf_start) & (df['timestamp'] <= yf_end) & (df['vehicle_id'] == vehicle_id)]
            speed_data = yf_data[yf_data['telemetry_name'] == 'speed']['telemetry_value']

            if len(speed_data) > 0:
                prediction_data = {
                    'duration': current_yellow['duration'],
                    'min_speed': speed_data.min(),
                    'avg_speed': speed_data.mean()
                }

                prediction = predict_pit_decision(prediction_data, circuit='indianapolis')

                if prediction:
                    # Calcular métricas adicionales
                    vehicle_data_so_far = df[(df['vehicle_id'] == vehicle_id) & (df.index <= current_index)]
                    brake_data = vehicle_data_so_far[vehicle_data_so_far['telemetry_name'] == 'brake_front']['telemetry_value']
                    acc_data = vehicle_data_so_far[vehicle_data_so_far['telemetry_name'] == 'acc_x']['telemetry_value']

                    time_factor = (elapsed / total_duration) * 100
                    brake_factor = (brake_data.mean() / 100) * 30 if len(brake_data) > 0 else 0
                    acc_factor = (abs(acc_data).mean() / 10) * 20 if len(acc_data) > 0 else 0
                    tire_wear = min(100, time_factor + brake_factor + acc_factor)

                    # Guardar recomendación para este vehículo
                    ml_recommendations_by_vehicle[vehicle_id] = {
                        'decision': prediction['decision'],
                        'confidence': prediction['confidence'],
                        'pit_probability': prediction['pit_probability'],
                        'tire_wear': tire_wear,
                        'duration': current_yellow['duration']
                    }

    # Crear tarjetas profesionales por vehículo
    vehicle_cards = []

    for vehicle_id, position in vehicles_to_monitor:
        vehicle_data = current_data[current_data['vehicle_id'] == vehicle_id]

        if len(vehicle_data) > 0:
            # Crear diccionario pivotado
            telemetry_dict = vehicle_data.set_index('telemetry_name')['telemetry_value'].to_dict()

            # ========== VALORES BÁSICOS ==========
            lap_distance = float(telemetry_dict.get('lap_distance', 0))
            speed = float(telemetry_dict.get('speed', 0))
            gear = int(telemetry_dict.get('gear', 0))
            rpm = float(telemetry_dict.get('rpm', 0))
            brake_front = float(telemetry_dict.get('brake_front', 0))
            brake_rear = float(telemetry_dict.get('brake_rear', 0))
            brake_avg = (brake_front + brake_rear) / 2
            steering = float(telemetry_dict.get('steering', 0))
            acc_x = float(telemetry_dict.get('acc_x', 0))
            acc_y = float(telemetry_dict.get('acc_y', 0))
            throttle = float(telemetry_dict.get('aps', 0))

            # ========== CALCULAR SECTOR ==========
            sector_1_limit = track_length / 3
            sector_2_limit = (track_length * 2) / 3

            if lap_distance < sector_1_limit:
                sector = "S1"
            elif lap_distance < sector_2_limit:
                sector = "S2"
            else:
                sector = "S3"

            # ========== DETECTAR CURVA/RECTA ==========
            if abs(steering) > 20 or abs(acc_x) > 0.4:
                track_section = "CURVE"
            else:
                track_section = "STRAIGHT"

            # ========== TOP SPEED ==========
            vehicle_history = df[(df.index <= current_index) & (df['vehicle_id'] == vehicle_id)]
            speed_history = vehicle_history[vehicle_history['telemetry_name'] == 'speed']['telemetry_value']
            top_speed = speed_history.max() if len(speed_history) > 0 else 0

            # ========== DELTA CON LÍDER ==========
            if leader_id and leader_id != vehicle_id:
                leader_data_current = current_data[current_data['vehicle_id'] == leader_id]
                if len(leader_data_current) > 0:
                    leader_telemetry = leader_data_current.set_index('telemetry_name')['telemetry_value'].to_dict()
                    leader_lap_dist = float(leader_telemetry.get('lap_distance', 0))
                    # Delta aproximado basado en distancia (cada 100m ≈ 3-4 segundos en promedio)
                    distance_diff = leader_lap_dist - lap_distance
                    if distance_diff < 0:  # El vehículo está en vuelta siguiente
                        distance_diff += track_length
                    # Estimación: 1 segundo cada 80 metros a velocidad promedio
                    delta_leader = distance_diff / 80.0
                else:
                    delta_leader = 0
            else:
                delta_leader = 0

            # ========== GAP CON SIGUIENTE ==========
            # Encontrar el vehículo inmediatamente adelante
            next_position = position - 1
            gap_next = 0
            if next_position >= 1:
                next_vehicle_id = None
                for vid, pos in vehicle_positions.items():
                    if pos == next_position:
                        next_vehicle_id = vid
                        break

                if next_vehicle_id:
                    next_vehicle_data = current_data[current_data['vehicle_id'] == next_vehicle_id]
                    if len(next_vehicle_data) > 0:
                        next_telemetry = next_vehicle_data.set_index('telemetry_name')['telemetry_value'].to_dict()
                        next_lap_dist = float(next_telemetry.get('lap_distance', 0))
                        distance_diff = next_lap_dist - lap_distance
                        if distance_diff < 0:
                            distance_diff += track_length
                        gap_next = distance_diff / 80.0

            # ========== TEMPERATURA FRENOS (Estimada) ==========
            # Basado en uso de frenos en los últimos segundos
            recent_brakes = vehicle_history[vehicle_history['telemetry_name'] == 'brake_front']['telemetry_value'].tail(100)
            if len(recent_brakes) > 0:
                brake_usage = recent_brakes.mean()
                # Temperatura base 100°C + incremento por uso (hasta 600°C en frenado intenso)
                temp_frenos = 100 + (brake_usage / 100) * 500
            else:
                temp_frenos = 100

            # ========== TEMPERATURA MOTOR (Estimada) ==========
            # Basado en RPM promedio reciente
            recent_rpm = vehicle_history[vehicle_history['telemetry_name'] == 'rpm']['telemetry_value'].tail(100)
            if len(recent_rpm) > 0:
                avg_rpm = recent_rpm.mean()
                # Temperatura base 80°C + incremento por RPM (hasta 110°C a RPM alto)
                temp_motor = 80 + (avg_rpm / 8000) * 30
            else:
                temp_motor = 80

            # ========== INTENSIDAD DE CONDUCCIÓN ==========
            # Score 0-100 basado en G-forces, frenado, aceleración
            recent_acc_x = vehicle_history[vehicle_history['telemetry_name'] == 'acc_x']['telemetry_value'].tail(50)
            recent_acc_y = vehicle_history[vehicle_history['telemetry_name'] == 'acc_y']['telemetry_value'].tail(50)

            if len(recent_acc_x) > 0 and len(recent_acc_y) > 0:
                avg_acc_x = abs(recent_acc_x).mean()
                avg_acc_y = abs(recent_acc_y).mean()
                avg_brake = recent_brakes.mean() if len(recent_brakes) > 0 else 0

                # Score combinado
                intensidad = min(100, (avg_acc_x * 20) + (avg_acc_y * 20) + (avg_brake / 2))
            else:
                intensidad = 0

            # ========== TRAIL BRAKING ==========
            # Detectar si frena mientras gira
            if brake_avg > 20 and abs(steering) > 15:
                trail_braking = "SÍ"
                trail_braking_color = "#ff9800"  # Naranja
            else:
                trail_braking = "NO"
                trail_braking_color = "#4caf50"  # Verde

            # ========== APEX SPEED ==========
            # Velocidad mínima en la curva actual (si está en curva)
            if track_section == "CURVA":
                # Buscar velocidades recientes en curva
                recent_speeds_in_curve = []
                recent_data = vehicle_history.tail(20)
                for idx_row in recent_data.index:
                    row = recent_data.loc[idx_row]
                    if row['telemetry_name'] == 'steering':
                        if abs(row['telemetry_value']) > 20:  # En curva
                            # Buscar speed correspondiente
                            speed_at_moment = recent_data[(recent_data.index == idx_row) & (recent_data['telemetry_name'] == 'speed')]
                            if len(speed_at_moment) > 0:
                                recent_speeds_in_curve.append(speed_at_moment.iloc[0]['telemetry_value'])

                if len(recent_speeds_in_curve) > 0:
                    apex_speed = min(recent_speeds_in_curve)
                else:
                    apex_speed = speed
            else:
                apex_speed = 0  # No aplicable en recta

            # ========== CREAR TARJETA PROFESIONAL ==========
            vehicle_card = dbc.Card([
                # Header con identificación del vehículo
                dbc.CardHeader([
                    dbc.Row([
                        dbc.Col([
                            html.H3(f"🏎️ {vehicle_id}", className='mb-0',
                                   style={'color': '#00d4ff', 'fontWeight': 'bold'})
                        ], width=6),
                        dbc.Col([
                            html.H2(f"P{position}", className='mb-0 text-end',
                                   style={'color': '#ffd700', 'fontWeight': 'bold'})
                        ], width=6)
                    ])
                ], style={'backgroundColor': '#1a1a2e', 'padding': '12px'}),

                # Body con métricas organizadas
                dbc.CardBody([
                    # ========== SECCIÓN YELLOW FLAG + ML (ARRIBA) ==========
                    # Si hay Yellow Flag activo, mostrar información completa
                    (dbc.Alert([
                        dbc.Row([
                            dbc.Col([
                                html.H5("🚩 YELLOW FLAG", className='mb-1', style={'fontWeight': 'bold'}),
                                html.P(f"Duration: {current_yellow['duration']:.0f}s", className='mb-0', style={'fontSize': '12px'})
                            ], width=4),
                            dbc.Col([
                                html.Small("YF Start: " + pd.to_datetime(current_yellow['start']).strftime('%H:%M:%S'), className='d-block', style={'fontSize': '11px'}),
                                html.Small("YF End: " + pd.to_datetime(current_yellow['end']).strftime('%H:%M:%S'), className='d-block', style={'fontSize': '11px'}),
                            ], width=4),
                            dbc.Col([
                                html.Div([
                                    html.Strong("Time Remaining:", style={'fontSize': '11px'}),
                                    html.H6(f"{max(0, (pd.to_datetime(current_yellow['end']) - current_time).total_seconds()):.0f}s",
                                           className='mb-0', style={'color': '#ff6b6b'})
                                ])
                            ], width=4)
                        ])
                    ], color='warning', className='mb-2', style={'padding': '10px'}) if in_yellow else html.Div()),

                    # ML RECOMMENDATIONS (solo si hay Yellow Flag Y hay recomendación para este vehículo)
                    (dbc.Alert([
                        dbc.Row([
                            dbc.Col([
                                html.H6(f"🎯 {ml_recommendations_by_vehicle[vehicle_id]['decision']}",
                                       className='mb-0',
                                       style={'color': '#ff4444' if ml_recommendations_by_vehicle[vehicle_id]['decision'] == 'PIT' else '#44ff44',
                                              'fontWeight': 'bold'})
                            ], width=3),
                            dbc.Col([
                                html.Small(f"Confidence: {ml_recommendations_by_vehicle[vehicle_id]['confidence']:.0f}%", className='d-block', style={'fontSize': '11px'}),
                                html.Small(f"PIT Prob: {ml_recommendations_by_vehicle[vehicle_id]['pit_probability']:.0f}%", className='d-block', style={'fontSize': '11px'}),
                            ], width=3),
                            dbc.Col([
                                html.Small(f"Tire Wear: {ml_recommendations_by_vehicle[vehicle_id]['tire_wear']:.0f}%", className='d-block', style={'fontSize': '11px'}),
                                dbc.Progress(
                                    value=ml_recommendations_by_vehicle[vehicle_id]['tire_wear'],
                                    color='danger' if ml_recommendations_by_vehicle[vehicle_id]['tire_wear'] > 70 else 'warning',
                                    style={'height': '8px'},
                                    className='mt-1'
                                )
                            ], width=6),
                        ])
                    ], color='info', className='mb-3', style={'padding': '10px'}) if vehicle_id in ml_recommendations_by_vehicle else html.Div()),

                    # SECCIÓN TIEMPO/VUELTA/TRANSCURRIDO (siempre visible)
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Small("TIME", style={'color': '#888', 'fontSize': '10px', 'display': 'block'}),
                                html.H5(current_time.strftime('%H:%M:%S'), style={'color': '#00d4ff', 'fontWeight': 'bold', 'margin': '0'})
                            ], style={'padding': '5px', 'backgroundColor': '#1a2a3a', 'borderRadius': '5px', 'textAlign': 'left'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("LAP", style={'color': '#888', 'fontSize': '10px', 'display': 'block'}),
                                html.H5(f"{current_lap}", style={'color': '#ffd700', 'fontWeight': 'bold', 'margin': '0'})
                            ], style={'padding': '5px', 'backgroundColor': '#2a2a1a', 'borderRadius': '5px', 'textAlign': 'left'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("PLAYBACK", style={'color': '#888', 'fontSize': '10px', 'display': 'block'}),
                                html.H6(f"{elapsed:.1f}s / {total_duration:.1f}s", style={'color': '#95e1d3', 'fontWeight': 'bold', 'margin': '0', 'fontSize': '14px'}),
                                html.Small(f"Record: {current_index:,} / {total_records:,}", style={'color': '#888', 'fontSize': '9px'})
                            ], style={'padding': '5px', 'backgroundColor': '#1a2a2a', 'borderRadius': '5px', 'textAlign': 'left'})
                        ], width=6),
                    ], className='mb-2'),

                    # SECCIÓN 0: UBICACIÓN (compacto)
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Small("SECTOR", style={'color': '#888', 'fontSize': '11px', 'display': 'block', 'textAlign': 'center'}),
                                html.H4(sector, style={'color': '#95e1d3', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'center'})
                            ], style={'padding': '8px', 'backgroundColor': '#2a4a3a', 'borderRadius': '5px'})
                        ], width=6),
                        dbc.Col([
                            html.Div([
                                html.Small("SECTION", style={'color': '#888', 'fontSize': '11px', 'display': 'block', 'textAlign': 'center'}),
                                html.H4(track_section, style={
                                    'color': '#ff9800' if track_section == "CURVE" else '#4caf50',
                                    'fontWeight': 'bold',
                                    'margin': '0',
                                    'textAlign': 'center'
                                })
                            ], style={
                                'padding': '8px',
                                'backgroundColor': '#3a2a1a' if track_section == "CURVE" else '#1a3a2a',
                                'borderRadius': '5px'
                            })
                        ], width=6),
                    ], className='mb-2'),

                    # SECCIÓN 2: VELOCIDAD Y GAPS
                    html.Hr(style={'borderColor': '#444', 'margin': '5px 0'}),
                    html.H6("⚡ SPEED AND POSITION", style={'color': '#00d4ff', 'marginBottom': '5px', 'fontSize': '14px'}),
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Small("Speed", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"{speed:.0f}", style={'color': '#4ecdc4', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                                html.Small("km/h", style={'color': '#666', 'fontSize': '9px', 'textAlign': 'left'})
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("Top Speed", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"{top_speed:.0f}", style={'color': '#51cf66', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                                html.Small("km/h", style={'color': '#666', 'fontSize': '9px', 'textAlign': 'left'})
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("Δ Leader", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"+{delta_leader:.1f}", style={'color': '#ff6b6b', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                                html.Small("sec", style={'color': '#666', 'fontSize': '9px', 'textAlign': 'left'})
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("Gap Next", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"{gap_next:.1f}", style={'color': '#ffa94d', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                                html.Small("sec", style={'color': '#666', 'fontSize': '9px', 'textAlign': 'left'})
                            ], style={'padding': '5px'})
                        ], width=3),
                    ], className='mb-3'),

                    # SECCIÓN 3: MOTOR
                    html.Hr(style={'borderColor': '#444', 'margin': '5px 0'}),
                    html.H6("🔧 ENGINE AND TRANSMISSION", style={'color': '#00d4ff', 'marginBottom': '5px', 'fontSize': '14px'}),
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Small("Gear", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"{gear}", style={'color': '#ffd43b', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("RPM", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"{rpm:.0f}", style={'color': '#ff6b6b', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("Engine Temp", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"{temp_motor:.0f}°", style={'color': '#ff8787', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left', 'visibility': 'hidden'}),
                                html.H3("", style={'margin': '0', 'visibility': 'hidden'}),
                            ], style={'padding': '5px'})
                        ], width=3),
                    ], className='mb-3'),

                    # SECCIÓN 4: FRENOS
                    html.Hr(style={'borderColor': '#444', 'margin': '5px 0'}),
                    html.H6("🛑 BRAKING SYSTEM", style={'color': '#00d4ff', 'marginBottom': '5px', 'fontSize': '14px'}),
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Small("Brake", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"{brake_avg:.0f}%", style={'color': '#ff6b6b', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("Brake Temp", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"{temp_frenos:.0f}°", style={'color': '#fa5252', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("Trail Braking", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(trail_braking, style={'color': trail_braking_color, 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left', 'visibility': 'hidden'}),
                                html.H3("", style={'margin': '0', 'visibility': 'hidden'}),
                            ], style={'padding': '5px'})
                        ], width=3),
                    ], className='mb-3'),

                    # SECCIÓN 5: CONDUCCIÓN
                    html.Hr(style={'borderColor': '#444', 'margin': '5px 0'}),
                    html.H6("🎯 DRIVING ANALYSIS", style={'color': '#00d4ff', 'marginBottom': '5px', 'fontSize': '14px'}),
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Small("Intensity", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"{intensidad:.0f}", style={'color': '#da77f2', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                                html.Small("/100", style={'color': '#666', 'fontSize': '9px', 'textAlign': 'left'})
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("Apex Speed", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left'}),
                                html.H3(f"{apex_speed:.0f}" if apex_speed > 0 else "N/A",
                                       style={'color': '#74c0fc', 'fontWeight': 'bold', 'margin': '0', 'textAlign': 'left'}),
                                html.Small("km/h" if apex_speed > 0 else "", style={'color': '#666', 'fontSize': '9px', 'textAlign': 'left'})
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left', 'visibility': 'hidden'}),
                                html.H3("", style={'margin': '0', 'visibility': 'hidden'}),
                            ], style={'padding': '5px'})
                        ], width=3),
                        dbc.Col([
                            html.Div([
                                html.Small("", style={'color': '#888', 'fontSize': '10px', 'textAlign': 'left', 'visibility': 'hidden'}),
                                html.H3("", style={'margin': '0', 'visibility': 'hidden'}),
                            ], style={'padding': '5px'})
                        ], width=3),
                    ]),
                ], style={'backgroundColor': '#0f1419', 'padding': '12px'}),
            ], className='mb-3', style={'border': '2px solid #00d4ff', 'borderRadius': '10px'})

            vehicle_cards.append(vehicle_card)

    # Layout final con tarjetas
    if len(vehicle_cards) > 0:
        tables_layout = html.Div(vehicle_cards)
    else:
        tables_layout = dbc.Alert([
            html.H5("⏳ Esperando datos de telemetría", className='mb-2'),
            html.P("Cargue un archivo parquet y presione Play para comenzar el monitoreo.", className='mb-0')
        ], color="info")

    # Yellow Flag status (ahora integrado en cada tarjeta de vehículo)
    yellow_status = html.Div()  # Vacío, ya está en las tarjetas

    # ML Predictions - GENERAR UNA RECOMENDACIÓN POR VEHÍCULO
    global last_ml_recommendation

    if in_yellow and current_yellow and ml_model is not None:
        yf_start = pd.to_datetime(current_yellow['start'])
        yf_end = pd.to_datetime(current_yellow['end'])

        ml_recommendations = []

        # Generar recomendación para CADA vehículo
        for vehicle_id in sorted(df['vehicle_id'].unique()):
            # Obtener datos de este vehículo durante Yellow Flag
            yf_data = df[(df['timestamp'] >= yf_start) & (df['timestamp'] <= yf_end) & (df['vehicle_id'] == vehicle_id)]
            speed_data = yf_data[yf_data['telemetry_name'] == 'speed']['telemetry_value']

            if len(speed_data) > 0:
                prediction_data = {
                    'duration': current_yellow['duration'],
                    'min_speed': speed_data.min(),
                    'avg_speed': speed_data.mean()
                }

                prediction = predict_pit_decision(prediction_data, circuit='indianapolis')

                if prediction:
                    # Color según decisión
                    alert_color = 'danger' if prediction['decision'] == 'PIT' else 'info'

                    # Análisis contextual
                    is_long = prediction_data['duration'] > 300
                    is_short = prediction_data['duration'] < 60
                    is_very_slow = prediction_data['avg_speed'] < 10

                    # Determinar motivo principal
                    if is_long:
                        motivo = "Long Yellow Flag (>5 min) - Optimal window"
                    elif is_very_slow:
                        motivo = "Very low speed - High safety probability"
                    elif is_short:
                        motivo = "Short Yellow Flag - Risk of losing time"
                    else:
                        motivo = f"Average speed: {prediction_data['avg_speed']:.1f} km/h"

                    # DESGASTE INDIVIDUAL POR VEHÍCULO basado en su telemetría
                    vehicle_data_so_far = df[(df['vehicle_id'] == vehicle_id) & (df.index <= current_index)]

                    # Calcular desgaste basado en uso de frenos y aceleraciones
                    brake_data = vehicle_data_so_far[vehicle_data_so_far['telemetry_name'] == 'brake_front']['telemetry_value']
                    acc_data = vehicle_data_so_far[vehicle_data_so_far['telemetry_name'] == 'acc_x']['telemetry_value']

                    # Fórmula de desgaste: tiempo + intensidad de frenado + aceleraciones laterales
                    time_factor = (elapsed / total_duration) * 100
                    brake_factor = (brake_data.mean() / 100) * 30 if len(brake_data) > 0 else 0
                    acc_factor = (abs(acc_data).mean() / 10) * 20 if len(acc_data) > 0 else 0

                    tire_wear = min(100, time_factor + brake_factor + acc_factor)

                    # DISTANCIA A PITS usando lap_distance
                    # Indianapolis: Pits en posición ~0 (inicio/fin de vuelta)
                    # Longitud total vuelta: ~4000m
                    lap_dist_data = vehicle_data_so_far[vehicle_data_so_far['telemetry_name'] == 'lap_distance']

                    if len(lap_dist_data) > 0:
                        current_lap_position = float(lap_dist_data.iloc[-1]['telemetry_value'])
                        # Distancia a pits (asumiendo pits en posición 0 o ~4000)
                        # Si estás cerca del inicio (< 2000m), distancia directa
                        # Si estás lejos (> 2000m), distancia a completar la vuelta
                        if current_lap_position < 2000:
                            distance_to_pits_m = current_lap_position
                        else:
                            distance_to_pits_m = 4000 - current_lap_position
                        distance_to_pits_km = distance_to_pits_m / 1000
                    else:
                        distance_to_pits_km = None

                    # Ventana de tiempo
                    time_in_yellow = (current_time - pd.to_datetime(current_yellow['start'])).total_seconds()
                    time_remaining = current_yellow['duration'] - time_in_yellow

                    # Crear recomendación para este vehículo
                    vehicle_recommendation = dbc.Card([
                        dbc.CardHeader([
                            html.Strong(f"🏎️ Vehicle: {vehicle_id}", style={'fontSize': '12px', 'color': '#00d4ff'})
                        ], style={'padding': '4px 8px', 'backgroundColor': '#1a3a4a'}),
                        dbc.CardBody([
                            html.Div([
                                html.H6(f"🎯 {prediction['decision']}", className='mb-1',
                                       style={'color': '#ff4444' if prediction['decision'] == 'PIT' else '#44ff44'}),

                                # Métricas principales
                                html.Small([
                                    f"Confidence: {prediction['confidence']:.1f}% | ",
                                    f"Prob PIT: {prediction['pit_probability']:.1f}%"
                                ], className='mb-1 d-block'),

                                dbc.Progress(
                                    value=prediction['pit_probability'],
                                    color='danger' if prediction['pit_probability'] > 50 else 'success',
                                    className='mb-2',
                                    style={'height': '6px'}
                                ),

                                # Motivo
                                html.Div([
                                    html.Strong("📋 ", style={'fontSize': '10px'}),
                                    html.Small(motivo, className='text-muted', style={'fontSize': '10px'})
                                ], className='mb-1'),

                                # Distancia a pits
                                html.Div([
                                    html.Strong("📍 Distance to Pits: ", style={'fontSize': '10px'}),
                                    html.Small(
                                        f"{distance_to_pits_km:.2f} km" if distance_to_pits_km is not None else "N/A",
                                        className='text-info',
                                        style={'fontSize': '10px', 'fontWeight': 'bold'}
                                    )
                                ], className='mb-1'),

                                # Desgaste llantas individual
                                html.Div([
                                    html.Strong("🔧 Wear: ", style={'fontSize': '10px'}),
                                    dbc.Progress(
                                        value=tire_wear,
                                        label=f"{tire_wear:.0f}%",
                                        color='danger' if tire_wear > 70 else 'warning' if tire_wear > 40 else 'success',
                                        style={'height': '12px', 'fontSize': '9px'}
                                    )
                                ], className='mb-1'),

                                # Yellow Flag timing
                                html.Small([
                                    f"⏱️ Remaining: {max(0, time_remaining):.0f}s"
                                ], className='text-muted', style={'fontSize': '9px'})
                            ])
                        ], style={'padding': '6px'})
                    ], className='mb-2', style={'border': '1px solid #333'})

                    ml_recommendations.append(vehicle_recommendation)

        if ml_recommendations:
            ml_content = html.Div(ml_recommendations)
            # GUARDAR la última recomendación para mostrarla después del Yellow Flag
            last_ml_recommendation = ml_content
        else:
            ml_content = html.Small("Esperando datos...", className='text-muted')
    else:
        # Cuando NO hay Yellow Flag activo
        if ml_model is None:
            ml_content = dbc.Alert([
                html.Small("Modelos ML no disponibles", className='mb-0')
            ], color='secondary', className='mb-0')
        elif last_ml_recommendation is not None:
            # MOSTRAR la última recomendación hasta que haya un nuevo Yellow Flag
            ml_content = last_ml_recommendation
        else:
            ml_content = dbc.Alert([
                html.Small("Esperando Yellow Flag...", className='mb-0')
            ], color='secondary', className='mb-0')

    # RESUMEN DE YELLOW FLAGS (al finalizar la simulación)
    yf_summary = ""
    if current_index >= total_records - 1:  # Simulación terminada
        yellow_flags = race_data_json['yellow_flags']

        if len(yellow_flags) > 0:
            # Calcular estadísticas
            total_yf_time = sum(yf['duration'] for yf in yellow_flags)
            avg_yf_duration = total_yf_time / len(yellow_flags)
            max_yf = max(yellow_flags, key=lambda x: x['duration'])
            min_yf = min(yellow_flags, key=lambda x: x['duration'])

            # Crear tabla de resumen
            yf_table_data = []
            for i, yf in enumerate(yellow_flags, 1):
                yf_table_data.append({
                    '#': i,
                    'Inicio': pd.to_datetime(yf['start']).strftime('%H:%M:%S'),
                    'Fin': pd.to_datetime(yf['end']).strftime('%H:%M:%S'),
                    'Duración (s)': f"{yf['duration']:.0f}",
                    'Duración (min)': f"{yf['duration']/60:.1f}"
                })

            yf_summary = dbc.Card([
                dbc.CardHeader([
                    html.H5("🏁 RESUMEN DE SIMULACIÓN - YELLOW FLAGS", className='mb-0 text-center')
                ], style={'backgroundColor': '#ffc107', 'color': '#000'}),
                dbc.CardBody([
                    # Estadísticas generales
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H3(f"{len(yellow_flags)}", className='text-center mb-0', style={'color': '#ffc107'}),
                                    html.P("Total Yellow Flags", className='text-center text-muted mb-0', style={'fontSize': '11px'})
                                ])
                            ], className='mb-2')
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H3(f"{total_yf_time/60:.1f} min", className='text-center mb-0', style={'color': '#ff6b6b'}),
                                    html.P("Total YF Time", className='text-center text-muted mb-0', style={'fontSize': '11px'})
                                ])
                            ], className='mb-2')
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H3(f"{avg_yf_duration:.0f}s", className='text-center mb-0', style={'color': '#4ecdc4'}),
                                    html.P("Duración Promedio", className='text-center text-muted mb-0', style={'fontSize': '11px'})
                                ])
                            ], className='mb-2')
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H3(f"{(total_yf_time/total_duration)*100:.1f}%", className='text-center mb-0', style={'color': '#95e1d3'}),
                                    html.P("% de Carrera", className='text-center text-muted mb-0', style={'fontSize': '11px'})
                                ])
                            ], className='mb-2')
                        ], width=3),
                    ], className='mb-3'),

                    # Tabla detallada de Yellow Flags
                    html.H6("Detalle de Yellow Flags:", className='mb-2'),
                    dash_table.DataTable(
                        data=yf_table_data,
                        columns=[
                            {'name': '#', 'id': '#'},
                            {'name': 'Inicio', 'id': 'Inicio'},
                            {'name': 'Fin', 'id': 'Fin'},
                            {'name': 'Duración (s)', 'id': 'Duración (s)'},
                            {'name': 'Duración (min)', 'id': 'Duración (min)'},
                        ],
                        style_cell={
                            'textAlign': 'center',
                            'backgroundColor': '#2a2a2a',
                            'color': 'white',
                            'fontSize': '11px',
                            'padding': '8px',
                        },
                        style_header={
                            'backgroundColor': '#ffc107',
                            'color': '#000',
                            'fontWeight': 'bold',
                            'fontSize': '12px',
                        },
                        style_data_conditional=[
                            {
                                'if': {'column_id': '#'},
                                'fontWeight': 'bold',
                                'backgroundColor': '#333'
                            }
                        ]
                    ),

                    # Extremos
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.Strong("🔴 Longest Yellow Flag: ", style={'fontSize': '11px'}),
                            html.Br(),
                            html.Small(f"{max_yf['duration']/60:.1f} min ({pd.to_datetime(max_yf['start']).strftime('%H:%M:%S')})",
                                      className='text-danger')
                        ], width=6),
                        dbc.Col([
                            html.Strong("🟢 Shortest Yellow Flag: ", style={'fontSize': '11px'}),
                            html.Br(),
                            html.Small(f"{min_yf['duration']:.0f}s ({pd.to_datetime(min_yf['start']).strftime('%H:%M:%S')})",
                                      className='text-success')
                        ], width=6),
                    ])
                ])
            ], className='mb-3', style={'border': '2px solid #ffc107'})

    return tables_layout, playback_info, progress, yellow_status, ml_content, yf_summary


# ============================================================================
# EJECUTAR APP
# ============================================================================

# Expose server for Gunicorn (production)
server = app.server

if __name__ == '__main__':
    print("\n" + "="*70)
    print("Toyota GR Racing Simulator - LIGHTWEIGHT (YF + ML INTEGRADO)")
    print("="*70)
    print(f"\nArchivos temporales: {TEMP_DIR}")
    print("Abriendo en: http://127.0.0.1:8052")
    print("\nPresiona Ctrl+C para detener")
    print("="*70 + "\n")

    # Development server - supports PORT environment variable for deployment
    import os
    port = int(os.environ.get('PORT', 8052))
    app.run(debug=False, host='0.0.0.0', port=port)
