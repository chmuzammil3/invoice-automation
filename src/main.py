import csv
from pathlib import Path
import pdfplumber
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

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
    
# ==================================
# EXCEL REPORT GENERATION
# ==================================

# Create a new Excel workbook
workbook = Workbook()

# First worksheet: Invoice Records
sheet = workbook.active
sheet.title = "Invoice Records"

# Define Excel column headings
excel_headers = [
    "Source File",
    "Invoice Number",
    "Date",
    "Supplier Name",
    "Total",
    "Status"
]

sheet.append(excel_headers)

# Add invoice records
for row in invoice_rows:

    excel_row = [
        row["Source File"],
        row["Invoice Number"],
        row["Date"],
        row["Supplier Name"],
        float(row["Total"].replace(",", "").replace("$", ""))
        if row["Total"] else None,
        row["Status"]
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


# Format the Total column as currency
for cell in sheet["E"][1:]:
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

# Count invoice statuses
total_invoices = len(invoice_rows)

complete_count = sum(
    1 for row in invoice_rows
    if row["Status"] == "Complete"
)

duplicate_count = sum(
    1 for row in invoice_rows
    if row["Status"] == "Duplicate"
)

review_count = sum(
    1 for row in invoice_rows
    if row["Status"].startswith("Needs Review")
)

error_count = sum(
    1 for row in invoice_rows
    if row["Status"] == "Processing Error"
)


# Calculate value of unique, complete invoices
total_value = sum(
    float(row["Total"].replace(",", "").replace("$", ""))
    for row in invoice_rows
    if row["Status"] == "Complete" and row["Total"]
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

summary["B7"].number_format = '$#,##0.00'


# Save Excel workbook
excel_path = OUTPUT_DIR / "invoice_report.xlsx"

workbook.save(excel_path)

print(f"Excel report created: {excel_path}")


print(f"\nCSV file created: {output_path}")
