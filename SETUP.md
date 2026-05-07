# Setup Guide

## What this does

- **Every Monday at 9am PT** — emails the prayer list to all subscribers
  - Active requests (no update yet) are listed under "Pray For"
  - Any request that got an update *since last Monday* appears under "Praise Reports"
- **Every 6 hours** — rebuilds the public GitHub Pages site from the live sheet

---

## Step 1 — Create a Google Cloud service account

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `yl-sacramento`)
3. Enable these two APIs:
   - **Google Sheets API**
   - (No Gmail API needed — we use SMTP instead)
4. Go to **IAM & Admin → Service Accounts → Create Service Account**
   - Name: `prayer-requests-bot`
   - Skip optional steps, click Done
5. Click the new service account → **Keys → Add Key → JSON**
   - Download the JSON file — you'll paste its contents as a secret shortly

6. **Share the Google Sheet with the service account email**
   - The service account email looks like: `prayer-requests-bot@yl-sacramento.iam.gserviceaccount.com`
   - Open the sheet → Share → paste that email → Viewer access

---

## Step 2 — Add a Subscribers tab to the sheet

In your Google Sheet, add a second tab named exactly **`Subscribers`** with these headers in row 1:

| Email | Active |
|---|---|
| jacksonlongyl@gmail.com | TRUE |

To add more subscribers, add rows. Set Active to `FALSE` to pause without deleting.

> **To let people subscribe via form:** Create a Google Form with an Email field, link its responses to a new sheet tab, then rename/reshape that tab to match the `Subscribers` format — or just add people manually.

---

## Step 3 — Get a Gmail App Password

Gmail won't accept your regular password for scripts. You need an App Password:

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Under "How you sign in to Google", enable **2-Step Verification** if not already on
3. Search for **App Passwords** (or go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords))
4. Create one: App = Mail, Device = Other → name it `YL Prayer Requests`
5. Copy the 16-character password

---

## Step 4 — Create the GitHub repo and set secrets

1. Create a new GitHub repo (e.g. `yl-sacramento-prayer-requests`) — can be public or private
2. Push this project:
   ```bash
   cd "prayer-requests"
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/yl-sacramento-prayer-requests.git
   git push -u origin main
   ```
3. In the repo on GitHub: **Settings → Secrets and variables → Actions → New repository secret**

   Add these four secrets:

   | Secret name | Value |
   |---|---|
   | `GOOGLE_SERVICE_ACCOUNT_JSON` | Paste the full contents of the JSON file from Step 1 |
   | `GMAIL_USER` | `jacksonlongyl@gmail.com` |
   | `GMAIL_APP_PASSWORD` | The 16-character app password from Step 3 |
   | `EMAIL_RECIPIENTS` | `jacksonlongyl@gmail.com` (fallback if Subscribers tab is empty) |

---

## Step 5 — Enable GitHub Pages

1. In the repo: **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `gh-pages` / `/ (root)`
4. Save

The site will be live at: `https://YOUR_USERNAME.github.io/yl-sacramento-prayer-requests/`

> The `gh-pages` branch is created automatically the first time the "Rebuild Site" workflow runs.

---

## Step 6 — Test it

Trigger both workflows manually to confirm everything works:

1. **Settings → Actions → "Rebuild Prayer Requests Site" → Run workflow**
   - Check the `gh-pages` branch to confirm `index.html` was generated
2. **"Send Monday Prayer Email" → Run workflow**
   - Check your inbox

---

## Schedule

| Action | When |
|---|---|
| Email sent | Every Monday, 9:00 AM Pacific |
| Site rebuilt | Every 6 hours |

To change the email time, edit `.github/workflows/monday-email.yml` and adjust the cron.
Pacific time = UTC − 7 (summer) or UTC − 8 (winter).
9am PDT = `0 16 * * 1` | 9am PST = `0 17 * * 1`
