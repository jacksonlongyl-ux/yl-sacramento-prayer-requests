#!/usr/bin/env python3
"""
Young Life Sacramento — Prayer Requests Automation

Commands:
  send-email   Read sheet, send Monday email, save state
  build-site   Read sheet, generate static site for GitHub Pages
"""

import os
import json
import html
import smtplib
import argparse
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────

SPREADSHEET_ID = "1fbNV9-u4x2_V0-O8khYnMoxM5bxaHajuJN706hsygXs"
REQUESTS_RANGE = "A:E"
SUBSCRIBERS_RANGE = "Subscribers!A:B"  # Email, Active (TRUE/FALSE)
SUBSCRIBE_FORM_URL = os.environ.get("SUBSCRIBE_FORM_URL", "")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPTS_DIR, "last_state.json")
SITE_OUTPUT = os.path.join(SCRIPTS_DIR, "..", "docs", "index.html")

# Column indices in the sheet
COL_TIMESTAMP = 0
COL_NAME = 1
COL_REQUEST = 2
COL_ROLE = 3
COL_UPDATE = 4

YL_PURPLE = "#4a235a"
YL_GREEN = "#27ae60"


# ── Google Sheets ─────────────────────────────────────────────────────────────

def _get_credentials():
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_json:
        info = json.loads(creds_json)
    else:
        local_path = os.path.join(SCRIPTS_DIR, "service_account.json")
        with open(local_path) as f:
            info = json.load(f)
    return service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )


def _get_sheet_values(range_name):
    service = build("sheets", "v4", credentials=_get_credentials())
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=range_name)
        .execute()
    )
    return result.get("values", [])


def get_prayer_rows():
    rows = _get_sheet_values(REQUESTS_RANGE)
    if not rows:
        return []
    out = []
    for row in rows[1:]:  # skip header
        while len(row) < 5:
            row.append("")
        out.append(
            {
                "timestamp": row[COL_TIMESTAMP].strip(),
                "name": row[COL_NAME].strip(),
                "request": row[COL_REQUEST].strip(),
                "role": row[COL_ROLE].strip(),
                "update": row[COL_UPDATE].strip(),
            }
        )
    return out


def get_subscribers():
    """Read subscriber emails from the Subscribers tab. Falls back to env var."""
    fallback = os.environ.get("EMAIL_RECIPIENTS", "jacksonlongyl@gmail.com")
    fallback_list = [e.strip() for e in fallback.split(",") if e.strip()]
    try:
        rows = _get_sheet_values(SUBSCRIBERS_RANGE)
        if not rows:
            return fallback_list
        emails = []
        for row in rows[1:]:  # skip header
            if len(row) >= 1:
                email = row[0].strip()
                active = row[1].strip().upper() if len(row) >= 2 else "TRUE"
                if email and active != "FALSE":
                    emails.append(email)
        return emails if emails else fallback_list
    except Exception:
        return fallback_list


# ── State tracking ────────────────────────────────────────────────────────────

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"rows": {}}


def save_state(rows):
    state = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "rows": {
            row["timestamp"]: {"had_update": bool(row["update"])}
            for row in rows
            if row["timestamp"]
        },
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"State saved ({len(state['rows'])} rows)")


# ── Email ─────────────────────────────────────────────────────────────────────

def _e(text):
    """HTML-escape user content."""
    return html.escape(text)


def _build_email_html(active, newly_updated, date_str):
    sections = ""

    if newly_updated:
        cards = ""
        for r in newly_updated:
            cards += f"""
      <div style="margin:12px 0;padding:14px 16px;background:#f0fff4;
                  border-left:3px solid {YL_GREEN};border-radius:4px;">
        <div style="font-weight:600;margin-bottom:2px;">{_e(r['name'])}</div>
        <div style="font-size:13px;color:#777;margin-bottom:8px;">{_e(r['role'])}</div>
        <div style="font-size:11px;font-weight:700;color:{YL_GREEN};
                    text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Update</div>
        <div style="line-height:1.6;color:#2d6a4f;">{_e(r['update'])}</div>
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid #c3e6cb;
                    font-size:13px;color:#555;font-style:italic;">
          Original request: {_e(r['request'])}
        </div>
      </div>"""
        sections += f"""
    <h2 style="color:{YL_PURPLE};margin:28px 0 8px;font-size:18px;">
      Praise Reports &amp; Updates
    </h2>{cards}"""

    if active:
        cards = ""
        for r in active:
            cards += f"""
      <div style="margin:12px 0;padding:14px 16px;background:#f9f5ff;
                  border-left:3px solid {YL_PURPLE};border-radius:4px;">
        <div style="font-weight:600;margin-bottom:2px;">{_e(r['name'])}</div>
        <div style="font-size:13px;color:#777;margin-bottom:8px;">{_e(r['role'])}</div>
        <div style="line-height:1.6;color:#444;">{_e(r['request'])}</div>
      </div>"""
        sections += f"""
    <h2 style="color:{YL_PURPLE};margin:28px 0 8px;font-size:18px;">
      Active Prayer Requests
    </h2>{cards}"""
    else:
        sections += f"""
    <h2 style="color:{YL_PURPLE};margin:28px 0 8px;font-size:18px;">
      Active Prayer Requests
    </h2>
    <p style="color:#aaa;font-style:italic;">No open requests this week.</p>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             color:#333;margin:0;padding:0;background:#f5f0ff;">
  <div style="max-width:600px;margin:0 auto;background:white;">

    <div style="background:{YL_PURPLE};color:white;padding:28px 24px;text-align:center;">
      <div style="font-size:22px;font-weight:700;margin-bottom:4px;">
        Young Life College Sacramento
      </div>
      <div style="opacity:.8;font-size:14px;">Prayer Requests &nbsp;·&nbsp; {_e(date_str)}</div>
    </div>

    <div style="padding:24px;">{sections}
    </div>

    <div style="padding:16px 24px 24px;border-top:1px solid #eee;
                font-size:12px;color:#aaa;text-align:center;">
      Reply to unsubscribe &nbsp;·&nbsp;
      <a href="https://younglifesacramento.com" style="color:{YL_PURPLE};text-decoration:none;">
        younglifesacramento.com
      </a>
    </div>

  </div>
</body>
</html>"""


def send_email(html_body, recipients):
    smtp_user = os.environ["GMAIL_USER"]
    smtp_pass = os.environ["GMAIL_APP_PASSWORD"]
    date_str = datetime.now().strftime("%B %d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"YL College Sacramento Prayer Requests — {date_str}"
    msg["From"] = f"Young Life College Sacramento <{smtp_user}>"
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, recipients, msg.as_string())

    print(f"Email sent to: {', '.join(recipients)}")


# ── Site builder ──────────────────────────────────────────────────────────────

def _prayer_card(r):
    return f"""
        <div class="card">
          <div class="card-meta">
            <span class="card-name">{_e(r['name'])}</span>
            {f'<span class="card-role">{_e(r["role"])}</span>' if r['role'] else ''}
          </div>
          <p class="card-text">{_e(r['request'])}</p>
        </div>"""


def _update_card(r):
    return f"""
        <div class="card card--update">
          <div class="card-meta">
            <span class="card-name">{_e(r['name'])}</span>
            {f'<span class="card-role">{_e(r["role"])}</span>' if r['role'] else ''}
          </div>
          <p class="card-text card-text--muted">{_e(r['request'])}</p>
          <div class="update-block">
            <span class="update-badge">Update</span>
            <p class="card-text">{_e(r['update'])}</p>
          </div>
        </div>"""


def build_site():
    rows = get_prayer_rows()
    updated_at = datetime.now(timezone.utc).strftime("%B %d, %Y · %I:%M %p UTC")

    active = sorted(
        [r for r in rows if not r["update"]], key=lambda r: r["timestamp"], reverse=True
    )
    answered = sorted(
        [r for r in rows if r["update"]], key=lambda r: r["timestamp"], reverse=True
    )

    active_cards = "".join(_prayer_card(r) for r in active) or \
        '<p class="empty-state">No open requests right now.</p>'
    update_cards = "".join(_update_card(r) for r in answered) or \
        '<p class="empty-state">No updates yet.</p>'

    active_count = len(active)
    update_count = len(answered)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Young Life Sacramento — Prayer Requests</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --purple: {YL_PURPLE};
      --purple-light: #f3eef8;
      --purple-mid: #7b4f96;
      --green: {YL_GREEN};
      --green-light: #edfaf3;
      --green-dark: #1e7e4a;
      --text: #1a1a2e;
      --text-muted: #6b7280;
      --border: #e5e7eb;
      --bg: #faf9fc;
      --white: #ffffff;
      --shadow-sm: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
      --shadow-md: 0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
      --radius: 12px;
    }}

    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }}

    /* ── Header ── */
    .site-header {{
      background: var(--purple);
      color: white;
      padding: 0;
      position: relative;
      overflow: hidden;
    }}
    .site-header::before {{
      content: '';
      position: absolute;
      inset: 0;
      background: radial-gradient(ellipse at 70% 50%, rgba(255,255,255,.07) 0%, transparent 60%);
      pointer-events: none;
    }}
    .header-inner {{
      max-width: 860px;
      margin: 0 auto;
      padding: 48px 24px 40px;
      position: relative;
    }}
    .header-eyebrow {{
      font-size: .75rem;
      font-weight: 600;
      letter-spacing: .12em;
      text-transform: uppercase;
      opacity: .6;
      margin-bottom: 10px;
    }}
    .header-title {{
      font-size: clamp(1.8rem, 5vw, 2.6rem);
      font-weight: 700;
      letter-spacing: -.02em;
      line-height: 1.15;
      margin-bottom: 10px;
    }}
    .header-subtitle {{
      font-size: 1rem;
      opacity: .7;
    }}

    /* ── Layout ── */
    .container {{
      max-width: 860px;
      margin: 0 auto;
      padding: 40px 24px 64px;
    }}

    /* ── Section ── */
    .section {{ margin-bottom: 48px; }}
    .section-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 20px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--border);
    }}
    .section-icon {{
      width: 36px; height: 36px;
      border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.1rem;
      flex-shrink: 0;
    }}
    .section-icon--pray {{ background: var(--purple-light); }}
    .section-icon--update {{ background: var(--green-light); }}
    .section-title {{
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--text);
      letter-spacing: -.01em;
    }}
    .section-count {{
      margin-left: auto;
      font-size: .78rem;
      font-weight: 600;
      color: var(--text-muted);
      background: var(--border);
      padding: 3px 10px;
      border-radius: 20px;
    }}

    /* ── Cards ── */
    .cards {{ display: grid; gap: 14px; }}
    @media (min-width: 640px) {{
      .cards {{ grid-template-columns: repeat(2, 1fr); }}
    }}

    .card {{
      background: var(--white);
      border-radius: var(--radius);
      padding: 20px 22px;
      box-shadow: var(--shadow-sm);
      border: 1px solid var(--border);
      transition: box-shadow .15s ease, transform .15s ease;
    }}
    .card:hover {{
      box-shadow: var(--shadow-md);
      transform: translateY(-1px);
    }}
    .card--update {{
      border-color: #d1fae5;
    }}

    .card-meta {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }}
    .card-name {{
      font-weight: 600;
      font-size: .95rem;
      color: var(--text);
    }}
    .card-role {{
      font-size: .72rem;
      font-weight: 500;
      color: var(--purple-mid);
      background: var(--purple-light);
      padding: 2px 8px;
      border-radius: 20px;
    }}
    .card-text {{
      font-size: .9rem;
      color: #374151;
      line-height: 1.65;
    }}
    .card-text--muted {{
      color: var(--text-muted);
      font-style: italic;
      margin-bottom: 14px;
    }}

    .update-block {{
      padding-top: 14px;
      border-top: 1px solid #d1fae5;
    }}
    .update-badge {{
      display: inline-block;
      font-size: .68rem;
      font-weight: 700;
      letter-spacing: .09em;
      text-transform: uppercase;
      color: var(--green-dark);
      background: var(--green-light);
      border: 1px solid #a7f3d0;
      padding: 2px 8px;
      border-radius: 20px;
      margin-bottom: 8px;
    }}

    .empty-state {{
      color: var(--text-muted);
      font-style: italic;
      padding: 12px 0;
      font-size: .9rem;
    }}

    /* ── Footer ── */
    .subscribe-section {{
      background: var(--purple);
      color: white;
      padding: 48px 24px;
      text-align: center;
    }}
    .subscribe-inner {{
      max-width: 480px;
      margin: 0 auto;
    }}
    .subscribe-title {{
      font-size: 1.5rem;
      font-weight: 700;
      letter-spacing: -.02em;
      margin-bottom: 10px;
    }}
    .subscribe-body {{
      font-size: .95rem;
      opacity: .8;
      line-height: 1.6;
      margin-bottom: 24px;
    }}
    .subscribe-btn {{
      display: inline-block;
      background: white;
      color: var(--purple);
      font-weight: 600;
      font-size: .95rem;
      padding: 12px 28px;
      border-radius: 8px;
      text-decoration: none;
      transition: opacity .15s ease;
    }}
    .subscribe-btn:hover {{ opacity: .9; }}

    .site-footer {{
      border-top: 1px solid var(--border);
      padding: 24px;
      text-align: center;
      font-size: .8rem;
      color: var(--text-muted);
    }}
    .site-footer a {{
      color: var(--purple);
      text-decoration: none;
      font-weight: 500;
    }}
    .site-footer a:hover {{ text-decoration: underline; }}
    .footer-updated {{
      margin-top: 6px;
      font-size: .75rem;
      color: #9ca3af;
    }}
  </style>
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <p class="header-eyebrow">Young Life College Sacramento</p>
    <h1 class="header-title">Prayer Requests</h1>
    <p class="header-subtitle">Introducing college students to Jesus and helping them grow in their faith</p>
  </div>
</header>

<div class="container">

  <section class="section">
    <div class="section-header">
      <div class="section-icon section-icon--pray"></div>
      <h2 class="section-title">Pray For</h2>
      <span class="section-count">{active_count}</span>
    </div>
    <div class="cards">
      {active_cards}
    </div>
  </section>

  <section class="section">
    <div class="section-header">
      <div class="section-icon section-icon--update"></div>
      <h2 class="section-title">Updates &amp; Praise</h2>
      <span class="section-count">{update_count}</span>
    </div>
    <div class="cards">
      {update_cards}
    </div>
  </section>

</div>

{f'''<section class="subscribe-section">
  <div class="subscribe-inner">
    <h2 class="subscribe-title">Pray With Us</h2>
    <p class="subscribe-body">Get prayer requests delivered to your inbox each morning. Join the team praying for students.</p>
    <a href="{SUBSCRIBE_FORM_URL}" class="subscribe-btn" target="_blank" rel="noopener">Sign up to pray</a>
  </div>
</section>''' if SUBSCRIBE_FORM_URL else ''}

<footer class="site-footer">
  <a href="https://younglifesacramento.com">Young Life College Sacramento</a>
  <p class="footer-updated">Last updated {updated_at}</p>
</footer>

</body>
</html>"""

    os.makedirs(os.path.dirname(os.path.abspath(SITE_OUTPUT)), exist_ok=True)
    with open(SITE_OUTPUT, "w") as f:
        f.write(page)
    print(f"Site built — {len(active)} active, {len(answered)} updated requests")


# ── Entry point ───────────────────────────────────────────────────────────────

def cmd_send_email():
    rows = get_prayer_rows()
    state = load_state()

    active, newly_updated = [], []
    for r in rows:
        had_update = state["rows"].get(r["timestamp"], {}).get("had_update", False)
        has_update = bool(r["update"])
        if has_update and not had_update:
            newly_updated.append(r)
        elif not has_update:
            active.append(r)

    active.sort(key=lambda r: r["timestamp"])

    date_str = datetime.now().strftime("%B %d, %Y")
    html_body = _build_email_html(active, newly_updated, date_str)
    recipients = get_subscribers()
    send_email(html_body, recipients)
    save_state(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["send-email", "build-site"])
    args = parser.parse_args()

    if args.command == "send-email":
        cmd_send_email()
    elif args.command == "build-site":
        build_site()
