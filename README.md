# resturent-management
# 🍽️ Restaurant Management System

A simple restaurant dashboard built with **Python** and **Streamlit**. It manages menu items, orders, customers, tables, inventory, and sales reports. Suitable as a beginner/university project.

## Key Features
- **Dashboard:** revenue, orders, customers, pending/completed counts, daily and monthly sales, best sellers, recent orders, low-stock alerts (all calculated from real data).
- **Menu:** add, edit, delete, search, filter by category, availability, CSV export.
- **Orders:** multi-item orders, quantities, discount, configurable tax %, unique order ID, timestamp, itemized bill, status updates (Pending / Preparing / Ready / Completed / Cancelled).
- **Customers:** register, search, edit, delete (blocked if they have orders), order history, total spending.
- **Tables:** add/edit, occupied/available, auto-release when an order is completed or cancelled, no double booking.
- **Inventory:** stock add/reduce, minimum threshold, low-stock alerts, link ingredients to menu items; stock is deducted once when an order is placed and restored if it is cancelled.
- **Reports:** date filters, daily/weekly/monthly sales, category sales, status distribution, CSV exports. Only completed orders count as revenue.
- Currency shown in **PKR**.

## Technologies Used
Python 3.9+, Streamlit, pandas (standard-library `json`, `datetime`, `os`).

## Project Structure
```
├── app.py            # entire application
├── requirements.txt  # dependencies
└── README.md         # documentation
```
(At runtime the app creates `restaurant_data.json` to save data. It is not part of the project and should not be committed.)

## Prerequisites
- Python 3.9 or newer
- pip
- Git and a GitHub account (for deployment)

## Installation
```bash
# 1. (Optional) create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt
```

## Run Locally
```bash
streamlit run app.py
```
Open the URL shown in the terminal (usually http://localhost:8501).

## Upload to GitHub
```bash
git init
git add app.py requirements.txt README.md
git commit -m "Restaurant Management System"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

## Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app** → choose your repository.
3. Set the branch to `main` and the main file path to `app.py`.
4. Click **Deploy**. Wait for dependencies to install.

## ⚠️ Data Storage Limitations
- Data lives in Streamlit Session State and is saved to a local JSON file.
- On Streamlit Community Cloud the local filesystem is **not guaranteed to be permanent**. Data can be lost when the app restarts, sleeps, or is redeployed.
- The data file is shared by everyone using the same running app. This is not a multi-user or production database.
- Use the CSV export buttons to back up important data.

## Example Usage
1. Open **Inventory** and add an ingredient (e.g. Burger Buns, 50 pcs).
2. Open **Menu**, add an item and link the ingredient.
3. Register a customer and add a table.
4. Open **Orders → New Order**, pick items and place the order.
5. Under **Manage Orders**, move the status to *Completed*. The table is released and revenue appears on the dashboard.

## Future Improvements
- Real database (SQLite / PostgreSQL / Google Sheets) for permanent storage
- User login and roles (admin, cashier)
- Multiple ingredients per menu item
- Printable PDF receipts
- Order editing after placement
- Profit reports using ingredient costs
