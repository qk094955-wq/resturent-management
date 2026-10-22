"""Simple Restaurant Management System (Streamlit).

All code lives in this one file. Data is kept in st.session_state and saved to a
local JSON file (restaurant_data.json) that is created automatically at runtime.
NOTE: on Streamlit Community Cloud the local file may be erased on restart.
"""
import json
import os
from datetime import datetime, date

import pandas as pd
import streamlit as st

DATA_FILE = "restaurant_data.json"
CATEGORIES = ["Fast Food", "Pizza", "Burgers", "Drinks", "Desserts", "Traditional Food"]
STATUSES = ["Pending", "Preparing", "Ready", "Completed", "Cancelled"]
ACTIVE = ["Pending", "Preparing", "Ready"]

st.set_page_config(page_title="Restaurant Manager", page_icon="🍽️", layout="wide")

# ---------- Styling ----------
st.markdown(
    """
<style>
html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
div[data-testid="stMetric"] {
    background: #fff7ed; border-left: 5px solid #ea580c;
    padding: 12px 16px; border-radius: 10px;
}
h1, h2, h3 { color: #9a3412; }
@media (max-width: 640px) { div[data-testid="stMetric"] { padding: 8px; } }
</style>
""",
    unsafe_allow_html=True,
)


# ---------- Data layer ----------
def default_db():
    """Starter data so the app is not empty on first run."""
    return {
        "menu": [
            {"id": "M1", "name": "Zinger Burger", "category": "Burgers", "price": 450.0,
             "available": True, "ingredient_id": "I1", "qty_per_item": 1.0},
            {"id": "M2", "name": "Chicken Tikka Pizza", "category": "Pizza", "price": 1200.0,
             "available": True, "ingredient_id": "", "qty_per_item": 0.0},
            {"id": "M3", "name": "Chicken Karahi", "category": "Traditional Food", "price": 1800.0,
             "available": True, "ingredient_id": "", "qty_per_item": 0.0},
            {"id": "M4", "name": "Cold Drink", "category": "Drinks", "price": 120.0,
             "available": True, "ingredient_id": "", "qty_per_item": 0.0},
        ],
        "customers": [],
        "orders": [],
        "tables": [
            {"id": "T1", "capacity": 2, "status": "Available", "order_id": ""},
            {"id": "T2", "capacity": 4, "status": "Available", "order_id": ""},
            {"id": "T3", "capacity": 6, "status": "Available", "order_id": ""},
        ],
        "inventory": [
            {"id": "I1", "name": "Burger Buns", "stock": 50.0, "unit": "pcs", "min_stock": 10.0, "unit_cost": 25.0},
        ],
        "counters": {"M": 4, "C": 0, "O": 0, "T": 3, "I": 1},
        "tax_pct": 0.0,
    }


def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return default_db()


def save_db():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.db, f, indent=2)
    except OSError:
        st.warning("Could not save to disk; data is kept for this session only.")


if "db" not in st.session_state:
    st.session_state.db = load_db()
db = st.session_state.db


def new_id(prefix):
    """Unique ID from a counter, e.g. M5, C3, O12."""
    db["counters"][prefix] += 1
    return f"{prefix}{db['counters'][prefix]}"


def pkr(amount):
    return f"PKR {amount:,.0f}"


def find(collection, rec_id):
    return next((r for r in db[collection] if r["id"] == rec_id), None)


def orders_df():
    rows = []
    for o in db["orders"]:
        rows.append({
            "Order ID": o["id"], "Date": o["created"], "Customer": o["customer_name"],
            "Table": o["table_id"] or "-", "Items": ", ".join(f"{i['name']} x{i['qty']}" for i in o["items"]),
            "Total": o["total"], "Status": o["status"],
        })
    return pd.DataFrame(rows)


def completed_orders():
    return [o for o in db["orders"] if o["status"] == "Completed"]


def csv_button(df, label, filename):
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), filename, "text/csv")


def confirm_delete(key):
    """Returns True only when the user ticks the box and clicks Delete."""
    ok = st.checkbox("I understand this cannot be undone", key=f"chk_{key}")
    return st.button("🗑️ Delete", key=f"del_{key}", disabled=not ok)


# ---------- Order / stock logic ----------
def needed_stock(items):
    """Total ingredient quantity needed for a list of order items."""
    need = {}
    for it in items:
        menu_item = find("menu", it["item_id"])
        if menu_item and menu_item.get("ingredient_id"):
            iid = menu_item["ingredient_id"]
            need[iid] = need.get(iid, 0) + menu_item["qty_per_item"] * it["qty"]
    return need


def set_status(order, new_status):
    """Change status; restore stock once on cancel and free the table."""
    if order["status"] == new_status:
        return
    if new_status == "Cancelled" and order["stock_deducted"]:
        for iid, qty in needed_stock(order["items"]).items():
            ing = find("inventory", iid)
            if ing:
                ing["stock"] += qty
        order["stock_deducted"] = False  # prevents double restore
    order["status"] = new_status
    if new_status in ("Completed", "Cancelled") and order["table_id"]:
        table = find("tables", order["table_id"])
        if table and table["order_id"] == order["id"]:
            table["status"], table["order_id"] = "Available", ""
    save_db()


# ---------- Pages ----------
def page_dashboard():
    st.title("📊 Dashboard")
    done = completed_orders()
    revenue = sum(o["total"] for o in done)
    c = st.columns(3)
    c[0].metric("Total Revenue", pkr(revenue))
    c[1].metric("Total Orders", len(db["orders"]))
    c[2].metric("Menu Items", len(db["menu"]))
    c = st.columns(3)
    c[0].metric("Customers", len(db["customers"]))
    c[1].metric("Pending Orders", sum(o["status"] in ACTIVE for o in db["orders"]))
    c[2].metric("Completed Orders", len(done))

    low = [i for i in db["inventory"] if i["stock"] <= i["min_stock"]]
    if low:
        st.error("⚠️ Low stock: " + ", ".join(f"{i['name']} ({i['stock']:g} {i['unit']})" for i in low))

    if not done:
        st.info("No completed orders yet. Charts will appear once orders are completed.")
    else:
        df = pd.DataFrame([{"Date": pd.to_datetime(o["created"]), "Total": o["total"]} for o in done])
        left, right = st.columns(2)
        left.subheader("Daily Sales")
        left.bar_chart(df.set_index("Date").resample("D")["Total"].sum())
        right.subheader("Monthly Sales")
        right.bar_chart(df.set_index("Date").resample("MS")["Total"].sum())

        sold = {}
        for o in done:
            for i in o["items"]:
                sold[i["name"]] = sold.get(i["name"], 0) + i["qty"]
        st.subheader("Best-Selling Items")
        st.bar_chart(pd.Series(sold).sort_values(ascending=False).head(5))

    st.subheader("Recent Orders")
    df = orders_df()
    if df.empty:
        st.info("No orders yet.")
    else:
        st.dataframe(df.tail(5).iloc[::-1], use_container_width=True, hide_index=True)


def page_menu():
    st.title("🍔 Menu Management")
    tab1, tab2, tab3 = st.tabs(["View", "Add Item", "Edit / Delete"])
    ingredients = {i["id"]: i["name"] for i in db["inventory"]}
    ing_options = [""] + list(ingredients)

    with tab1:
        search = st.text_input("Search by name")
        cat = st.selectbox("Category", ["All"] + CATEGORIES)
        rows = [m for m in db["menu"]
                if search.lower() in m["name"].lower() and (cat == "All" or m["category"] == cat)]
        if not rows:
            st.info("No menu items found.")
        else:
            df = pd.DataFrame(rows)[["id", "name", "category", "price", "available"]]
            df["price"] = df["price"].map(pkr)
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv_button(pd.DataFrame(db["menu"]), "⬇️ Export menu CSV", "menu.csv")

    with tab2:
        with st.form("add_menu", clear_on_submit=True):
            name = st.text_input("Item name")
            category = st.selectbox("Category", CATEGORIES)
            price = st.number_input("Price (PKR)", min_value=0.0, step=10.0)
            available = st.checkbox("Available", value=True)
            ing = st.selectbox("Ingredient used (optional)", ing_options,
                               format_func=lambda x: ingredients.get(x, "None"))
            qty = st.number_input("Ingredient quantity per item", min_value=0.0, step=0.1)
            if st.form_submit_button("Add Item"):
                if not name.strip() or price <= 0:
                    st.error("Enter a name and a price greater than 0.")
                elif any(m["name"].lower() == name.strip().lower() for m in db["menu"]):
                    st.error("An item with this name already exists.")
                else:
                    db["menu"].append({"id": new_id("M"), "name": name.strip(), "category": category,
                                       "price": price, "available": available,
                                       "ingredient_id": ing, "qty_per_item": qty if ing else 0.0})
                    save_db()
                    st.success("Menu item added.")

    with tab3:
        if not db["menu"]:
            st.info("No menu items to edit.")
            return
        mid = st.selectbox("Select item", [m["id"] for m in db["menu"]],
                           format_func=lambda x: f"{x} - {find('menu', x)['name']}")
        m = find("menu", mid)
        name = st.text_input("Name", m["name"], key=f"mn_{mid}")
        category = st.selectbox("Category", CATEGORIES, CATEGORIES.index(m["category"]), key=f"mc_{mid}")
        price = st.number_input("Price (PKR)", min_value=0.0, value=float(m["price"]), step=10.0, key=f"mp_{mid}")
        available = st.checkbox("Available", m["available"], key=f"ma_{mid}")
        cur = m.get("ingredient_id", "")
        ing = st.selectbox("Ingredient", ing_options, ing_options.index(cur) if cur in ing_options else 0,
                           format_func=lambda x: ingredients.get(x, "None"), key=f"mi_{mid}")
        qty = st.number_input("Ingredient qty per item", min_value=0.0, value=float(m.get("qty_per_item", 0)),
                              step=0.1, key=f"mq_{mid}")
        if st.button("💾 Save changes", key=f"ms_{mid}"):
            if not name.strip() or price <= 0:
                st.error("Enter a name and a price greater than 0.")
            else:
                m.update(name=name.strip(), category=category, price=price, available=available,
                         ingredient_id=ing, qty_per_item=qty if ing else 0.0)
                save_db()
                st.success("Item updated.")
        st.divider()
        if confirm_delete(f"menu_{mid}"):
            db["menu"].remove(m)
            save_db()
            st.success("Item deleted.")
            st.rerun()


def page_orders():
    st.title("🧾 Order Management")
    tab1, tab2 = st.tabs(["New Order", "Manage Orders"])

    with tab1:
        available = [m for m in db["menu"] if m["available"]]
        if not available:
            st.info("Add available menu items first.")
            return
        customers = {c["id"]: c["name"] for c in db["customers"]}
        cust = st.selectbox("Customer", ["Walk-in"] + list(customers),
                            format_func=lambda x: customers.get(x, "Walk-in"))
        free_tables = [t["id"] for t in db["tables"] if t["status"] == "Available"]
        table = st.selectbox("Table (optional)", [""] + free_tables, format_func=lambda x: x or "No table")
        chosen = st.multiselect("Items", [m["id"] for m in available],
                                format_func=lambda x: f"{find('menu', x)['name']} - {pkr(find('menu', x)['price'])}")
        items = []
        for mid in chosen:
            m = find("menu", mid)
            q = st.number_input(f"Quantity: {m['name']}", min_value=1, value=1, step=1, key=f"q_{mid}")
            items.append({"item_id": mid, "name": m["name"], "category": m["category"],
                          "price": m["price"], "qty": int(q)})
        col1, col2 = st.columns(2)
        discount = col1.number_input("Discount (PKR)", min_value=0.0, step=10.0)
        tax_pct = col2.number_input("Tax (%)", min_value=0.0, max_value=100.0, value=float(db["tax_pct"]), step=0.5)

        subtotal = sum(i["price"] * i["qty"] for i in items)
        taxable = max(subtotal - discount, 0)
        tax = taxable * tax_pct / 100
        total = taxable + tax
        st.markdown(f"**Subtotal:** {pkr(subtotal)} | **Discount:** {pkr(discount)} | "
                    f"**Tax:** {pkr(tax)} | **Total:** {pkr(total)}")

        if st.button("✅ Place Order", type="primary"):
            need = needed_stock(items)
            short = [find("inventory", k)["name"] for k, v in need.items()
                     if not find("inventory", k) or find("inventory", k)["stock"] < v]
            if not items:
                st.error("Select at least one item.")
            elif discount > subtotal:
                st.error("Discount cannot exceed the subtotal.")
            elif short:
                st.error("Not enough stock for: " + ", ".join(short))
            else:
                for k, v in need.items():  # deduct stock exactly once, here
                    find("inventory", k)["stock"] -= v
                oid = new_id("O")
                db["orders"].append({
                    "id": oid, "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "customer_id": "" if cust == "Walk-in" else cust,
                    "customer_name": customers.get(cust, "Walk-in"),
                    "table_id": table, "items": items, "subtotal": subtotal, "discount": discount,
                    "tax_pct": tax_pct, "tax": tax, "total": total,
                    "status": "Pending", "stock_deducted": True,
                })
                if table:
                    t = find("tables", table)
                    t["status"], t["order_id"] = "Occupied", oid
                db["tax_pct"] = tax_pct
                save_db()
                st.success(f"Order {oid} placed. Total {pkr(total)}.")

    with tab2:
        if not db["orders"]:
            st.info("No orders yet.")
            return
        search = st.text_input("Search by order ID or customer")
        status_f = st.selectbox("Status", ["All"] + STATUSES)
        matches = [o for o in reversed(db["orders"])
                   if (search.lower() in o["id"].lower() or search.lower() in o["customer_name"].lower())
                   and (status_f == "All" or o["status"] == status_f)]
        if not matches:
            st.info("No matching orders.")
            return
        st.dataframe(orders_df().set_index("Order ID").loc[[o["id"] for o in matches]],
                     use_container_width=True)
        oid = st.selectbox("Open order", [o["id"] for o in matches])
        o = find("orders", oid)
        st.markdown(f"### Bill - {o['id']}  \n{o['created']} | {o['customer_name']} | Table: {o['table_id'] or '-'}")
        bill = pd.DataFrame([{"Item": i["name"], "Qty": i["qty"], "Price": pkr(i["price"]),
                              "Amount": pkr(i["price"] * i["qty"])} for i in o["items"]])
        st.table(bill)
        st.write(f"Subtotal: {pkr(o['subtotal'])} | Discount: {pkr(o['discount'])} | "
                 f"Tax ({o['tax_pct']:g}%): {pkr(o['tax'])}")
        st.markdown(f"**Total: {pkr(o['total'])}**")
        new_status = st.selectbox("Update status", STATUSES, STATUSES.index(o["status"]), key=f"st_{oid}")
        if st.button("Update Status", key=f"us_{oid}"):
            if o["status"] in ("Completed", "Cancelled"):
                st.error("Completed or cancelled orders cannot be changed.")
            else:
                set_status(o, new_status)
                st.success("Status updated.")
                st.rerun()


def page_customers():
    st.title("👥 Customer Management")
    tab1, tab2, tab3 = st.tabs(["View", "Register", "Edit / Delete"])

    def spending(cid):
        mine = [o for o in db["orders"] if o["customer_id"] == cid]
        return len(mine), sum(o["total"] for o in mine if o["status"] == "Completed")

    with tab1:
        search = st.text_input("Search by name or phone")
        rows = []
        for c in db["customers"]:
            if search.lower() in c["name"].lower() or search in c["phone"]:
                n, spent = spending(c["id"])
                rows.append({"ID": c["id"], "Name": c["name"], "Phone": c["phone"],
                             "Orders": n, "Total Spent": spent})
        if not rows:
            st.info("No customers found.")
        else:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv_button(df, "⬇️ Export customers CSV", "customers.csv")
            cid = st.selectbox("Order history for", [r["ID"] for r in rows],
                               format_func=lambda x: f"{x} - {find('customers', x)['name']}")
            hist = orders_df()
            hist = hist[hist["Order ID"].isin([o["id"] for o in db["orders"] if o["customer_id"] == cid])]
            st.dataframe(hist, use_container_width=True, hide_index=True) if not hist.empty else st.info("No orders yet.")

    with tab2:
        with st.form("add_cust", clear_on_submit=True):
            name = st.text_input("Name")
            phone = st.text_input("Phone (digits only)")
            if st.form_submit_button("Register"):
                if not name.strip() or not phone.strip().isdigit() or len(phone.strip()) < 10:
                    st.error("Enter a name and a valid phone number (at least 10 digits).")
                elif any(c["phone"] == phone.strip() for c in db["customers"]):
                    st.error("This phone number is already registered.")
                else:
                    db["customers"].append({"id": new_id("C"), "name": name.strip(), "phone": phone.strip()})
                    save_db()
                    st.success("Customer registered.")

    with tab3:
        if not db["customers"]:
            st.info("No customers to edit.")
            return
        cid = st.selectbox("Select customer", [c["id"] for c in db["customers"]], key="ec",
                           format_func=lambda x: f"{x} - {find('customers', x)['name']}")
        c = find("customers", cid)
        name = st.text_input("Name", c["name"], key=f"cn_{cid}")
        phone = st.text_input("Phone", c["phone"], key=f"cp_{cid}")
        if st.button("💾 Save changes", key=f"cs_{cid}"):
            if not name.strip() or not phone.strip().isdigit() or len(phone.strip()) < 10:
                st.error("Enter a name and a valid phone number.")
            else:
                c["name"], c["phone"] = name.strip(), phone.strip()
                save_db()
                st.success("Customer updated.")
        st.divider()
        if confirm_delete(f"cust_{cid}"):
            if spending(cid)[0] > 0:
                st.error("Cannot delete a customer who has orders.")
            else:
                db["customers"].remove(c)
                save_db()
                st.rerun()


def page_tables():
    st.title("🪑 Table Management")
    if db["tables"]:
        rows = [{"Table": t["id"], "Seats": t["capacity"], "Status": t["status"],
                 "Current Order": t["order_id"] or "-"} for t in db["tables"]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No tables yet.")

    tab1, tab2 = st.tabs(["Add Table", "Edit / Delete"])
    with tab1:
        with st.form("add_table", clear_on_submit=True):
            cap = st.number_input("Seating capacity", min_value=1, value=4, step=1)
            if st.form_submit_button("Add Table"):
                db["tables"].append({"id": new_id("T"), "capacity": int(cap), "status": "Available", "order_id": ""})
                save_db()
                st.success("Table added.")
                st.rerun()
    with tab2:
        if not db["tables"]:
            return
        tid = st.selectbox("Select table", [t["id"] for t in db["tables"]])
        t = find("tables", tid)
        cap = st.number_input("Capacity", min_value=1, value=int(t["capacity"]), step=1, key=f"tc_{tid}")
        status = st.selectbox("Status", ["Available", "Occupied"],
                              ["Available", "Occupied"].index(t["status"]), key=f"ts_{tid}")
        if st.button("💾 Save", key=f"tsv_{tid}"):
            active = find("orders", t["order_id"]) if t["order_id"] else None
            if status == "Available" and active and active["status"] in ACTIVE:
                st.error("Complete or cancel the order first; the table is released automatically.")
            else:
                t["capacity"], t["status"] = int(cap), status
                if status == "Available":
                    t["order_id"] = ""
                save_db()
                st.success("Table updated.")
                st.rerun()
        st.divider()
        if confirm_delete(f"table_{tid}"):
            if t["status"] == "Occupied":
                st.error("Cannot delete an occupied table.")
            else:
                db["tables"].remove(t)
                save_db()
                st.rerun()


def page_inventory():
    st.title("📦 Inventory Management")
    low = [i for i in db["inventory"] if i["stock"] <= i["min_stock"]]
    if low:
        st.error("⚠️ Low stock: " + ", ".join(i["name"] for i in low))
    tab1, tab2, tab3 = st.tabs(["View", "Add Ingredient", "Edit / Stock / Delete"])

    with tab1:
        search = st.text_input("Search ingredient")
        only_low = st.checkbox("Show low stock only")
        rows = [i for i in db["inventory"] if search.lower() in i["name"].lower()
                and (not only_low or i["stock"] <= i["min_stock"])]
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No ingredients found.")

    with tab2:
        with st.form("add_ing", clear_on_submit=True):
            name = st.text_input("Ingredient name")
            stock = st.number_input("Stock", min_value=0.0, step=1.0)
            unit = st.text_input("Unit (kg, pcs, litre)", "kg")
            min_stock = st.number_input("Minimum stock", min_value=0.0, step=1.0)
            cost = st.number_input("Unit cost (PKR, optional)", min_value=0.0, step=1.0)
            if st.form_submit_button("Add"):
                if not name.strip() or not unit.strip():
                    st.error("Name and unit are required.")
                else:
                    db["inventory"].append({"id": new_id("I"), "name": name.strip(), "stock": stock,
                                            "unit": unit.strip(), "min_stock": min_stock, "unit_cost": cost})
                    save_db()
                    st.success("Ingredient added.")

    with tab3:
        if not db["inventory"]:
            st.info("No ingredients yet.")
            return
        iid = st.selectbox("Select ingredient", [i["id"] for i in db["inventory"]],
                           format_func=lambda x: f"{x} - {find('inventory', x)['name']}")
        i = find("inventory", iid)
        st.write(f"Current stock: **{i['stock']:g} {i['unit']}**")
        amt = st.number_input("Quantity", min_value=0.0, step=1.0, key=f"ia_{iid}")
        a, b = st.columns(2)
        if a.button("➕ Add stock", key=f"ias_{iid}"):
            i["stock"] += amt
            save_db()
            st.rerun()
        if b.button("➖ Reduce stock", key=f"irs_{iid}"):
            if amt > i["stock"]:
                st.error("Cannot reduce below zero.")
            else:
                i["stock"] -= amt
                save_db()
                st.rerun()
        st.divider()
        name = st.text_input("Name", i["name"], key=f"in_{iid}")
        unit = st.text_input("Unit", i["unit"], key=f"iu_{iid}")
        min_stock = st.number_input("Minimum stock", min_value=0.0, value=float(i["min_stock"]), key=f"im_{iid}")
        cost = st.number_input("Unit cost", min_value=0.0, value=float(i["unit_cost"]), key=f"ic_{iid}")
        if st.button("💾 Save changes", key=f"isv_{iid}"):
            if not name.strip() or not unit.strip():
                st.error("Name and unit are required.")
            else:
                i.update(name=name.strip(), unit=unit.strip(), min_stock=min_stock, unit_cost=cost)
                save_db()
                st.success("Ingredient updated.")
        st.divider()
        if confirm_delete(f"ing_{iid}"):
            if any(m.get("ingredient_id") == iid for m in db["menu"]):
                st.error("This ingredient is used by a menu item. Remove the link first.")
            else:
                db["inventory"].remove(i)
                save_db()
                st.rerun()


def page_reports():
    st.title("📈 Sales & Reports")
    c1, c2 = st.columns(2)
    start = c1.date_input("From", date.today().replace(day=1))
    end = c2.date_input("To", date.today())
    if start > end:
        st.error("Start date must be before end date.")
        return

    done = [o for o in completed_orders() if start <= datetime.strptime(o["created"], "%Y-%m-%d %H:%M:%S").date() <= end]
    # Only completed orders count as sales; cancelled orders are excluded.
    st.metric("Completed-order revenue", pkr(sum(o["total"] for o in done)))
    st.metric("Completed orders", len(done))

    if not done:
        st.info("No completed orders in this date range.")
    else:
        df = pd.DataFrame([{"Date": pd.to_datetime(o["created"]), "Total": o["total"]} for o in done]).set_index("Date")
        daily, weekly, monthly = (df.resample(r)["Total"].sum() for r in ("D", "W", "MS"))
        st.subheader("Revenue Trend (daily)")
        st.line_chart(daily)
        t1, t2 = st.columns(2)
        t1.subheader("Weekly Sales")
        t1.bar_chart(weekly)
        t2.subheader("Monthly Sales")
        t2.bar_chart(monthly)

        sold, by_cat = {}, {}
        for o in done:
            for i in o["items"]:
                sold[i["name"]] = sold.get(i["name"], 0) + i["qty"]
                by_cat[i["category"]] = by_cat.get(i["category"], 0) + i["price"] * i["qty"]
        b1, b2 = st.columns(2)
        b1.subheader("Best-Selling Items")
        b1.bar_chart(pd.Series(sold).sort_values(ascending=False).head(10))
        b2.subheader("Sales by Category")
        b2.bar_chart(pd.Series(by_cat))

        sales_df = daily.reset_index().rename(columns={"Total": "Revenue"})
        csv_button(sales_df, "⬇️ Export daily sales CSV", "sales_report.csv")

    st.subheader("Order Status Distribution")
    in_range = [o for o in db["orders"] if start <= datetime.strptime(o["created"], "%Y-%m-%d %H:%M:%S").date() <= end]
    if in_range:
        st.bar_chart(pd.Series([o["status"] for o in in_range]).value_counts())
    else:
        st.info("No orders in this date range.")
    if db["orders"]:
        csv_button(orders_df(), "⬇️ Export all orders CSV", "orders.csv")


def page_about():
    st.title("ℹ️ About & Help")
    st.markdown(
        """
**Restaurant Management System** - a simple Streamlit project.

**How to use**
1. Add ingredients in *Inventory*, then menu items in *Menu* (optionally link an ingredient).
2. Register customers and create tables.
3. Create an order, then update its status (Pending → Preparing → Ready → Completed).
4. View sales in *Dashboard* and *Reports*; export CSV files.

**Good to know**
- Stock is deducted when an order is placed, and restored if it is cancelled.
- Tables are released automatically when an order is completed or cancelled.
- Only *Completed* orders count as revenue.
- Data is saved to a local JSON file, which may be erased when Streamlit Cloud restarts.
"""
    )
    with st.expander("⚠️ Reset all data"):
        if confirm_delete("reset"):
            st.session_state.db = default_db()
            save_db()
            st.rerun()


# ---------- Navigation ----------
PAGES = {
    "📊 Dashboard": page_dashboard,
    "🍔 Menu": page_menu,
    "🧾 Orders": page_orders,
    "👥 Customers": page_customers,
    "🪑 Tables": page_tables,
    "📦 Inventory": page_inventory,
    "📈 Reports": page_reports,
    "ℹ️ About": page_about,
}
st.sidebar.title("🍽️ Restaurant Manager")
choice = st.sidebar.radio("Navigate", list(PAGES))
PAGES[choice]()
