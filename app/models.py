import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "test.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                price INTEGER NOT NULL
            )
        """)
        db.commit()

# Example helper functions
def create_price(price):
    db = get_db()
    db.execute("INSERT INTO test (price) VALUES (?)", (price,))
    db.commit()

def get_all_contacts():
    db = get_db()
    return [dict(row) for row in db.execute("SELECT * FROM test").fetchall()]
