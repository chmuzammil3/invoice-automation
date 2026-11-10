
import sqlite3
from pathlib import Path


# Find the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Create database folder
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database file location
DB_PATH = DATA_DIR / "invoices.db"


def initialize_database():

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier TEXT NOT NULL,
            invoice_number TEXT NOT NULL,
            invoice_date TEXT,
            total REAL,
            source_file TEXT,
            UNIQUE(supplier, invoice_number)
        )
    """)

    connection.commit()
    connection.close()


def check_and_save_invoice(data, source_file):

    supplier = data["Supplier Name"].strip().casefold()
    invoice_number = data["Invoice Number"].strip().casefold()

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO invoices (
                supplier,
                invoice_number,
                invoice_date,
                total,
                source_file
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            supplier,
            invoice_number,
            data["Date"],
            float(data["Total"].replace(",", "").replace("$", "")),
            source_file
        ))

        connection.commit()

        return "Complete"

    except sqlite3.IntegrityError:

        return "Duplicate"

    finally:

        connection.close()
