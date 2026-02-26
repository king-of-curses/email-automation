"""
Flask backend: serves frontend and provides /api/templates, /api/send.
Credentials (Gmail + App Password) are sent in the request body and never stored.
"""
import html
import json
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, jsonify, send_from_directory

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_PATH = APP_DIR / "templates.json"
SIGNATURES_PATH = APP_DIR / "signatures.json"
SIGNATURE_PATH = APP_DIR / "signature.html"

SIGNATURE_PLAIN = """

Purrvi
Customers and Community
+1 646-240-5987
purrvi@dodopayments.com
www.dodopayments.com
"""

app = Flask(__name__, static_folder="frontend", static_url_path="")


def load_templates():
    with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_templates(templates):
    with open(TEMPLATES_PATH, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2)


def load_signatures():
    with open(SIGNATURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_signatures(signatures):
    with open(SIGNATURES_PATH, "w", encoding="utf-8") as f:
        json.dump(signatures, f, indent=2)


def get_signature(signatures, signature_id):
    for s in signatures:
        if s.get("id") == signature_id:
            return s
    return None


def build_signature_html(sig):
    """Full signature.html layout with only name, title, email replaced from sig."""
    raw = load_signature()
    n = html.escape((sig.get("name") or "").strip())
    t = html.escape((sig.get("title") or "").strip())
    e = html.escape((sig.get("email") or "").strip())
    raw = raw.replace(">Purrvi<", ">" + n + "<")
    raw = raw.replace(">Customers and Community<", ">" + t + "<")
    raw = raw.replace("purrvi@dodopayments.com", e)
    return raw


def build_signature_plain(sig):
    """Same structure as SIGNATURE_PLAIN; only name, title, email from sig."""
    n = (sig.get("name") or "").strip()
    t = (sig.get("title") or "").strip()
    e = (sig.get("email") or "").strip()
    return "\n\n" + n + "\n" + t + "\n+1 646-240-5987\n" + e + "\nwww.dodopayments.com\n"


def load_signature():
    with open(SIGNATURE_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_template(templates, template_id):
    for t in templates:
        if t.get("id") == template_id:
            return t
    return None


def render(text, name):
    return (text or "").replace("{{name}}", name)


def body_to_html(plain_body):
    escaped = html.escape(plain_body)
    return f'<div dir="ltr">{escaped.replace(chr(10), "<br>")}</div>'


def send_one(smtp_user, smtp_password, to_email, subject, body_plain, signature_html, body_html=None, signature_plain=None):
    plain_sig = signature_plain if signature_plain is not None else SIGNATURE_PLAIN
    plain_with_sig = body_plain + plain_sig
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


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/templates", methods=["GET"])
def api_templates_get():
    try:
        templates = load_templates()
        return jsonify(templates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/signatures", methods=["GET"])
def api_signatures_get():
    try:
        signatures = load_signatures()
        return jsonify(signatures)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/signatures", methods=["POST"])
def api_signatures_post():
    try:
        data = request.get_json() or {}
        sid = (data.get("signature_name") or data.get("id") or "").strip()
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        title = (data.get("title") or "").strip()
        if not sid:
            return jsonify({"error": "signature_name is required"}), 400
        signatures = load_signatures()
        for s in signatures:
            if s.get("id") == sid:
                s["name"] = name
                s["email"] = email
                s["title"] = title
                save_signatures(signatures)
                return jsonify({"ok": True, "signatures": signatures})
        signatures.append({"id": sid, "name": name, "email": email, "title": title})
        save_signatures(signatures)
        return jsonify({"ok": True, "signatures": signatures})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/templates", methods=["POST"])
def api_templates_post():
    try:
        data = request.get_json() or {}
        tid = (data.get("id") or "").strip()
        subject = data.get("subject") or ""
        body = data.get("body") or ""
        body_html = data.get("bodyHtml")
        if not tid:
            return jsonify({"error": "Template id is required"}), 400
        templates = load_templates()
        for t in templates:
            if t.get("id") == tid:
                t["subject"] = subject
                t["body"] = body
                if body_html is not None:
                    t["bodyHtml"] = body_html
                save_templates(templates)
                return jsonify({"ok": True, "templates": templates})
        templates.append({"id": tid, "subject": subject, "body": body, "bodyHtml": body_html})
        save_templates(templates)
        return jsonify({"ok": True, "templates": templates})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/send", methods=["POST"])
def api_send():
    try:
        data = request.get_json() or {}
        gmail = (data.get("gmail") or "").strip()
        password = (data.get("password") or "").strip()
        template_id = (data.get("templateId") or "").strip()
        signature_id = (data.get("signatureId") or "").strip() or None
        recipients = data.get("recipients") or []
        if not gmail or not password:
            return jsonify({"error": "Gmail and password are required"}), 400
        if not template_id:
            return jsonify({"error": "templateId is required"}), 400
        if not recipients:
            return jsonify({"error": "recipients list is required"}), 400

        templates = load_templates()
        template = get_template(templates, template_id)
        if not template:
            return jsonify({"error": f"Template '{template_id}' not found"}), 400

        if signature_id:
            signatures = load_signatures()
            sig = get_signature(signatures, signature_id)
            if not sig:
                return jsonify({"error": f"Signature '{signature_id}' not found"}), 400
            signature_html = build_signature_html(sig)
            signature_plain = build_signature_plain(sig)
        else:
            signature_html = load_signature()
            signature_plain = None
        sent = 0
        failed = []

        for r in recipients:
            name = (r.get("name") or "").strip()
            email = (r.get("email") or "").strip()
            if not email:
                continue
            subject = render(template["subject"], name)
            body_plain = render(template["body"], name)
            body_html = render(template["bodyHtml"], name) if template.get("bodyHtml") else None
            try:
                send_one(gmail, password, email, subject, body_plain, signature_html, body_html, signature_plain)
                sent += 1
            except Exception as e:
                failed.append({"email": email, "error": str(e)})

        return jsonify({"ok": True, "sent": sent, "failed": failed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
