
from pathlib import Path
import pdfplumber

# Find the project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Locate the invoices folder
INVOICE_DIR = BASE_DIR / "invoices"

# Find all PDF files
pdf_files = list(INVOICE_DIR.glob("*.pdf"))

# Process each PDF
for pdf_path in pdf_files:

    print(f"\nProcessing: {pdf_path.name}")

    try:
        with pdfplumber.open(pdf_path) as pdf:

            invoice_text = ""

            for page in pdf.pages:
                text = page.extract_text()

                if text:
                    invoice_text += text + "\n"

        print(invoice_text)

    except Exception as error:
        print(f"Failed to process {pdf_path.name}: {error}")
