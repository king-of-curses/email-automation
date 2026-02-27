"""
Flask backend: serves frontend and provides /api/templates, /api/send, /api/generate.
Credentials (Gmail + App Password) are sent in the request body and never stored.
"""
import html
import json
import os
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, jsonify, send_from_directory

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

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


DEFAULT_DODO_PROMPT = """You are an account manager at Dodo Payments (a payments and billing platform for SaaS, AI, and digital products). Write a personalized cold email to {{name}} at {{company_name}}.

Follow this structure exactly:

1. Start with: "Hi {{name}},\\n\\nHope you're doing well!"

2. Second paragraph: "I'm {{sender_name}}, your dedicated Account Manager at Dodo Payments. I took a quick look at {{company_name}}'s [pricing page / product / website] and really liked [mention 2–3 specific features, plans, or differentiators you know about them—use your knowledge of {{company_name}}]. Be specific and accurate; do not invent features if unsure."

3. Third paragraph: Explain how a modern billing infrastructure could help {{company_name}}—e.g. streamline their subscription model, scale bookings, improve revenue management. Tailor this to their business (SaaS, beauty, wellness, etc.).

4. Fourth paragraph: "With Dodo, you get an end-to-end billing stack—subscriptions management, smart retries & failed payment recovery, and global payment methods with built-in tax compliance as a Merchant of Record, so your team can focus purely on [their core business] instead of payment operations."

5. Fifth paragraph: "If you need any help, feature requests, or priority support around subscriptions management, global expansion, or checkout optimization, feel free to reach out anytime."

6. Close with: "Looking forward to building a great partnership."

Use {{sender_name}}, {{name}}, and {{company_name}} as provided. Keep a friendly, professional tone. Do not use bullet points. Write only the email body—no subject line."""


def _generate_body_with_claude(api_key, prompt_template, name, email, company_name, sender_name=""):
    """Call Claude to generate email body. Uses model knowledge about company."""
    if not Anthropic:
        raise RuntimeError("anthropic package not installed")
    template = (prompt_template or "").strip() or DEFAULT_DODO_PROMPT
    prompt = (
        template
        .replace("{{name}}", name or "")
        .replace("{{company_name}}", company_name or "")
        .replace("{{email}}", email or "")
        .replace("{{sender_name}}", sender_name or "")
    )
    client = Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return (msg.content[0].text or "").strip()


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """Generate email bodies using Claude. Uses {{name}}, {{company_name}}, {{email}} in prompt."""
    try:
        if not Anthropic:
            return jsonify({"error": "anthropic package not installed"}), 500
        data = request.get_json() or {}
        recipients = data.get("recipients") or []
        prompt_template = (data.get("promptTemplate") or data.get("prompt_template") or "").strip()
        default_company = (data.get("defaultCompany") or data.get("default_company") or "").strip()
        sender_name = (data.get("senderName") or data.get("sender_name") or "").strip()
        api_key = (data.get("apiKey") or data.get("api_key") or "").strip() or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return jsonify({"error": "Claude API key required (apiKey in body or ANTHROPIC_API_KEY in env)"}), 400
        if not recipients:
            return jsonify({"error": "recipients list is required"}), 400

        bodies = []
        for r in recipients:
            name = (r.get("name") or "").strip()
            email = (r.get("email") or "").strip()
            company_name = (r.get("company_name") or r.get("company") or "").strip() or default_company
            if not email:
                continue
            try:
                body = _generate_body_with_claude(api_key, prompt_template, name, email, company_name, sender_name)
                bodies.append({"email": email, "name": name, "body": body})
            except Exception as e:
                bodies.append({"email": email, "name": name, "body": "", "error": str(e)})
        return jsonify({"ok": True, "bodies": bodies})
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
        custom_bodies = data.get("customBodies") or data.get("custom_bodies") or []
        ai_subject = (data.get("subject") or "").strip()
        if not gmail or not password:
            return jsonify({"error": "Gmail and password are required"}), 400
        if not recipients:
            return jsonify({"error": "recipients list is required"}), 400

        use_custom = bool(custom_bodies)
        if use_custom:
            if not ai_subject:
                return jsonify({"error": "subject is required when using customBodies"}), 400
        else:
            if not template_id:
                return jsonify({"error": "templateId is required (or provide customBodies + subject)"}), 400
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

        body_by_email = {b["email"]: b.get("body") or "" for b in custom_bodies} if use_custom else {}
        sent = 0
        failed = []

        for r in recipients:
            name = (r.get("name") or "").strip()
            email = (r.get("email") or "").strip()
            if not email:
                continue
            if use_custom:
                subject = ai_subject.replace("{{name}}", name)
                body_plain = body_by_email.get(email) or ""
                if not body_plain:
                    failed.append({"email": email, "error": "No generated body for this recipient"})
                    continue
                body_html = None
            else:
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
