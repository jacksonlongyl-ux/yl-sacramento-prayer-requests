# YL Prayer Requests

A free, automated prayer request system for Young Life ministries. Connects to a Google Sheet, sends a daily email to your prayer team, and publishes a live public website — all without any ongoing maintenance.

**[See a live example →](https://jacksonlongyl-ux.github.io/yl-sacramento-prayer-requests/)**

---

## What it does

- **Daily email at 4am** — sends all active prayer requests to everyone on your list. When a request gets an update, it highlights it as a praise report for two days.
- **Live website** — a public page showing all active requests and praise reports, rebuilt every hour from your Google Sheet.
- **Easy sign-ups** — link a Google Form so anyone can subscribe to the emails.

---

## Set up your own (30 minutes)

### Step 1 — Use this template

Click **"Use this template"** at the top of this repo → **"Create a new repository"**. Give it a name like `yl-[your-city]-prayer-requests`.

### Step 2 — Create your Google Sheet

1. Make a copy of [this Google Form template](https://forms.gle/Vm4mhQW92V4ewUng6) (or create your own with fields: Name, Role, "How can we pray for you?", "Update on Prayer Request")
2. Link the form responses to a Google Sheet
3. Copy the Sheet ID from the URL: `docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`

### Step 3 — Create a Google Cloud service account

> This lets the script read your private Google Sheet.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create a new project
2. Enable the **Google Sheets API**
3. Go to **IAM & Admin → Service Accounts → Create Service Account**
4. Click the new account → **Keys → Add Key → JSON** → download the file
5. **Share your Google Sheet** with the service account email (looks like `name@project.iam.gserviceaccount.com`) as a Viewer

### Step 4 — Set up email sending

**Option A — Gmail (simplest, sends from your own address)**
1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Create an app password for Mail → copy the 16-character code

**Option B — Resend (free, sends from a custom or shared address)**
1. Sign up at [resend.com](https://resend.com)
2. Create an API key → copy it
3. Set `FROM_EMAIL` to your desired from address (e.g. `Young Life Fresno <prayers@younglifefresno.com>`)

### Step 5 — Set up a subscribe form

1. Create a Google Form with two questions: **Name** and **Email**
2. Link its responses to a new tab in your sheet
3. Copy the form's share link

### Step 6 — Add GitHub secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Required | Description |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | ✅ | Full contents of the JSON file from Step 3 |
| `GMAIL_USER` | Gmail only | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail only | 16-character app password |
| `RESEND_API_KEY` | Resend only | API key from resend.com |
| `ORG_NAME` | | Your ministry name (default: Young Life College Sacramento) |
| `ORG_TAGLINE` | | Tagline shown on the site |
| `ORG_WEBSITE` | | Your ministry website URL |
| `SPREADSHEET_ID` | | Your Google Sheet ID from Step 2 |
| `SUBSCRIBE_FORM_URL` | | Your subscribe form link from Step 5 |
| `FROM_EMAIL` | Resend only | e.g. `Young Life Fresno <prayers@younglifefresno.com>` |
| `EMAIL_RECIPIENTS` | | Fallback email if subscriber sheet is empty |

### Step 7 — Enable GitHub Pages

1. **Settings → Pages → Source: Deploy from a branch**
2. Branch: `main` / Folder: `/docs` → Save

### Step 8 — Test it

1. **Actions → "Rebuild Prayer Requests Site" → Run workflow** — check your site URL
2. **Actions → "Send Monday Prayer Email" → Run workflow** — check your inbox

Your site will be at: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/`

---

## How the email logic works

- **Active requests** = rows with no update yet → listed under "Pray For"
- **Praise reports** = rows where an update was added since yesterday → shown under "Updates & Praise" for two consecutive days, then dropped
- **Subscribers** = anyone who fills out your subscribe form (read directly from the sheet)

---

## Schedule

| Action | When |
|---|---|
| Email sent | Every day at 4:00 AM Pacific |
| Site rebuilt | Every hour |

To change the email time, edit `.github/workflows/monday-email.yml`. Pacific time = UTC−7 (summer). Multiply: 4am PDT = `0 11 * * *`.

---

## Built by Young Life College Sacramento

Questions? Open an issue or email [jacksonlongyl@gmail.com](mailto:jacksonlongyl@gmail.com).
