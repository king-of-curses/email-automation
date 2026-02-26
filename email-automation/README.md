# Email automation (Gmail)

Send templated emails from your Gmail using a CSV of recipients.

## Web app (browser)

Run the Flask app to use the UI: enter Gmail + App Password, upload CSV, pick a template, and send.

```bash
cd email-automation
pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000](http://localhost:5000). To host for free online, see [HOSTING.md](HOSTING.md).

## Gmail setup

1. **Enable 2-Step Verification**  
   Google Account → Security → 2-Step Verification → turn on.

2. **Create an App Password**  
   Security → 2-Step Verification → App passwords → create one (e.g. "Email script").  
   Use this 16-character password in the script, **not** your normal Gmail password.

3. **Credentials in `.env`** (don’t commit this file):
   - Copy `.env.example` to `.env`
   - Edit `.env` and set your Gmail address and App Password:
   ```
   GMAIL_USER=your@gmail.com
   GMAIL_APP_PASSWORD=your-16-char-app-password
   ```

## Usage

- **Templates:** Edit `templates.json`. Use `{{name}}` in `subject` and `body`; it’s replaced with the recipient’s name from the CSV.
- **Signature:** Every email includes the HTML signature from `signature.html` by default. Edit that file to change the footer.
- **CSV:** Must have columns `name` and `email`. Example: `sample_recipients.csv`.

Run:

```bash
# From the email-automation folder
python send_emails.py --csv sample_recipients.csv --template welcome
```

- `--csv` – path to your CSV (relative to this folder or absolute).
- `--template` – template `id` from `templates.json` (e.g. `welcome`, `reminder`).
- `--dry-run` – print what would be sent without sending.

Example dry run:

```bash
python send_emails.py --csv sample_recipients.csv --template welcome --dry-run
```
