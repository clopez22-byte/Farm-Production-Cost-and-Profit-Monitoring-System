# Farm Production Cost and Profit Monitoring System

A Streamlit + SQLite prototype for a cooperative/association setting.

## Features
- Role-based sign-in: Administrator, Farmer, Agricultural Officer
- Farm information records
- Production expense records (seeds, fertilizer, pesticides, labor, transport, etc.)
- Harvest quantity records
- Product sales records
- Dashboard with total expenses, sales, harvest, and estimated profit/loss
- Date-range profit and loss reports with CSV export
- Administrator can create user accounts

## Demo accounts
Created automatically the first time the app runs:

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `Admin123!` |
| Farmer | `farmer` | `Farmer123!` |
| Agricultural Officer | `officer` | `Officer123!` |

Change demo passwords and configure production authentication before real deployment.

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the app:
   ```bash
   streamlit run app.py
   ```

## Publish with GitHub and Streamlit Community Cloud
1. Create a GitHub repository, for example `farm-cost-profit-monitor`.
2. Upload `app.py`, `requirements.txt`, `.gitignore`, and `README.md`.
3. Open https://share.streamlit.io/ and sign in with GitHub.
4. Select **New app**, choose the repository and branch, and set the main file path to `app.py`.
5. Deploy.

## User roles
- **Administrator:** creates accounts and views all farm, expense, harvest, sales, and report data.
- **Farmer:** manages their own farm records, expenses, harvest, and sales; sees only their own data.
- **Agricultural Officer:** read-only dashboard, farm records, and reports for monitoring.

## Important prototype limitations
- SQLite is suitable for a classroom prototype, not a multi-user production deployment.
- The demo credentials are public and must not be used for real personal or financial data.
- Use a hosted database, HTTPS, secure secret management, backups, audit logs, and stronger account administration before operational use.
- Administrator farm creation currently assigns the farm to the first active farmer. For clean ownership assignment, create the farm while signed in as the intended farmer.
- This system calculates estimated profit from recorded sales minus recorded expenses; it does not value unsold harvest or automatically allocate shared costs.
