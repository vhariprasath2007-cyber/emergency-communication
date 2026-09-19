# Emergency Assistant Backend

Flask API for the SOS flow: validate the report, generate a structured emergency message, attach location data, and save the record to Firestore.

## Run locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

With the default `DEMO_MODE=true`, records are held in memory and the API works without credentials. Set `DEMO_MODE=false` only after configuring Firebase.

## Firebase and Gemini

- Set `GEMINI_API_KEY` to enable Gemini message generation. Without it, a safe deterministic fallback is used.
- Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of a Firebase service-account JSON file, or set `FIREBASE_PROJECT_ID` when using Application Default Credentials.
- Never commit the service-account JSON or API keys. Firestore records are written to the `emergencies` collection.

## API

- `GET /api/health`
- `POST /api/emergency`
- `POST /api/chat`
- `GET /api/emergency/<id>`
- `PUT /api/emergency/<id>/status`

Example request:

```json
{
  "emergency_type": "accident",
  "description": "My friend met with an accident. We need help.",
  "user_name": "Asha",
  "location": {
    "latitude": 12.92,
    "longitude": 80.12,
    "label": "Tambaram, Chennai"
  }
}
```