import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("database/invoices.db")

def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Customers Table
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, contact TEXT, 
        address TEXT, city TEXT, state TEXT, pincode TEXT, 
        phone TEXT, email TEXT, gst TEXT)''')
    
    # Products Table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, isbn TEXT, 
        author TEXT, publication TEXT, mrp REAL)''')
    
    # Documents Master Table
    c.execute('''CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY, doc_type TEXT, date TEXT, 
        customer_name TEXT, total_amount REAL, file_path TEXT)''')
    
    # Settings/Sequences Table
    c.execute('''CREATE TABLE IF NOT EXISTS sequences (
        doc_type TEXT PRIMARY KEY, current_val INTEGER)''')
    
    # Init default sequences
    c.executemany("INSERT OR IGNORE INTO sequences VALUES (?, ?)", 
                  [('Invoice', 10120), ('Proforma', 5001), ('Quotation', 7001)])
    conn.commit()
    conn.close()

def get_next_sequence(doc_type):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT current_val FROM sequences WHERE doc_type=?", (doc_type,))
    val = c.fetchone()[0]
    conn.close()
    return val

def increment_sequence(doc_type):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sequences SET current_val = current_val + 1 WHERE doc_type=?", (doc_type,))
    conn.commit()
    conn.close()

def save_document(doc_id, doc_type, date, customer, amount, path):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)", 
              (doc_id, doc_type, date, customer, amount, path))
    conn.commit()
    conn.close()

def load_table(table_name):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

# --- NEW: Edit & Delete Functions ---
def update_customer(customer_id, name, contact, address, city, state, pincode, phone, email, gst):
    conn = get_connection()
    conn.execute('''UPDATE customers SET 
                    name=?, contact=?, address=?, city=?, state=?, pincode=?, phone=?, email=?, gst=? 
                    WHERE id=?''', 
                 (name, contact, address, city, state, pincode, phone, email, gst, customer_id))
    conn.commit()
    conn.close()

def delete_customer(customer_id):
    conn = get_connection()
    conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
    conn.commit()
    conn.close()
