# Wi-Fi Sonar

A privacy-first Python/Flask prototype that displays an indoor floor plan, estimates a target position from four receivers, and highlights Wi-Fi motion disturbances. It starts in simulation mode, so the dashboard works immediately.

## Run

```bash
python -m venv .venv
source .venv/bin/activate             # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:8000`.

## Connect real sensors

Place four fixed receivers at the coordinates in `app.py`. Each receiver sends readings to the computer running the dashboard:

```bash
curl -X POST http://DASHBOARD_IP:8000/api/readings \
  -H 'Content-Type: application/json' \
  -d '{"anchor_id":"north-west","rssi":-61.2,"distance":2.8,"motion":0.42}'
```

Send at least three different anchor IDs every 1–2 seconds. The dashboard switches from `SIMULATION` to `SENSORS`; readings expire after five seconds.

### Hardware path

1. **Basic ranging:** four Raspberry Pis or ESP32 devices reporting RSSI. Cheap, but multipath reflections can cause errors of several metres.
2. **Recommended movement sensing:** ESP32-S3 CSI-capable receivers using Espressif's CSI examples. Convert CSI amplitude variance over a sliding baseline into a normalized `motion` score.
3. **Higher accuracy:** UWB anchors for position plus Wi-Fi CSI for presence. Wi-Fi alone is not reliable enough for safety, security, or medical decisions.

## Calibration

Measure the room and update `ROOM` and `ANCHORS`. At known 1 m and 3 m points, record RSSI, then tune `tx_power` and `path_loss` in `distance_from_rssi`. Concrete, metal, people, antenna direction, and neighboring networks all affect readings.

## Privacy and safety

Use only in spaces you own or where everyone has explicitly consented. The API has no authentication and is intended for a trusted local network. Do not expose port 8000 to the internet without adding authentication and TLS.

## Test

```bash
python -m unittest discover -s tests
```
