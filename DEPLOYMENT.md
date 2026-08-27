# ☁️ Deployment Guide — EcoVision AI

## 1. Push to GitHub

```bash
cd ecovision-ai
git init
git add .
git commit -m "Initial commit — EcoVision AI Smart Waste Management Platform"
git branch -M main
git remote add origin https://github.com/<your-username>/ecovision-ai.git
git push -u origin main
```

> ⚠️ Double-check `.env` is **not** committed — it's already in `.gitignore`.
> Only `.env.example` (with placeholder values) should be in the repo.

## 2. Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **"New app"** → select your `ecovision-ai` repository → branch `main`.
3. Set **Main file path** to `app.py`.
4. Click **"Advanced settings"** → **Secrets** and paste your environment
   variables in TOML format (Streamlit Cloud injects these as `st.secrets`,
   which `python-dotenv` + `os.getenv` will also pick up if you mirror them
   into environment variables — see note below):

```toml
OPENROUTER_API_KEY = "sk-or-your-real-key"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "meta-llama/llama-3.2-11b-vision-instruct:free"
OPENROUTER_TEXT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"
APP_SECRET_KEY = "generate-a-long-random-string"
MUNICIPALITY_NAME = "Municipal Corporation of Gurugram (MCG)"
SUPPORT_EMAIL = "support@yourdomain.in"
SUPPORT_PHONE = "+91-XXXXXXXXXX"
```

5. Click **Deploy**. First boot will install `requirements.txt` and
   auto-create the SQLite database.

### Note on secrets vs `.env` on Streamlit Cloud

Streamlit Cloud secrets aren't automatically written to `os.environ` in older
Streamlit versions. If `config/settings.py` doesn't pick up your secrets,
add this snippet near the top of `app.py` (before `from config import settings`):

```python
import os, streamlit as st
for k, v in st.secrets.items():
    os.environ.setdefault(k, str(v))
```

## 3. Persistent Storage Note

Streamlit Community Cloud's filesystem is **ephemeral** — the SQLite file
and uploaded images reset on redeploys/restarts. For a real production
municipal deployment, swap `database/db.py` to point at a managed database
(e.g. PostgreSQL) and store uploaded images in object storage (e.g. AWS S3 /
IBM Cloud Object Storage) instead of the local `assets/uploads/` folder.

## 4. Custom Domain / IBM Cloud (optional)

To run this on IBM Cloud instead of Streamlit Cloud:
1. Containerize with a `Dockerfile` (`FROM python:3.11-slim`, copy repo,
   `pip install -r requirements.txt`, `CMD ["streamlit","run","app.py","--server.port=8080","--server.address=0.0.0.0"]`).
2. Push the image to IBM Cloud Container Registry.
3. Deploy via IBM Cloud Code Engine or Kubernetes Service, injecting the same
   environment variables as secrets/config maps.

## 5. Post-Deployment Checklist

- [ ] Create your admin account via `python scripts/create_admin.py` (no default admin account exists — see `supabase/README.md`).
- [ ] Confirm `OPENROUTER_API_KEY` is set and AI features respond live (not demo mode).
- [ ] Test registration, login, and password reset end-to-end.
- [ ] Verify file upload size limits match `.streamlit/config.toml` (`maxUploadSize`).
- [ ] Set up a real database + object storage before going into production with real citizen data.
