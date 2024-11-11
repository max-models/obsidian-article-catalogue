import os
import glob
import argparse
from PIL import Image
from pdf2image import convert_from_path


def save_frontpage(pdf_path, overwrite=False):
    output_file = f"{pdf_path}_frontpage.jpg"
    if os.path.exists(output_file) and not overwrite:
        print(f"Front page image already exists for {pdf_path}, skipping.")
        return

    print(f"Processing front page of {pdf_path}")
    try:
        image = convert_from_path(pdf_path, first_page=1, last_page=1)[0]
        image.save(output_file)
        print(f"Saved front page image to {output_file}")
    except Exception as e:
        print(f"Error processing front page of {pdf_path}: {e}")


def save_pdf_collage(pdf_path, overwrite=False, images_per_row=4):
    output_file = f"{pdf_path}.jpg"
    if os.path.exists(output_file) and not overwrite:
        print(f"Collage image already exists for {pdf_path}, skipping.")
        return

    print(f"Creating collage image for {pdf_path}")
    try:
        images = convert_from_path(pdf_path)
        if len(images) > 16:
            images = images[:16]

        widths, heights = zip(*(img.size for img in images))

        rows = (len(images) + images_per_row - 1) // images_per_row
        total_width = max(widths) * images_per_row
        total_height = max(heights) * rows

        collage_image = Image.new("RGB", (total_width, total_height), (255, 255, 255))

        y_offset = 0
        for row in range(rows):
            x_offset = 0
            for img in images[row * images_per_row : (row + 1) * images_per_row]:
                collage_image.paste(img, (x_offset, y_offset))
                x_offset += img.size[0]
            y_offset += max(heights)

        collage_image.save(output_file)
        print(f"Saved collage image to {output_file}")
    except Exception as e:
        print(f"Error creating collage for {pdf_path}: {e}")


def process_pdfs(input_dir, overwrite=False):
    pdf_files = [
        y for x in os.walk(input_dir) for y in glob.glob(os.path.join(x[0], "*.pdf"))
    ]
    for pdf_path in pdf_files:
        save_pdf_collage(pdf_path, overwrite)
        save_frontpage(pdf_path, overwrite)


def main():
    parser = argparse.ArgumentParser(description="Convert PDFs to images.")
    parser.add_argument(
        "-i", "--input", required=True, help="Input directory containing PDFs.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing images if they exist.",
    )

    args = parser.parse_args()

    if not os.path.isdir(args.input):
        print(f"Input directory {args.input} does not exist.")
        exit(1)

    process_pdfs(args.input, args.overwrite)
    print("Processing completed.")


if __name__ == "__main__":
    main()
