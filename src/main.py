import csv
from pathlib import Path
import pdfplumber

from extractor import extract_invoice_data

# Project folders
BASE_DIR = Path(__file__).resolve().parent.parent
INVOICE_DIR = BASE_DIR / "invoices"
OUTPUT_DIR = BASE_DIR / "output"

# Create output folder if it does not exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Store all invoice results
invoice_rows = []
seen_invoices = set()

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
            # Normalize supplier and invoice number
            supplier = data.get("Supplier Name", "").strip().casefold()
            invoice_number = data.get("Invoice Number", "").strip().casefold()

            # Create a unique key for this invoice
            invoice_key = (supplier, invoice_number)

            # Check whether this invoice was already processed
            if invoice_key in seen_invoices:
                status = "Duplicate"
            else:
                seen_invoices.add(invoice_key)
                status = "Complete"

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
