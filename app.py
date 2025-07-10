from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_FILE = "dicemint.db"

# --- Ensure DB + Tables Exist ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS balances (
            telegram_id TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id TEXT,
            new_user_id TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# --- Helpers ---
def get_balance(telegram_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT balance FROM balances WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def set_balance(telegram_id, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO balances (telegram_id, balance) VALUES (?, ?)", (telegram_id, amount))
    conn.commit()
    conn.close()

def update_balance(telegram_id, amount):
    current = get_balance(telegram_id)
    new_balance = current + amount
    set_balance(telegram_id, new_balance)

# --- Routes ---
@app.route("/")
def home():
    return "✅ DiceMint Backend (SQLite) is Live!"

@app.route("/get_balance", methods=["POST"])
def get_balance_route():
    data = request.get_json()
    telegram_id = str(data.get("telegram_id"))
    balance = get_balance(telegram_id)
    return jsonify({"balance": balance})

@app.route("/update_balance", methods=["POST"])
def update_balance_route():
    data = request.get_json()
    telegram_id = str(data.get("telegram_id"))
    balance = int(data.get("balance", 0))
    set_balance(telegram_id, balance)
    return jsonify({"success": True, "new_balance": balance})

@app.route("/api/referral", methods=["POST"])
def referral():
    data = request.get_json()
    new_user_id = str(data.get("new_user_id"))
    referrer_id = str(data.get("referrer_id"))

    if new_user_id == referrer_id:
        return jsonify({"status": "error", "message": "Self-referral is not allowed"}), 400

    # Check if new_user already exists
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT balance FROM balances WHERE telegram_id = ?", (new_user_id,))
    if c.fetchone():
        conn.close()
        return jsonify({"status": "skipped", "message": "User already registered"}), 200

    # Insert new user
    c.execute("INSERT INTO balances (telegram_id, balance) VALUES (?, ?)", (new_user_id, 0))
    c.execute("INSERT INTO referrals (referrer_id, new_user_id) VALUES (?, ?)", (referrer_id, new_user_id))

    # Reward referrer
    current_balance = get_balance(referrer_id)
    set_balance(referrer_id, current_balance + 500)

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Referral successful"}), 200

if __name__ == "__main__":
    app.run(debug=True)
