
import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import secrets
from datetime import date
from pathlib import Path

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Farm Cost & Profit Monitor",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = Path(__file__).with_name("farm_monitor.db")

# =====================================================
# CUSTOM COLOR THEME
# =====================================================

st.markdown("""
<style>

/* Main background */
.stApp {
    background-color: #F4F8F1;
}

/* Main content spacing */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* Headings */
h1 {
    color: #1B5E20 !important;
    font-weight: 800 !important;
}

h2, h3 {
    color: #2E7D32 !important;
    font-weight: 700 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B5E20, #2E7D32);
}

[data-testid="stSidebar"] * {
    color: white;
}

/* Sidebar radio navigation */
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    background-color: rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 8px;
}

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button {
    background-color: #F9A825;
    color: #1B5E20 !important;
    font-weight: bold;
}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: white;
    padding: 20px;
    border-radius: 12px;
    border-left: 5px solid #4CAF50;
    box-shadow: 0 3px 12px rgba(0,0,0,0.07);
}

/* Metric values */
[data-testid="stMetricValue"] {
    color: #1B5E20;
    font-weight: bold;
}

/* Buttons */
.stButton > button,
.stFormSubmitButton > button,
.stDownloadButton > button {
    background-color: #2E7D32;
    color: white !important;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    padding: 10px 18px;
    transition: 0.3s;
}

/* Button hover */
.stButton > button:hover,
.stFormSubmitButton > button:hover,
.stDownloadButton > button:hover {
    background-color: #F9A825;
    color: #1B5E20 !important;
}

/* Forms */
[data-testid="stForm"] {
    background-color: white;
    padding: 22px;
    border: 1px solid #C8E6C9;
    border-radius: 12px;
}

/* Input fields */
.stTextInput input,
.stNumberInput input,
.stDateInput input {
    border-radius: 8px;
    border: 1px solid #A5D6A7;
}

/* Tables */
[data-testid="stDataFrame"] {
    background-color: white;
    border: 1px solid #C8E6C9;
    border-radius: 10px;
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 10px;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    color: #1B5E20;
    font-weight: bold;
}

/* Divider */
hr {
    border-color: #A5D6A7;
}

/* Captions */
.stCaption {
    color: #607D60;
}

/* Custom header */
.farm-header {
    background: linear-gradient(120deg, #1B5E20, #66BB6A);
    padding: 25px;
    border-radius: 15px;
    margin-bottom: 20px;
    color: white;
}

.farm-header h1 {
    color: white !important;
}

.farm-header p {
    color: white;
    font-size: 15px;
}

/* Section cards */
.section-card {
    background-color: white;
    padding: 20px;
    border-radius: 12px;
    border-left: 5px solid #F9A825;
    margin-bottom: 15px;
}

/* Login card */
.login-card {
    background-color: white;
    padding: 25px;
    border-radius: 15px;
    border: 1px solid #C8E6C9;
    box-shadow: 0 4px 15px rgba(0,0,0,0.06);
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# DATABASE CONNECTION
# =====================================================

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# =====================================================
# PASSWORD SECURITY
# =====================================================

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        120_000
    ).hex()

    return f"{salt}${digest}"


def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)

        return secrets.compare_digest(
            hash_password(password, salt).split("$", 1)[1],
            digest
        )

    except Exception:
        return False


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

def init_db():

    with db() as con:

        con.executescript("""

        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(
                role IN (
                    'Administrator',
                    'Farmer',
                    'Agricultural Officer'
                )
            ),
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

        # Create demo accounts on first launch

        if con.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0] == 0:

            demos = [
                ("admin", "Admin123!", "System Administrator", "Administrator"),
                ("farmer", "Farmer123!", "Demo Farmer", "Farmer"),
                ("officer", "Officer123!", "Agricultural Officer", "Agricultural Officer")
            ]

            for username, password, name, role in demos:

                con.execute(
                    """
                    INSERT INTO users(
                        username,
                        password_hash,
                        full_name,
                        role
                    )
                    VALUES(?,?,?,?)
                    """,
                    (
                        username,
                        hash_password(password),
                        name,
                        role
                    )
                )

            farmer_id = con.execute(
                "SELECT id FROM users WHERE username='farmer'"
            ).fetchone()["id"]

            con.execute(
                """
                INSERT INTO farms(
                    farmer_id,
                    farm_name,
                    location,
                    size_hectares,
                    crop_type
                )
                VALUES(?,?,?,?,?)
                """,
                (
                    farmer_id,
                    "Demo Rice Farm",
                    "Bunawan, Agusan del Sur",
                    1.5,
                    "Rice"
                )
            )


init_db()


# =====================================================
# DATABASE HELPER FUNCTIONS
# =====================================================

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

        return query_df(
            """
            SELECT id, farm_name
            FROM farms
            WHERE farmer_id=?
            ORDER BY farm_name
            """,
            (user["id"],)
        )

    return query_df(
        """
        SELECT f.id, f.farm_name,
               u.full_name AS farmer_name
        FROM farms f
        JOIN users u ON u.id=f.farmer_id
        ORDER BY f.farm_name
        """
    )


def selected_farm_id(df):

    if df.empty:
        return None

    labels = [
        f"{r.farm_name}" +
        (f" — {r.farmer_name}" if "farmer_name" in df.columns else "")
        for r in df.itertuples()
    ]

    chosen = st.selectbox(
        "Select farm",
        range(len(labels)),
        format_func=lambda x: labels[x]
    )

    return int(df.iloc[chosen]["id"])


def scoped_sql(user, table_alias=""):

    if user["role"] == "Farmer":

        return (
            " WHERE " +
            (table_alias + "." if table_alias else "") +
            "farmer_id=?",
            (user["id"],)
        )

    return "", ()


# =====================================================
# SESSION STATE
# =====================================================

if "user" not in st.session_state:
    st.session_state.user = None


# =====================================================
# LOGIN SCREEN
# =====================================================

def login_screen():

    st.markdown("""
<div class="farm-header">
    <h1>🌾 Farm Production Cost & Profit</h1>
    <h2>Monitoring System</h2>
    <p>
        Manage farm information, production expenses,
        harvests, sales, and financial reports.
    </p>
</div>
""", unsafe_allow_html=True)

    left, right = st.columns([1.2, 1])

    with left:

        st.markdown(
            '<div class="login-card">',
            unsafe_allow_html=True
        )

        st.subheader("🔐 Sign In")

        with st.form("login_form"):

            username = st.text_input(
                "Username",
                placeholder="Enter your username"
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )

            submitted = st.form_submit_button(
                "Sign In",
                use_container_width=True
            )

        if submitted:

            row = query_df(
                """
                SELECT *
                FROM users
                WHERE username=? AND active=1
                """,
                (username.strip(),)
            )

            if (
                not row.empty
                and verify_password(
                    password,
                    row.iloc[0]["password_hash"]
                )
            ):

                st.session_state.user = row.iloc[0].to_dict()
                st.rerun()

            else:

                st.error(
                    "Incorrect username or password, or account is inactive."
                )

        st.markdown("</div>", unsafe_allow_html=True)

    with right:

        st.markdown(
            '<div class="login-card">',
            unsafe_allow_html=True
        )

        st.subheader("👥 Demo Accounts")

        st.success("Administrator")
        st.code("Username: admin\nPassword: Admin123!")

        st.info("Farmer")
        st.code("Username: farmer\nPassword: Farmer123!")

        st.warning("Agricultural Officer")
        st.code("Username: officer\nPassword: Officer123!")

        st.caption(
            "Demo accounts are automatically created on first launch. "
            "Change these passwords before real deployment."
        )

        st.markdown("</div>", unsafe_allow_html=True)


# =====================================================
# AUTHENTICATION CHECK
# =====================================================

if not current_user():

    login_screen()
    st.stop()


user = current_user()


# =====================================================
# SIDEBAR NAVIGATION
# =====================================================

with st.sidebar:

    st.title("🌾 FARM MONITOR")

    st.markdown("---")

    st.write("👤 **" + user["full_name"] + "**")

    st.caption("Role: " + user["role"])

    st.divider()

    pages = [
        "Dashboard",
        "Farm Information",
        "Production Expenses",
        "Harvest Records",
        "Product Sales",
        "Profit & Loss Reports"
    ]

    if user["role"] == "Administrator":
        pages.append("User Management")

    page = st.radio(
        "📌 NAVIGATION",
        pages
    )

    st.divider()

    if st.button(
        "🚪 Sign Out",
        use_container_width=True
    ):

        st.session_state.user = None
        st.rerun()

    st.caption("🌱 Growing better farms with better information.")


# =====================================================
# PAGE HEADER
# =====================================================

st.markdown("""
<style>
.farm-header {
    background: linear-gradient(110deg, #1B5E20, #43A047);
    padding: 30px;
    border-radius: 18px;
    margin-bottom: 25px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.10);
}

.farm-header h1 {
    color: white !important;
    font-size: 32px;
    font-weight: bold;
}

.farm-header p {
    color: #F1F8E9 !important;
    font-size: 16px;
}
</style>
""", unsafe_allow_html=True)



# =====================================================
# DASHBOARD
# =====================================================

if page == "Dashboard":

    where, params = scoped_sql(user)

    expenses = query_df(
        "SELECT COALESCE(SUM(amount),0) total FROM expenses" + where,
        params
    ).iloc[0]["total"]

    sales = query_df(
        "SELECT COALESCE(SUM(quantity*unit_price),0) total FROM sales" + where,
        params
    ).iloc[0]["total"]

    harvest = query_df(
        "SELECT COALESCE(SUM(quantity),0) total FROM harvests" + where,
        params
    ).iloc[0]["total"]

    farm_count = query_df(
        "SELECT COUNT(*) total FROM farms" +
        (" WHERE farmer_id=?" if user["role"] == "Farmer" else ""),
        (user["id"],) if user["role"] == "Farmer" else ()
    ).iloc[0]["total"]

    profit = sales - expenses

    st.subheader("📊 Farm Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🌾 Registered Farms",
        f"{farm_count}"
    )

    c2.metric(
        "💸 Total Expenses",
        f"₱{expenses:,.2f}"
    )

    c3.metric(
        "💰 Total Sales",
        f"₱{sales:,.2f}"
    )

    c4.metric(
        "📈 Estimated Profit / Loss",
        f"₱{profit:,.2f}",
        delta=f"₱{profit:,.2f}"
    )

    st.info(
        "Profit is calculated as recorded sales minus recorded expenses. "
        "It is an estimate based only on entries in this system."
    )

    st.divider()

    exp_df = query_df(
        """
        SELECT category, SUM(amount) AS amount
        FROM expenses
        """ + where + """
        GROUP BY category
        """,
        params
    )

    sale_df = query_df(
        """
        SELECT sale_date,
               SUM(quantity*unit_price) AS income
        FROM sales
        """ + where + """
        GROUP BY sale_date
        ORDER BY sale_date
        """,
        params
    )

    a, b = st.columns(2)

    with a:

        st.subheader("🌱 Expenses by Category")

        if not exp_df.empty:

            st.bar_chart(
                exp_df.set_index("category"),
                color="#4CAF50"
            )

        else:

            st.info("No expense records yet.")

    with b:

        st.subheader("💰 Sales Income Over Time")

        if not sale_df.empty:

            st.line_chart(
                sale_df.set_index("sale_date"),
                color="#F9A825"
            )

        else:

            st.info("No sales records yet.")

    if user["role"] == "Agricultural Officer":

        st.caption(
            "Officer view: Dashboard and reports are read-only."
        )


# =====================================================
# FARM INFORMATION
# =====================================================

elif page == "Farm Information":

    farms = farm_options(user)

    if user["role"] in ("Farmer", "Administrator"):

        st.subheader("➕ Add New Farm")

        with st.form("farm_form"):

            farm_name = st.text_input("Farm Name")

            location = st.text_input("Farm Location")

            size = st.number_input(
                "Farm Size (Hectares)",
                min_value=0.0,
                step=0.1
            )

            crop = st.text_input("Main Crop")

            farmers = (
                query_df(
                    """
                    SELECT id, full_name
                    FROM users
                    WHERE role='Farmer' AND active=1
                    """
                )
                if user["role"] == "Administrator"
                else pd.DataFrame()
            )

            owner_id = user["id"]

            if user["role"] == "Administrator":

                if not farmers.empty:

                    chosen_farmer = st.selectbox(
                        "Assign Farm to Farmer",
                        farmers["full_name"].tolist()
                    )

                    owner_id = int(
                        farmers.loc[
                            farmers["full_name"] == chosen_farmer,
                            "id"
                        ].iloc[0]
                    )

                else:

                    st.warning(
                        "Create a farmer account before adding a farm."
                    )

            if st.form_submit_button(
                "💾 Save Farm",
                use_container_width=True
            ):

                if not farm_name.strip():

                    st.error("Farm name is required.")

                elif (
                    user["role"] == "Administrator"
                    and farmers.empty
                ):

                    st.error("Create a farmer account first.")

                else:

                    execute(
                        """
                        INSERT INTO farms(
                            farmer_id,
                            farm_name,
                            location,
                            size_hectares,
                            crop_type
                        )
                        VALUES(?,?,?,?,?)
                        """,
                        (
                            owner_id,
                            farm_name.strip(),
                            location,
                            size,
                            crop
                        )
                    )

                    st.success("Farm successfully saved!")
                    st.rerun()

    st.divider()

    st.subheader("📋 Registered Farms")

    sql = """
    SELECT f.id,
           f.farm_name,
           u.full_name AS farmer,
           f.location,
           f.size_hectares,
           f.crop_type
    FROM farms f
    JOIN users u ON u.id=f.farmer_id
    """

    if user["role"] == "Farmer":

        data = query_df(
            sql + " WHERE f.farmer_id=? ORDER BY f.id DESC",
            (user["id"],)
        )

    else:

        data = query_df(
            sql + " ORDER BY f.id DESC"
        )

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True
    )


# =====================================================
# PRODUCTION EXPENSES
# =====================================================

elif page == "Production Expenses":

    farms = farm_options(user)

    if user["role"] in ("Farmer", "Administrator"):

        if farms.empty:

            st.warning(
                "Add a farm before recording expenses."
            )

        else:

            st.subheader("💸 Record Production Expense")

            with st.form("expense_form"):

                farm_id = selected_farm_id(farms)

                expense_date = st.date_input(
                    "Expense Date",
                    value=date.today()
                )

                category = st.selectbox(
                    "Expense Category",
                    [
                        "Seeds",
                        "Fertilizers",
                        "Pesticides",
                        "Labor",
                        "Transportation",
                        "Equipment",
                        "Water / Irrigation",
                        "Other"
                    ]
                )

                description = st.text_input(
                    "Description"
                )

                amount = st.number_input(
                    "Amount (PHP)",
                    min_value=0.01,
                    step=100.0
                )

                if st.form_submit_button(
                    "💾 Save Expense",
                    use_container_width=True
                ):

                    owner_id = (
                        user["id"]
                        if user["role"] == "Farmer"
                        else int(
                            query_df(
                                "SELECT farmer_id FROM farms WHERE id=?",
                                (farm_id,)
                            ).iloc[0]["farmer_id"]
                        )
                    )

                    execute(
                        """
                        INSERT INTO expenses(
                            farmer_id,
                            farm_id,
                            expense_date,
                            category,
                            description,
                            amount
                        )
                        VALUES(?,?,?,?,?,?)
                        """,
                        (
                            owner_id,
                            farm_id,
                            str(expense_date),
                            category,
                            description,
                            amount
                        )
                    )

                    st.success("Expense successfully recorded!")
                    st.rerun()

    st.divider()

    st.subheader("📋 Expense History")

    data = query_df(
        """
        SELECT e.expense_date,
               f.farm_name,
               u.full_name AS farmer,
               e.category,
               e.description,
               e.amount
        FROM expenses e
        JOIN farms f ON f.id=e.farm_id
        JOIN users u ON u.id=e.farmer_id
        """ +
        (" WHERE e.farmer_id=?" if user["role"] == "Farmer" else "") +
        " ORDER BY e.expense_date DESC",
        (user["id"],) if user["role"] == "Farmer" else ()
    )

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True
    )

    if not data.empty:

        st.download_button(
            "📥 Download Expenses CSV",
            data.to_csv(index=False).encode("utf-8"),
            "farm_expenses.csv",
            "text/csv"
        )


# =====================================================
# HARVEST RECORDS
# =====================================================

elif page == "Harvest Records":

    farms = farm_options(user)

    if user["role"] in ("Farmer", "Administrator"):

        if farms.empty:

            st.warning(
                "Add a farm before recording harvest."
            )

        else:

            st.subheader("🌾 Record Harvest")

            with st.form("harvest_form"):

                farm_id = selected_farm_id(farms)

                harvest_date = st.date_input(
                    "Harvest Date",
                    value=date.today()
                )

                quantity = st.number_input(
                    "Quantity Harvested",
                    min_value=0.01,
                    step=1.0
                )

                unit = st.selectbox(
                    "Measurement Unit",
                    ["kg", "sacks", "tons", "crates", "pieces"]
                )

                notes = st.text_input("Notes")

                if st.form_submit_button(
                    "💾 Save Harvest",
                    use_container_width=True
                ):

                    owner_id = (
                        user["id"]
                        if user["role"] == "Farmer"
                        else int(
                            query_df(
                                "SELECT farmer_id FROM farms WHERE id=?",
                                (farm_id,)
                            ).iloc[0]["farmer_id"]
                        )
                    )

                    execute(
                        """
                        INSERT INTO harvests(
                            farmer_id,
                            farm_id,
                            harvest_date,
                            quantity,
                            unit,
                            notes
                        )
                        VALUES(?,?,?,?,?,?)
                        """,
                        (
                            owner_id,
                            farm_id,
                            str(harvest_date),
                            quantity,
                            unit,
                            notes
                        )
                    )

                    st.success("Harvest successfully recorded!")
                    st.rerun()

    st.divider()

    st.subheader("📋 Harvest History")

    sql = """
    SELECT h.harvest_date,
           f.farm_name,
           u.full_name AS farmer,
           h.quantity,
           h.unit,
           h.notes
    FROM harvests h
    JOIN farms f ON f.id=h.farm_id
    JOIN users u ON u.id=h.farmer_id
    """

    data = query_df(
        sql +
        (" WHERE h.farmer_id=?" if user["role"] == "Farmer" else "") +
        " ORDER BY h.harvest_date DESC",
        (user["id"],) if user["role"] == "Farmer" else ()
    )

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True
    )


# =====================================================
# PRODUCT SALES
# =====================================================

elif page == "Product Sales":

    farms = farm_options(user)

    if user["role"] in ("Farmer", "Administrator"):

        if farms.empty:

            st.warning(
                "Add a farm before recording sales."
            )

        else:

            st.subheader("🛒 Record Product Sale")

            with st.form("sales_form"):

                farm_id = selected_farm_id(farms)

                sale_date = st.date_input(
                    "Sale Date",
                    value=date.today()
                )

                product = st.text_input(
                    "Product / Crop Sold",
                    value="Rice"
                )

                quantity = st.number_input(
                    "Quantity Sold",
                    min_value=0.01,
                    step=1.0
                )

                unit = st.selectbox(
                    "Measurement Unit",
                    ["kg", "sacks", "tons", "crates", "pieces"]
                )

                unit_price = st.number_input(
                    "Selling Price per Unit (PHP)",
                    min_value=0.01,
                    step=10.0
                )

                buyer = st.text_input(
                    "Buyer (Optional)"
                )

                if st.form_submit_button(
                    "💾 Save Sale",
                    use_container_width=True
                ):

                    owner_id = (
                        user["id"]
                        if user["role"] == "Farmer"
                        else int(
                            query_df(
                                "SELECT farmer_id FROM farms WHERE id=?",
                                (farm_id,)
                            ).iloc[0]["farmer_id"]
                        )
                    )

                    execute(
                        """
                        INSERT INTO sales(
                            farmer_id,
                            farm_id,
                            sale_date,
                            product,
                            quantity,
                            unit,
                            unit_price,
                            buyer
                        )
                        VALUES(?,?,?,?,?,?,?,?)
                        """,
                        (
                            owner_id,
                            farm_id,
                            str(sale_date),
                            product,
                            quantity,
                            unit,
                            unit_price,
                            buyer
                        )
                    )

                    st.success("Sale successfully recorded!")
                    st.rerun()

    st.divider()

    st.subheader("📋 Sales History")

    sql = """
    SELECT s.sale_date,
           f.farm_name,
           u.full_name AS farmer,
           s.product,
           s.quantity,
           s.unit,
           s.unit_price,
           (s.quantity*s.unit_price) AS total_income,
           s.buyer
    FROM sales s
    JOIN farms f ON f.id=s.farm_id
    JOIN users u ON u.id=s.farmer_id
    """

    data = query_df(
        sql +
        (" WHERE s.farmer_id=?" if user["role"] == "Farmer" else "") +
        " ORDER BY s.sale_date DESC",
        (user["id"],) if user["role"] == "Farmer" else ()
    )

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True
    )

    if not data.empty:

        st.download_button(
            "📥 Download Sales CSV",
            data.to_csv(index=False).encode("utf-8"),
            "farm_sales.csv",
            "text/csv"
        )


# =====================================================
# PROFIT AND LOSS REPORTS
# =====================================================

elif page == "Profit & Loss Reports":

    st.subheader("📊 Financial Performance Report")

    st.write(
        "Select a date range to review production costs and income."
    )

    col1, col2 = st.columns(2)

    with col1:

        start = st.date_input(
            "Start Date",
            value=date(date.today().year, 1, 1)
        )

    with col2:

        end = st.date_input(
            "End Date",
            value=date.today()
        )

    if start > end:

        st.error(
            "Start date must be on or before end date."
        )

        st.stop()

    farmer_clause = (
        " AND farmer_id=?"
        if user["role"] == "Farmer"
        else ""
    )

    params = (
        [str(start), str(end)] +
        ([user["id"]] if user["role"] == "Farmer" else [])
    )

    expenses = query_df(
        """
        SELECT COALESCE(SUM(amount),0) total
        FROM expenses
        WHERE expense_date BETWEEN ? AND ?
        """ + farmer_clause,
        params
    ).iloc[0]["total"]

    income = query_df(
        """
        SELECT COALESCE(SUM(quantity*unit_price),0) total
        FROM sales
        WHERE sale_date BETWEEN ? AND ?
        """ + farmer_clause,
        params
    ).iloc[0]["total"]

    profit = income - expenses

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "💸 Production Cost",
        f"₱{expenses:,.2f}"
    )

    c2.metric(
        "💰 Sales Income",
        f"₱{income:,.2f}"
    )

    c3.metric(
        "📈 Estimated Profit / Loss",
        f"₱{profit:,.2f}",
        delta=f"₱{profit:,.2f}"
    )

    st.info(
        "Estimated profit = Sales income − Recorded expenses. "
        "Unsold harvest is not counted as income."
    )

    st.divider()

    exp_detail = query_df(
        """
        SELECT expense_date AS Date,
               category AS Type,
               description AS Details,
               amount AS Amount
        FROM expenses
        WHERE expense_date BETWEEN ? AND ?
        """ + farmer_clause + " ORDER BY expense_date",
        params
    )

    sales_detail = query_df(
        """
        SELECT sale_date AS Date,
               product AS Product,
               quantity AS Quantity,
               unit,
               unit_price AS Unit_Price,
               quantity*unit_price AS Income
        FROM sales
        WHERE sale_date BETWEEN ? AND ?
        """ + farmer_clause + " ORDER BY sale_date",
        params
    )

    st.subheader("💸 Expense Details")

    st.dataframe(
        exp_detail,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("💰 Sales Details")

    st.dataframe(
        sales_detail,
        use_container_width=True,
        hide_index=True
    )

    report = pd.DataFrame([
        {
            "Start Date": start,
            "End Date": end,
            "Production Cost": expenses,
            "Sales Income": income,
            "Estimated Profit/Loss": profit
        }
    ])

    st.download_button(
        "📥 Download Summary Report CSV",
        report.to_csv(index=False).encode("utf-8"),
        "farm_profit_loss_report.csv",
        "text/csv"
    )


# =====================================================
# ADMIN USER MANAGEMENT
# =====================================================

elif page == "User Management" and user["role"] == "Administrator":

    st.subheader("👤 Create User Account")

    with st.form("create_user"):

        full_name = st.text_input(
            "Full Name"
        )

        username = st.text_input(
            "Username"
        )

        password = st.text_input(
            "Temporary Password",
            type="password"
        )

        role = st.selectbox(
            "User Role",
            [
                "Farmer",
                "Agricultural Officer",
                "Administrator"
            ]
        )

        if st.form_submit_button(
            "➕ Create Account",
            use_container_width=True
        ):

            if (
                not full_name.strip()
                or not username.strip()
                or len(password) < 8
            ):

                st.error(
                    "Enter a name and username, and use a password with at least 8 characters."
                )

            else:

                try:

                    execute(
                        """
                        INSERT INTO users(
                            username,
                            password_hash,
                            full_name,
                            role
                        )
                        VALUES(?,?,?,?)
                        """,
                        (
                            username.strip(),
                            hash_password(password),
                            full_name.strip(),
                            role
                        )
                    )

                    st.success(
                        "User account successfully created!"
                    )

                    st.rerun()

                except sqlite3.IntegrityError:

                    st.error(
                        "That username is already in use."
                    )

    st.divider()

    st.subheader("📋 Registered User Accounts")

    users = query_df(
        """
        SELECT id,
               full_name,
               username,
               role,
               active
        FROM users
        ORDER BY id
        """
    )

    st.dataframe(
        users,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Account activation/deactivation and password reset are not included in this prototype."
    )


# =====================================================
# FOOTER
# =====================================================

st.markdown("""
<div class="farm-header">
    <h1>🌾 Farm Production Cost & Profit Monitoring System</h1>
    
    <p>
        Growing better farms through better information.
    </p>
</div>
""", unsafe_allow_html=True)

    left, right = st.columns([1.2, 1])

    with left:

        st.markdown(
            '<div class="login-card">',
            unsafe_allow_html=True
        )
