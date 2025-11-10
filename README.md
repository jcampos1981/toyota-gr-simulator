# Toyota GR Racing Simulator

Interactive race replay simulator with real-time telemetry visualization and ML-powered pit stop predictions.

## Features

- **File Upload**: Load race telemetry data (CSV or Parquet format)
- **Race Replay**: Configurable playback speed (0.5x to 10x)
- **Live GPS Tracking**: Real-time position visualization on race track map
- **Telemetry Charts**: Speed, throttle, and other metrics in real-time
- **Yellow Flag Detection**: Automatic detection of caution periods
- **ML Predictions**: AI-powered pit stop recommendations during Yellow Flags
- **Playback Controls**: Play, pause, reset, and speed adjustment

## Installation

1. Install dependencies:

```bash
cd simulator
pip install -r requirements.txt
```

## Usage

### Running the Simulator

```bash
python app.py
```

The application will start at `http://127.0.0.1:8050`

### Loading Race Data

1. Click or drag-and-drop a telemetry file (CSV or Parquet)
2. Wait for the data to load and Yellow Flags to be detected
3. Use playback controls to start the race replay

### Playback Controls

- **▶️ Play**: Start race replay
- **⏸️ Pause**: Pause at current position
- **⏮️ Reset**: Return to start
- **Speed Slider**: Adjust playback speed (0.5x - 10x)

### Required Telemetry Data Format

The telemetry file must contain the following columns:

- `timestamp`: Datetime of the measurement
- `vehicle_id`: Unique identifier for each vehicle
- `telemetry_name`: Type of measurement (speed, throttle, latitude, longitude, etc.)
- `telemetry_value`: Numeric value of the measurement

Example:

```csv
timestamp,vehicle_id,telemetry_name,telemetry_value
2024-09-14 14:30:00,1,speed,120.5
2024-09-14 14:30:00,1,latitude,33.4567
2024-09-14 14:30:00,1,longitude,-86.1234
```

## ML Predictions

During Yellow Flag periods, the simulator will:

1. **Detect the caution**: Identifies when average field speed drops below 50 km/h
2. **Analyze conditions**: Calculates duration, minimum speed, average speed
3. **Make prediction**: Uses trained ML model to recommend PIT or NO PIT
4. **Show confidence**: Displays prediction confidence and pit probability

The ML model was trained on historical Toyota GR Cup race data and achieves 96.6% accuracy.

## Architecture

- **Frontend**: Dash + Plotly (interactive web interface)
- **Backend**: Python + Pandas (data processing)
- **ML Engine**: Scikit-learn Gradient Boosting model
- **Visualization**: Plotly graphs + OpenStreetMap

## Performance Tips

For large telemetry files (>1M records):

- Use Parquet format instead of CSV (faster loading)
- Increase playback speed to skip through race quickly
- The simulator downsamples display data automatically for smooth performance

## Integration with ML Models

The simulator automatically loads trained models from `../models/`:

- `gradient_boosting_pit_decision.pkl` - Main ML model
- `label_encoders.pkl` - Feature encoders
- `feature_config.json` - Model configuration

Ensure you've run the ML training scripts first:

```bash
python scripts/08_train_ml_models.py
```

## Troubleshooting

### "No module named 'dash'"

Install dependencies:

```bash
pip install -r requirements.txt
```

### "Invalid file format" error

Ensure your telemetry file has the required columns: `timestamp`, `vehicle_id`, `telemetry_name`, `telemetry_value`

### Map not showing

The simulator uses OpenStreetMap. Ensure you have an internet connection for map tiles to load.

### ML predictions not showing

Verify that the ML models exist in `../models/` directory. Run training scripts if needed.

## Development

Built for Toyota Gazoo Racing's "Hack the Track 2024" competition.

**Stack:**
- Dash 2.14.2
- Plotly 5.18.0
- Pandas 2.1.3
- Scikit-learn 1.3.2

## License

Developed for Toyota GR Racing Analytics - Hack the Track 2024
