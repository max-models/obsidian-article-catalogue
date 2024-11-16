import os
import argparse
from urllib.parse import unquote
import pybtex.database.input.bibtex

from obscat.state import load_state_file

def latextitle2mdtitle(text):
    text = text.replace("\\hspace", " ")
    text = text.replace("0.167em", "")
    text = text.replace("\\textendash", "-")
    text = text.replace("\\textemdash", "-")
    for _str in [
        '"',
        "mathrm",
        "textquotesingle",
        "sum",
        "mathrm",
        "textquotedblleft",
        "textquotedblright",
        "textdollar",
        "textbackslashhbox",
        "lbrace",
        "rbrace",
        "textdollar",
    ]:
        text = text.replace(f"\\{_str}", "")
    for char in "[]{}$^\\":
        text = text.replace(char, "")
    text = text.replace("/", " or ")
    text = text.replace("\\&", " and ")
    print(text)
    if "\\" in text:
        raise ValueError(f"We should remove any slash from the title {text}")

    return text


def clean_tags(tag):
    return (
        tag.replace(",", "")
        .replace(".", "")
        .replace(" ", "")
        .replace("{", "")
        .replace("}", "")
        .replace("(", "")
        .replace(")", "")
        .replace(":", "")
        .replace('\\"u', "ü")
    )


def write_markdown_file(entry_key, entry, output_dir, full_path=False):
    title = entry.fields.get("title", "Unknown Title").replace("{", "").replace("}", "")
    authors = entry.persons.get("author", ["Unknown Author"])
    main_author = clean_tags(str(authors[0]) if authors else "Unknown Author")
    year = clean_tags(entry.fields.get("year", "Unknown Year"))
    month = clean_tags(entry.fields.get("month", "XX"))
    journal = clean_tags(entry.fields.get("journal", "Unknown Journal"))

    tags = [
        f"#Articles/Author/{main_author}",
        f"#Articles/Year/{year}",
        f"#Articles/Journal/{journal}",
    ]

    clean_authors = [clean_tags(str(author)) for author in authors]
    clean_authors_links = "[[" + "]], [[".join(clean_authors) + "]]"
    folder_path = os.path.join(output_dir, entry_key)
    os.makedirs(folder_path, exist_ok=True)

    yaml_header = f"---\ntitle: {title}\nauthor: {main_author}\ndate: {year}-{month}\nbibentry: {entry_key}\n---\n"
    markdown_content = [
        yaml_header,
        " ".join(tags),
        f"\n# {title}\n",
        f"\nAuthors: {clean_authors_links}\n",
        f"\n## Notes\n ![[{folder_path}/{entry_key}_notes.md]]",
        f"\n## Summary\n![[{folder_path}/{entry_key}.pdf.jpg]]",
        f"\n## Full pdf\n![[{folder_path}/{entry_key}.pdf]]",
        f"\n## Citation\n```cpp\n{entry.to_string(bib_format='bibtex')}\n```",
    ]
    if not full_path:
        markdown_content = [
            line.replace(f"{folder_path}/", "") for line in markdown_content
        ]

    md_filename = f"{latextitle2mdtitle(title)}.md"
    md_filepath = os.path.join(folder_path, md_filename)
    with open(md_filepath, "w") as f:
        f.writelines(markdown_content)


def write_missing_articles(missing_articles, output_dir):
    missing_articles_file = os.path.join(output_dir, "Missing articles.md")
    with open(missing_articles_file, "w") as f:
        f.write("# Missing articles\n")
        for item in missing_articles:
            f.write(
                f"- [{item['key']}]({item['clean_url']}) | [Folder]({item['folder']})\n",
            )


def write_files(entry_key, entry, missing_articles, output_dir, full_path=False):
    folder_path = os.path.join(output_dir, entry_key)
    os.makedirs(folder_path, exist_ok=True)

    url = entry.fields.get("url", "Unknown URL")
    clean_url = unquote(url).replace("\\%2", "/").replace("\\", "")

    write_markdown_file(entry_key, entry, output_dir, full_path)

    html_file_path = os.path.join(folder_path, f"{entry_key}.html")
    if not os.path.exists(html_file_path):
        with open(html_file_path, "w") as html_file:
            html_file.write(
                f'<html><body><a href="{clean_url}">Link to Resource</a></body></html>\n',
            )

    # Check for missing PDF
    pdf_path = os.path.join(folder_path, f"{entry_key}.pdf")
    if not os.path.exists(pdf_path):
        missing_articles.append(
            {"key": entry_key, "clean_url": clean_url, "folder": folder_path},
        )

    # Write BibTeX entry only if it doesn't exist
    bib_file_path = os.path.join(folder_path, f"{entry_key}.bib")
    if not os.path.exists(bib_file_path):
        with open(bib_file_path, "w") as bib_file:
            entry_text = f"@{entry.type}{{{entry_key},\n"
            for field, value in entry.fields.items():
                entry_text += f"  {field} = {{{value}}},\n"
            entry_text += "}\n"
            bib_file.write(entry_text)


def write_article_md(entries, output_dir, full_path=False):
    article_md_file = os.path.join(output_dir, "article_catalogue.md")
    with open(article_md_file, "w") as md_file:
        md_file.write("| Article Name | First Author | Year | Journal |\n")
        md_file.write("|--------------|--------------|------|---------|\n")
        for entry_key, entry in entries.items():
            title = (
                entry.fields.get("title", "Unknown Title")
                .replace("{", "")
                .replace("}", "")
            )
            authors = entry.persons.get("author", ["Unknown Author"])
            main_author = str(authors[0]) if authors else "Unknown Author"
            year = entry.fields.get("year", "Unknown Year")
            journal = entry.fields.get("journal", "Unknown Journal")

            md_filename = f"{latextitle2mdtitle(title)}.md"
            if full_path:
                md_link = (
                    f"[{title}]({os.path.join(output_dir, entry_key, md_filename)})"
                )
            else:
                md_link = f"[[{md_filename}]]"
            md_file.write(f"| {md_link} | {main_author} | {year} | {journal} |\n")


def main():
    state_file = load_state_file()
    article_folder_path = state_file['article_folder_path']
    bib_file_path = state_file['bib_file_path']
    
    parser = argparse.ArgumentParser(
        description="Process BibTeX files and generate markdown files.",
    )
    parser.add_argument(
        "-i",
        "--input",
        required=False if article_folder_path else True,
        default=bib_file_path,
        help="Input BibTeX file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False if article_folder_path else True,
        default=article_folder_path,
        help="Output directory.",
    )
    parser.add_argument(
        "--full-path",
        action="store_true",
        help="Use full paths in markdown links.",
    )
    args = parser.parse_args()

    input_bib_file = args.input
    output_dir = args.output
    full_path = args.full_path

    if not os.path.isfile(input_bib_file):
        print(f"Input BibTeX file {input_bib_file} does not exist.")
        exit(1)

    os.makedirs(output_dir, exist_ok=True)

    bib_parser = pybtex.database.input.bibtex.Parser()
    bibdata = bib_parser.parse_file(input_bib_file)

    missing_articles = []
    article_entries = {}

    for entry_key in bibdata.entries:
        entry = bibdata.entries[entry_key]
        if entry.type in ["article", "inproceedings"]:
            write_files(entry_key, entry, missing_articles, output_dir, full_path)
            article_entries[entry_key] = entry

    write_missing_articles(missing_articles, output_dir)
    write_article_md(article_entries, output_dir, full_path)


if __name__ == "__main__":
    main()
