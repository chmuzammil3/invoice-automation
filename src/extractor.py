
import re


def extract_invoice_data(invoice_text):

    text = invoice_text.strip()

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    invoice_data = {
        "Invoice Number": "",
        "Date": "",
        "Supplier Name": "",
        "Total": ""
    }

    # Extract supplier name
    for line in lines:
        if line.upper() not in ["INVOICE", "TAX INVOICE"]:
            invoice_data["Supplier Name"] = line
            break

    # Extract invoice number
    number_patterns = [
        r"(?:Invoice\s*(?:Number|No\.?|#|ID)|Inv\.?\s*(?:No\.?|#))\s*:?\s*([A-Z0-9/-]*\d[A-Z0-9/-]*)"
    ]

    for pattern in number_patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            value = match.group(1)

            if value.upper() not in ["ISSUED", "DATE"]:
                invoice_data["Invoice Number"] = value
                break

    # Special handling for table-style invoice
    if not invoice_data["Invoice Number"]:

        match = re.search(
            r"Invoice ID\s+Issued\s+([A-Z0-9/-]+)\s+"
            r"(\w+\s+\d{1,2},?\s+\d{4})",
            text,
            re.IGNORECASE
        )

        if match:
            invoice_data["Invoice Number"] = match.group(1)

    # Extract date
    date_pattern = (
        r"(?:Invoice\s+Date|Date|Issued)\s*:?\s*"
        r"(\d{4}-\d{2}-\d{2}|"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
        r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})"
    )

    date_match = re.search(date_pattern, text, re.IGNORECASE)

    if date_match:
        invoice_data["Date"] = date_match.group(1)

    else:
        # Handle date appearing after the invoice number in a table
        match = re.search(
            r"Invoice ID\s+Issued\s+[A-Z0-9/-]+\s+"
            r"(\w+\s+\d{1,2},?\s+\d{4})",
            text,
            re.IGNORECASE
        )

        if match:
            invoice_data["Date"] = match.group(1)

    # Extract total
    total_pattern = (
        r"(?:Grand\s+Total|Amount\s+Due|(?<!Sub)\bTotal\b)"
        r"\s*:?\s*(?:USD\s*)?[$€£]?\s*"
        r"([\d,]+(?:\.\d{1,2})?)"
    )

    total_match = re.search(total_pattern, text, re.IGNORECASE)

    if total_match:
        invoice_data["Total"] = total_match.group(1)

    return invoice_data
