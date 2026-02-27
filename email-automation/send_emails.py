#!/usr/bin/env python3
"""
Send emails from Gmail using a CSV of recipients and a template from templates.json.
Usage: python send_emails.py --csv recipients.csv --template welcome
"""
import argparse
import csv
import html
import json
import os
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")
TEMPLATES_PATH = SCRIPT_DIR / "templates.json"
SIGNATURE_PATH = SCRIPT_DIR / "signature.html"

# Plain-text version of the signature (appended to plain body)
SIGNATURE_PLAIN = """

Purrvi
Customers and Community
+1 646-240-5987
purrvi@dodopayments.com
www.dodopayments.com
"""


def load_templates():
    with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_signature():
    with open(SIGNATURE_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_template(templates, template_id):
    for t in templates:
        if t.get("id") == template_id:
            return t
    raise ValueError(f"Template '{template_id}' not found in templates.json. Available: {[t['id'] for t in templates]}")


def render(text, name):
    return text.replace("{{name}}", name)


def body_to_html(plain_body):
    """Convert plain text body to HTML and escape special chars."""
    escaped = html.escape(plain_body)
    return f'<div dir="ltr">{escaped.replace(chr(10), "<br>")}</div>'


def send_email(smtp_user, smtp_password, to_email, subject, body_plain, signature_html, body_html=None):
    plain_with_sig = body_plain + SIGNATURE_PLAIN
    if body_html is not None:
        html_body = f'<div dir="ltr">{body_html}</div>' + signature_html
    else:
        html_body = body_to_html(body_plain) + signature_html
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(plain_with_sig, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())


def main():
    parser = argparse.ArgumentParser(description="Send templated emails from Gmail using a CSV of recipients.")
    parser.add_argument("--csv", required=True, help="Path to CSV file with 'name' and 'email' columns")
    parser.add_argument("--template", required=True, help="Template id from templates.json (e.g. welcome, reminder)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be sent without sending")
    args = parser.parse_args()

    smtp_user = os.environ.get("GMAIL_USER")
    smtp_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not args.dry_run and (not smtp_user or not smtp_password):
        print("Set GMAIL_USER and GMAIL_APP_PASSWORD in the .env file (or use --dry-run).")
        return 1

    templates = load_templates()
    template = get_template(templates, args.template)
    signature_html = load_signature()
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = SCRIPT_DIR / csv_path
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 1

    sent = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "name" not in reader.fieldnames or "email" not in reader.fieldnames:
            print("CSV must have 'name' and 'email' columns.")
            return 1
        for row in reader:
            name = (row.get("name") or "").strip()
            email = (row.get("email") or "").strip()
            if not email:
                continue
            subject = render(template["subject"], name)
            body_plain = render(template["body"], name)
            body_html = render(template["bodyHtml"], name) if template.get("bodyHtml") else None
            if args.dry_run:
                print(f"[DRY RUN] To: {email} | Subject: {subject}")
                sent += 1
                continue
            try:
                send_email(smtp_user, smtp_password, email, subject, body_plain, signature_html, body_html)
                print(f"Sent to {email}")
                sent += 1
            except Exception as e:
                print(f"Failed {email}: {e}")

    print(f"Done. Sent: {sent}")
    return 0


if __name__ == "__main__":
    exit(main())
