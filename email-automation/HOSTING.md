# Free hosting for the web app

The app is one Flask server that serves the frontend and the API. Deploy the **email-automation** folder (with `app.py`, `frontend/`, `templates.json`, `signature.html`, `requirements.txt`, `Procfile`).

---

## Option 1: Render (recommended)

1. **Push your code to GitHub** (create a repo and push the `email-automation` folder, or the whole project with `email-automation` at the repo root).

2. Go to [render.com](https://render.com) and sign up (free).

3. **New → Web Service**. Connect your GitHub repo.

4. **Settings:**
   - **Root Directory:** If the app is in a subfolder (e.g. `email-automation`), set **Root Directory** to that folder.
   - **Build Command:** `pip install -r requirements.txt` (or leave blank if Render auto-detects).
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`

5. Click **Create Web Service**. Render will build and deploy. Your app URL will be like `https://your-app-name.onrender.com`.

**Note:** On the free tier, the service may spin down after inactivity; the first request after that can take 30–60 seconds.

---

## Option 2: Railway

1. Go to [railway.app](https://railway.app) and sign up.

2. **New Project → Deploy from GitHub repo**. Select your repo and the branch.

3. Set the **Root Directory** to `email-automation` if the app lives in that folder.

4. Railway usually detects Python and runs `pip install` + your start command. If not, set **Start Command** to:
   ```bash
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```
   (Railway sets `PORT` automatically.)

5. Deploy. Use the generated URL (e.g. `https://your-app.up.railway.app`).

Free tier has a monthly usage limit.

---

## Option 3: Fly.io

1. Install [flyctl](https://fly.io/docs/hands-on/install-flyctl/) and sign up.

2. From the **email-automation** folder:
   ```bash
   fly launch
   ```
   Answer the prompts (app name, region). Do not add a database.

3. Create a `Dockerfile` in `email-automation` if Fly doesn’t auto-detect:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   ENV PORT=8080
   CMD gunicorn app:app --bind 0.0.0.0:$PORT
   ```

4. Run:
   ```bash
   fly deploy
   ```
   Your app will be at `https://your-app-name.fly.dev`.

Free tier has a monthly allowance.

---

## Option 4: Run locally

No hosting; run on your machine:

```bash
cd email-automation
pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000](http://localhost:5000). Use this for testing; Gmail and App Password are only sent to your local server.

---

## After deployment

- Open the deployed URL in your browser.
- Enter your Gmail and App Password (from Google App passwords), upload a CSV, choose a template, and click Send.
- Credentials are sent only in the request and are not stored on the server.
