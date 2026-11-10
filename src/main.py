import csv
import sqlite3
from pathlib import Path
import pdfplumber
from database import initialize_database, check_and_save_invoice
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from extractor import extract_invoice_data

# Initialize external database functions
initialize_database()

# Project folders
BASE_DIR = Path(__file__).resolve().parent.parent
INVOICE_DIR = BASE_DIR / "invoices"
OUTPUT_DIR = BASE_DIR / "output"
DATABASE_DIR = BASE_DIR / "data"

# Create folders if they do not exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# Define database location
DATABASE_PATH = DATABASE_DIR / "invoices.db"

# Connect to SQLite database
connection = sqlite3.connect(DATABASE_PATH)

# Create table if it does not exist
connection.execute("""
    CREATE TABLE IF NOT EXISTS processed_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_key TEXT NOT NULL,
        invoice_key TEXT NOT NULL,
        supplier_name TEXT,
        invoice_number TEXT,
        source_file TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(supplier_key, invoice_key)
    )
""")
connection.commit()

# Store all invoice results
invoice_rows = []

# Safe helper function to parse currency strings to float
def parse_currency(value_str):
    if not value_str:
        return None
    try:
        clean_str = str(value_str).replace(",", "").replace("$", "").strip()
        return float(clean_str) if clean_str else None
    except ValueError:
        return None

# Process every PDF invoice
for pdf_path in INVOICE_DIR.glob("*.pdf"):
    print(f"\nProcessing: {pdf_path.name}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            invoice_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    invoice_text += text + "\n"

        # Extract invoice fields
        data = extract_invoice_data(invoice_text)
        
        # Check for missing fields
        missing_fields = [
            field for field, value in data.items()
            if not value
        ]

        if missing_fields:
            status = "Needs Review: " + ", ".join(missing_fields)
        else:
            status = check_and_save_invoice(data, pdf_path.name)
       
        # Combine filename, extracted data and status
        row = {
            "Source File": pdf_path.name,
            **data,
            "Status": status
        }
        invoice_rows.append(row)

        print(data)
        print("Status:", status)

    except Exception as error:
        print(f"Error processing {pdf_path.name}: {error}")
        invoice_rows.append({
            "Source File": pdf_path.name,
            "Invoice Number": "",
            "Date": "",
            "Supplier Name": "",
            "Total": "",
            "Status": "Processing Error"
        })

# CSV output location
output_path = OUTPUT_DIR / "invoice_results.csv"

# Define CSV columns
fieldnames = [
    "Source File",
    "Invoice Number",
    "Date",
    "Supplier Name",
    "Total",
    "Status"
]

# Write invoice results into CSV
with output_path.open("w", newline="", encoding="utf-8-sig") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(invoice_rows)
    
print(f"\nCSV file created: {output_path}")

# ==================================
# EXCEL REPORT GENERATION
# ==================================

# Create a new Excel workbook
workbook = Workbook()

# First worksheet: Invoice Records
sheet = workbook.active
sheet.title = "Invoice Records"

sheet.append(fieldnames)

# Add invoice records
for row in invoice_rows:
    excel_row = [
        row.get("Source File", ""),
        row.get("Invoice Number", ""),
        row.get("Date", ""),
        row.get("Supplier Name", ""),
        parse_currency(row.get("Total")),
        row.get("Status", "")
    ]
    sheet.append(excel_row)

# Format the header row
for cell in sheet[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill(
        start_color="1F4E78",
        end_color="1F4E78",
        fill_type="solid"
    )
    cell.alignment = Alignment(horizontal="center")

# Format the Total column as currency (skipping row 1 header)
for row_idx in range(2, sheet.max_row + 1):
    cell = sheet.cell(row=row_idx, column=5)
    if cell.value is not None:
        cell.number_format = '$#,##0.00'

# Adjust column widths
column_widths = {
    "A": 35,
    "B": 22,
    "C": 20,
    "D": 30,
    "E": 15,
    "F": 25
}

for column, width in column_widths.items():
    sheet.column_dimensions[column].width = width

# Second worksheet: Summary
summary = workbook.create_sheet("Summary")

# Count invoice statuses safely using dict.get() defaults
total_invoices = len(invoice_rows)
complete_count = sum(1 for r in invoice_rows if r.get("Status") == "Complete")
duplicate_count = sum(1 for r in invoice_rows if r.get("Status") == "Duplicate")
review_count = sum(1 for r in invoice_rows if str(r.get("Status", "")).startswith("Needs Review"))
error_count = sum(1 for r in invoice_rows if r.get("Status") == "Processing Error")

# Calculate value of unique, complete invoices safely
total_value = sum(
    parse_currency(r.get("Total")) or 0.0
    for r in invoice_rows
    if r.get("Status") == "Complete"
)

# Write summary data
summary.append(["Metric", "Value"])
summary.append(["Total Invoices", total_invoices])
summary.append(["Complete Invoices", complete_count])
summary.append(["Duplicate Invoices", duplicate_count])
summary.append(["Needs Review", review_count])
summary.append(["Processing Errors", error_count])
summary.append(["Unique Invoice Value", total_value])

# Format summary headings
for cell in summary[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill(
        start_color="1F4E78",
        end_color="1F4E78",
        fill_type="solid"
    )

summary.column_dimensions["A"].width = 30
summary.column_dimensions["B"].width = 20

# Format summary total metric as currency safely
summary["B7"].number_format = '$#,##0.00'

# Save Excel workbook
excel_path = OUTPUT_DIR / "invoice_report.xlsx"
workbook.save(excel_path)

print(f"Excel report created: {excel_path}")
connection.close()
