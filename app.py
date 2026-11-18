import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import secrets
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).with_name("farm_monitor.db")

st.set_page_config(page_title="Farm Cost & Profit Monitor", page_icon="🌾", layout="wide")

# ---------- Database ----------
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"

def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
        return secrets.compare_digest(hash_password(password, salt).split("$", 1)[1], digest)
    except Exception:
        return False

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Administrator','Farmer','Agricultural Officer')),
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS farms(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            farm_name TEXT NOT NULL,
            location TEXT,
            size_hectares REAL DEFAULT 0,
            crop_type TEXT,
            FOREIGN KEY(farmer_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            farm_id INTEGER NOT NULL,
            expense_date TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            FOREIGN KEY(farmer_id) REFERENCES users(id),
            FOREIGN KEY(farm_id) REFERENCES farms(id)
        );
        CREATE TABLE IF NOT EXISTS harvests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            farm_id INTEGER NOT NULL,
            harvest_date TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY(farmer_id) REFERENCES users(id),
            FOREIGN KEY(farm_id) REFERENCES farms(id)
        );
        CREATE TABLE IF NOT EXISTS sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            farm_id INTEGER NOT NULL,
            sale_date TEXT NOT NULL,
            product TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            unit_price REAL NOT NULL,
            buyer TEXT,
            FOREIGN KEY(farmer_id) REFERENCES users(id),
            FOREIGN KEY(farm_id) REFERENCES farms(id)
        );
        """)
        # First-run demo accounts. Change these passwords after signing in.
        if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            demos = [
                ("admin", "Admin123!", "System Administrator", "Administrator"),
                ("farmer", "Farmer123!", "Demo Farmer", "Farmer"),
                ("officer", "Officer123!", "Agricultural Officer", "Agricultural Officer"),
            ]
            for username, password, name, role in demos:
                con.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)",
                            (username, hash_password(password), name, role))
            farmer_id = con.execute("SELECT id FROM users WHERE username='farmer'").fetchone()["id"]
            con.execute("INSERT INTO farms(farmer_id,farm_name,location,size_hectares,crop_type) VALUES(?,?,?,?,?)",
                        (farmer_id, "Demo Rice Farm", "Bunawan, Agusan del Sur", 1.5, "Rice"))

init_db()

def query_df(sql, params=()):
    with db() as con:
        return pd.read_sql_query(sql, con, params=params)

def execute(sql, params=()):
    with db() as con:
        con.execute(sql, params)
        con.commit()

def current_user():
    return st.session_state.get("user")

def farm_options(user):
    if user["role"] == "Farmer":
        return query_df("SELECT id, farm_name FROM farms WHERE farmer_id=? ORDER BY farm_name", (user["id"],))
    return query_df("""SELECT f.id, f.farm_name, u.full_name AS farmer_name
                       FROM farms f JOIN users u ON u.id=f.farmer_id ORDER BY f.farm_name""")

def selected_farm_id(df):
    if df.empty:
        return None
    labels = [f"{r.farm_name}" + (f" — {r.farmer_name}" if "farmer_name" in df.columns else "") for r in df.itertuples()]
    chosen = st.selectbox("Select farm", range(len(labels)), format_func=lambda x: labels[x])
    return int(df.iloc[chosen]["id"])

def scoped_sql(user, table_alias=""):
    # Non-farmers can see all records; farmers only see their own.
    if user["role"] == "Farmer":
        return " WHERE " + (table_alias + "." if table_alias else "") + "farmer_id=?", (user["id"],)
    return "", ()

# ---------- Authentication ----------
if "user" not in st.session_state:
    st.session_state.user = None

def login_screen():
    st.title("🌾 Farm Production Cost & Profit Monitoring System")
    st.write("Manage farm information, production expenses, harvests, sales, and financial reports.")
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Sign in")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            row = query_df("SELECT * FROM users WHERE username=? AND active=1", (username.strip(),))
            if not row.empty and verify_password(password, row.iloc[0]["password_hash"]):
                st.session_state.user = row.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Incorrect username or password, or account is inactive.")
    with right:
        st.subheader("Demo accounts")
        st.info("Administrator: `admin` / `Admin123!`\n\nFarmer: `farmer` / `Farmer123!`\n\nAgricultural Officer: `officer` / `Officer123!`")
        st.caption("Demo accounts are created automatically on first launch. Change these passwords before real deployment.")

if not current_user():
    login_screen()
    st.stop()

user = current_user()
with st.sidebar:
    st.title("🌾 Farm Monitor")
    st.write(f"**{user['full_name']}**")
    st.caption(user["role"])
    st.divider()
    pages = ["Dashboard", "Farm Information", "Production Expenses", "Harvest Records", "Product Sales", "Profit & Loss Reports"]
    if user["role"] == "Administrator":
        pages += ["User Management"]
    page = st.radio("Navigation", pages)
    if st.button("Sign out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

st.title(page)
st.caption("Farm Production Cost and Profit Monitoring System")

# ---------- Dashboard ----------
if page == "Dashboard":
    where, params = scoped_sql(user)
    expenses = query_df("SELECT COALESCE(SUM(amount),0) total FROM expenses" + where, params).iloc[0]["total"]
    sales = query_df("SELECT COALESCE(SUM(quantity*unit_price),0) total FROM sales" + where, params).iloc[0]["total"]
    harvest = query_df("SELECT COALESCE(SUM(quantity),0) total FROM harvests" + where, params).iloc[0]["total"]
    profit = sales - expenses
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Expenses", f"₱{expenses:,.2f}")
    c2.metric("Total Sales / Income", f"₱{sales:,.2f}")
    c3.metric("Harvest Quantity", f"{harvest:,.2f}")
    c4.metric("Estimated Profit / Loss", f"₱{profit:,.2f}", delta=f"₱{profit:,.2f}")
    st.info("Profit is calculated as recorded sales minus recorded expenses. It is an estimate based only on entries in this system.")
    exp_df = query_df("SELECT category, SUM(amount) AS amount FROM expenses" + where + " GROUP BY category", params)
    sale_df = query_df("SELECT sale_date, SUM(quantity*unit_price) AS income FROM sales" + where + " GROUP BY sale_date ORDER BY sale_date", params)
    a,b = st.columns(2)
    with a:
        st.subheader("Expenses by category")
        if not exp_df.empty:
            st.bar_chart(exp_df.set_index("category"))
        else:
            st.write("No expense records yet.")
    with b:
        st.subheader("Sales income over time")
        if not sale_df.empty:
            st.line_chart(sale_df.set_index("sale_date"))
        else:
            st.write("No sales records yet.")
    if user["role"] == "Agricultural Officer":
        st.caption("Officer view: dashboard and reports are read-only.")

# ---------- Farm Information ----------
elif page == "Farm Information":
    farms = farm_options(user)
    if user["role"] in ("Farmer", "Administrator"):
        st.subheader("Add farm")
        with st.form("farm_form"):
            farm_name = st.text_input("Farm name")
            location = st.text_input("Location")
            size = st.number_input("Farm size (hectares)", min_value=0.0, step=0.1)
            crop = st.text_input("Main crop")
            farmers = query_df("SELECT id, full_name FROM users WHERE role='Farmer' AND active=1") if user["role"] == "Administrator" else pd.DataFrame()
            owner_id = user["id"]
            if user["role"] == "Administrator":
                if not farmers.empty:
                    chosen_farmer = st.selectbox("Assign farm to farmer", farmers["full_name"].tolist())
                    owner_id = int(farmers.loc[farmers["full_name"] == chosen_farmer, "id"].iloc[0])
                else:
                    st.warning("Create a farmer account before adding a farm.")
            if st.form_submit_button("Save farm"):
                if not farm_name.strip():
                    st.error("Farm name is required.")
                elif user["role"] == "Administrator" and farmers.empty:
                    st.error("Create a farmer account first.")
                else:
                    execute("INSERT INTO farms(farmer_id,farm_name,location,size_hectares,crop_type) VALUES(?,?,?,?,?)",
                            (owner_id, farm_name.strip(), location, size, crop))
                    st.success("Farm saved.")
                    st.rerun()
    st.subheader("Registered farms")
    sql = """SELECT f.id, f.farm_name, u.full_name AS farmer, f.location, f.size_hectares, f.crop_type
             FROM farms f JOIN users u ON u.id=f.farmer_id"""
    if user["role"] == "Farmer":
        sql += " WHERE f.farmer_id=?"
        data = query_df(sql + " ORDER BY f.id DESC", (user["id"],))
    else:
        data = query_df(sql + " ORDER BY f.id DESC")
    st.dataframe(data, use_container_width=True, hide_index=True)

# ---------- Expenses ----------
elif page == "Production Expenses":
    farms = farm_options(user)
    if user["role"] in ("Farmer", "Administrator"):
        if farms.empty:
            st.warning("Add a farm before recording expenses.")
        else:
            st.subheader("Record production expense")
            with st.form("expense_form"):
                farm_id = selected_farm_id(farms)
                expense_date = st.date_input("Expense date", value=date.today())
                category = st.selectbox("Category", ["Seeds", "Fertilizers", "Pesticides", "Labor", "Transportation", "Equipment", "Water / Irrigation", "Other"])
                description = st.text_input("Description")
                amount = st.number_input("Amount (PHP)", min_value=0.01, step=100.0)
                if st.form_submit_button("Save expense"):
                    owner_id = user["id"] if user["role"] == "Farmer" else int(query_df("SELECT farmer_id FROM farms WHERE id=?", (farm_id,)).iloc[0]["farmer_id"])
                    execute("INSERT INTO expenses(farmer_id,farm_id,expense_date,category,description,amount) VALUES(?,?,?,?,?,?)",
                            (owner_id, farm_id, str(expense_date), category, description, amount))
                    st.success("Expense recorded.")
                    st.rerun()
    where, params = scoped_sql(user)
    data = query_df("""SELECT e.expense_date, f.farm_name, u.full_name AS farmer, e.category, e.description, e.amount
                       FROM expenses e JOIN farms f ON f.id=e.farm_id JOIN users u ON u.id=e.farmer_id""" +
                    (" WHERE e.farmer_id=?" if user["role"]=="Farmer" else "") + " ORDER BY e.expense_date DESC", params)
    st.subheader("Expense history")
    st.dataframe(data, use_container_width=True, hide_index=True)
    if not data.empty:
        st.download_button("Download expenses CSV", data.to_csv(index=False).encode("utf-8"), "farm_expenses.csv", "text/csv")

# ---------- Harvest ----------
elif page == "Harvest Records":
    farms = farm_options(user)
    if user["role"] in ("Farmer", "Administrator"):
        if farms.empty:
            st.warning("Add a farm before recording harvest.")
        else:
            st.subheader("Record harvest")
            with st.form("harvest_form"):
                farm_id = selected_farm_id(farms)
                harvest_date = st.date_input("Harvest date", value=date.today())
                quantity = st.number_input("Quantity harvested", min_value=0.01, step=1.0)
                unit = st.selectbox("Unit", ["kg", "sacks", "tons", "crates", "pieces"])
                notes = st.text_input("Notes")
                if st.form_submit_button("Save harvest"):
                    owner_id = user["id"] if user["role"] == "Farmer" else int(query_df("SELECT farmer_id FROM farms WHERE id=?", (farm_id,)).iloc[0]["farmer_id"])
                    execute("INSERT INTO harvests(farmer_id,farm_id,harvest_date,quantity,unit,notes) VALUES(?,?,?,?,?,?)",
                            (owner_id, farm_id, str(harvest_date), quantity, unit, notes))
                    st.success("Harvest recorded.")
                    st.rerun()
    sql = """SELECT h.harvest_date, f.farm_name, u.full_name AS farmer, h.quantity, h.unit, h.notes
             FROM harvests h JOIN farms f ON f.id=h.farm_id JOIN users u ON u.id=h.farmer_id"""
    data = query_df(sql + (" WHERE h.farmer_id=?" if user["role"]=="Farmer" else "") + " ORDER BY h.harvest_date DESC",
                    (user["id"],) if user["role"]=="Farmer" else ())
    st.subheader("Harvest history")
    st.dataframe(data, use_container_width=True, hide_index=True)

# ---------- Sales ----------
elif page == "Product Sales":
    farms = farm_options(user)
    if user["role"] in ("Farmer", "Administrator"):
        if farms.empty:
            st.warning("Add a farm before recording sales.")
        else:
            st.subheader("Record product sale")
            with st.form("sales_form"):
                farm_id = selected_farm_id(farms)
                sale_date = st.date_input("Sale date", value=date.today())
                product = st.text_input("Product / crop sold", value="Rice")
                quantity = st.number_input("Quantity sold", min_value=0.01, step=1.0)
                unit = st.selectbox("Unit", ["kg", "sacks", "tons", "crates", "pieces"])
                unit_price = st.number_input("Selling price per unit (PHP)", min_value=0.01, step=10.0)
                buyer = st.text_input("Buyer (optional)")
                if st.form_submit_button("Save sale"):
                    owner_id = user["id"] if user["role"] == "Farmer" else int(query_df("SELECT farmer_id FROM farms WHERE id=?", (farm_id,)).iloc[0]["farmer_id"])
                    execute("INSERT INTO sales(farmer_id,farm_id,sale_date,product,quantity,unit,unit_price,buyer) VALUES(?,?,?,?,?,?,?,?)",
                            (owner_id, farm_id, str(sale_date), product, quantity, unit, unit_price, buyer))
                    st.success("Sale recorded.")
                    st.rerun()
    sql = """SELECT s.sale_date, f.farm_name, u.full_name AS farmer, s.product, s.quantity, s.unit,
                    s.unit_price, (s.quantity*s.unit_price) AS total_income, s.buyer
             FROM sales s JOIN farms f ON f.id=s.farm_id JOIN users u ON u.id=s.farmer_id"""
    data = query_df(sql + (" WHERE s.farmer_id=?" if user["role"]=="Farmer" else "") + " ORDER BY s.sale_date DESC",
                    (user["id"],) if user["role"]=="Farmer" else ())
    st.subheader("Sales history")
    st.dataframe(data, use_container_width=True, hide_index=True)
    if not data.empty:
        st.download_button("Download sales CSV", data.to_csv(index=False).encode("utf-8"), "farm_sales.csv", "text/csv")

# ---------- Reports ----------
elif page == "Profit & Loss Reports":
    st.write("Select a date range to review production costs and income.")
    start = st.date_input("Start date", value=date(date.today().year, 1, 1))
    end = st.date_input("End date", value=date.today())
    if start > end:
        st.error("Start date must be on or before end date.")
        st.stop()
    farmer_clause = " AND farmer_id=?" if user["role"]=="Farmer" else ""
    p = [str(start), str(end)] + ([user["id"]] if user["role"]=="Farmer" else [])
    expenses = query_df("SELECT COALESCE(SUM(amount),0) total FROM expenses WHERE expense_date BETWEEN ? AND ?" + farmer_clause, p).iloc[0]["total"]
    income = query_df("SELECT COALESCE(SUM(quantity*unit_price),0) total FROM sales WHERE sale_date BETWEEN ? AND ?" + farmer_clause, p).iloc[0]["total"]
    c1,c2,c3 = st.columns(3)
    c1.metric("Production Cost", f"₱{expenses:,.2f}")
    c2.metric("Sales Income", f"₱{income:,.2f}")
    c3.metric("Estimated Profit / Loss", f"₱{income-expenses:,.2f}")
    st.caption("Estimated profit = sales income − recorded expenses. Unsold harvest is not counted as income.")
    exp_detail = query_df("""SELECT expense_date AS Date, category AS Type, description AS Details, amount AS Amount
                             FROM expenses WHERE expense_date BETWEEN ? AND ?""" + farmer_clause + " ORDER BY expense_date", p)
    sales_detail = query_df("""SELECT sale_date AS Date, product AS Product, quantity AS Quantity, unit,
                               unit_price AS Unit_Price, quantity*unit_price AS Income
                               FROM sales WHERE sale_date BETWEEN ? AND ?""" + farmer_clause + " ORDER BY sale_date", p)
    st.subheader("Expense details")
    st.dataframe(exp_detail, use_container_width=True, hide_index=True)
    st.subheader("Sales details")
    st.dataframe(sales_detail, use_container_width=True, hide_index=True)
    report = pd.DataFrame([{"Start date": start, "End date": end, "Production Cost": expenses,
                            "Sales Income": income, "Estimated Profit/Loss": income-expenses}])
    st.download_button("Download summary report CSV", report.to_csv(index=False).encode("utf-8"),
                       "farm_profit_loss_report.csv", "text/csv")

# ---------- Admin user management ----------
elif page == "User Management" and user["role"] == "Administrator":
    st.subheader("Create user account")
    with st.form("create_user"):
        full_name = st.text_input("Full name")
        username = st.text_input("Username")
        password = st.text_input("Temporary password", type="password")
        role = st.selectbox("Role", ["Farmer", "Agricultural Officer", "Administrator"])
        if st.form_submit_button("Create account"):
            if not full_name.strip() or not username.strip() or len(password) < 8:
                st.error("Enter a name and username, and use a password with at least 8 characters.")
            else:
                try:
                    execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)",
                            (username.strip(), hash_password(password), full_name.strip(), role))
                    st.success("Account created.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("That username is already in use.")
    st.subheader("User accounts")
    users = query_df("SELECT id, full_name, username, role, active FROM users ORDER BY id")
    st.dataframe(users, use_container_width=True, hide_index=True)
    st.caption("Account activation/deactivation and password reset are not included in this prototype.")

st.divider()
st.caption("Prototype for academic evaluation. Use HTTPS, secure secrets, backups, and a production database before real-world deployment.")
