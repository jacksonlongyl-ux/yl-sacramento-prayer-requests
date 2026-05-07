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

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPTS_DIR, "last_state.json")
SITE_OUTPUT = os.path.join(SCRIPTS_DIR, "..", "site", "index.html")

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
      🙌 Praise Reports &amp; Updates
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
      🙏 Active Prayer Requests
    </h2>{cards}"""
    else:
        sections += f"""
    <h2 style="color:{YL_PURPLE};margin:28px 0 8px;font-size:18px;">
      🙏 Active Prayer Requests
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
        Young Life Sacramento
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
    msg["Subject"] = f"YL Sacramento Prayer Requests — {date_str}"
    msg["From"] = f"Young Life Sacramento <{smtp_user}>"
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, recipients, msg.as_string())

    print(f"Email sent to: {', '.join(recipients)}")


# ── Site builder ──────────────────────────────────────────────────────────────

def _card(r, answered=False):
    accent = YL_GREEN if answered else YL_PURPLE
    bg = "#f0fff4" if answered else "#f9f5ff"
    update_section = ""
    if answered:
        update_section = f"""
      <div class="update-section">
        <div class="update-label">Update</div>
        <p class="update-text">{_e(r['update'])}</p>
      </div>"""
    return f"""
    <div class="card" style="border-left-color:{accent};background:{bg};">
      <div class="card-header">
        <span class="name">{_e(r['name'])}</span>
        <span class="role">{_e(r['role'])}</span>
      </div>
      <p class="request-text">{_e(r['request'])}</p>{update_section}
    </div>"""


def build_site():
    rows = get_prayer_rows()
    updated_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")

    active = sorted(
        [r for r in rows if not r["update"]], key=lambda r: r["timestamp"], reverse=True
    )
    answered = sorted(
        [r for r in rows if r["update"]], key=lambda r: r["timestamp"], reverse=True
    )

    active_html = "".join(_card(r) for r in active) or '<p class="empty">No open requests right now.</p>'
    answered_html = "".join(_card(r, answered=True) for r in answered) or '<p class="empty">No updates yet.</p>'

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Young Life Sacramento — Prayer Requests</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        background:#f5f0ff;color:#333}}
  header{{background:{YL_PURPLE};color:white;padding:36px 24px;text-align:center}}
  header h1{{font-size:1.9rem;font-weight:700;margin-bottom:6px}}
  header p{{opacity:.75;font-size:.95rem}}
  .container{{max-width:720px;margin:0 auto;padding:32px 16px}}
  h2{{font-size:1.2rem;color:{YL_PURPLE};margin:36px 0 14px;
      display:flex;align-items:center;gap:8px}}
  .card{{background:white;border-radius:8px;padding:18px 20px;margin-bottom:14px;
         box-shadow:0 1px 4px rgba(0,0,0,.07);border-left:4px solid}}
  .card-header{{display:flex;align-items:baseline;gap:10px;margin-bottom:10px;flex-wrap:wrap}}
  .name{{font-weight:600;font-size:1.05rem}}
  .role{{font-size:.8rem;color:#888;background:#ede8f5;padding:2px 9px;border-radius:12px}}
  .request-text{{line-height:1.65;color:#444}}
  .update-section{{margin-top:14px;padding-top:12px;border-top:1px solid #c3e6cb}}
  .update-label{{font-size:.75rem;font-weight:700;color:{YL_GREEN};
                 text-transform:uppercase;letter-spacing:.07em;margin-bottom:5px}}
  .update-text{{line-height:1.65;color:#2d6a4f}}
  .empty{{color:#bbb;font-style:italic;padding:8px 0}}
  footer{{text-align:center;padding:32px 16px;color:#aaa;font-size:.83rem}}
  footer a{{color:{YL_PURPLE};text-decoration:none}}
  .updated{{font-size:.78rem;color:#bbb;margin-top:6px}}
</style>
</head>
<body>
<header>
  <h1>Young Life Sacramento</h1>
  <p>Prayer Requests</p>
</header>
<div class="container">

  <h2>🙏 Pray For</h2>
  {active_html}

  <h2>🙌 Updates &amp; Praise</h2>
  {answered_html}

</div>
<footer>
  <a href="https://younglifesacramento.com">younglifesacramento.com</a>
  <p class="updated">Last updated: {updated_at}</p>
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
