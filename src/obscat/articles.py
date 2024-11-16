import fitz  # PyMuPDF
import argparse


def extract_pdf_metadata(pdf_path):
    # Open the PDF file
    doc = fitz.open(pdf_path)

    # Try to get metadata if available
    metadata = doc.metadata
    title = metadata.get("title", "No title found")
    authors = metadata.get("author", "No author found")

    # Display the title and authors
    print("Title:", title)
    print("Authors:", authors)


def extract_title_from_text(pdf_path):
    # Open the PDF file
    doc = fitz.open(pdf_path)

    # Extract text from the first page
    first_page_text = doc[0].get_text("text")

    # Split the text into lines
    lines = first_page_text.splitlines()

    # Attempt to identify the title
    # Assuming the title is the first non-empty line with a certain length constraint
    title = None
    for line in lines:
        if (
            line.strip() and 10 < len(line) < 100
        ):  # Adjust length constraints if necessary
            title = line.strip()
            break

    # Display the title or fallback message
    if title:
        print("Title:", title)
    else:
        print("Title could not be determined from the text.")


def add():
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description="Extract title and authors from a PDF file."
    )
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file")

    # Parse the arguments
    args = parser.parse_args()

    # Call the extract_pdf_metadata function with the provided pdf_path
    extract_pdf_metadata(args.pdf_path)
    extract_title_from_text(args.pdf_path)


if __name__ == "__main__":
    add()
