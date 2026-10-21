"""Command line interface: ``obscat <command>``."""

import argparse
import sys
from pathlib import Path

from pybtex.exceptions import PybtexError

from obscat import ObscatError, __version__
from obscat.articles import add_article
from obscat.catalogue import BASE_FILE, build_catalogue, load_entries
from obscat.config import config_path, load_config, save_config
from obscat.images import DEFAULT_DPI, remove_frontpages, render_collages, save_collage
from obscat.layout import Layout
from obscat.pdfs import move_pdfs


def _add_path_options(parser, bib=True, articles=True, pdfs=True):
    if bib:
        parser.add_argument(
            "-b", "--bib", type=Path, help="BibTeX file (default: from config)"
        )
    if articles:
        parser.add_argument(
            "-a",
            "--articles",
            type=Path,
            help="Articles folder in the vault (default: from config)",
        )
    if pdfs:
        parser.add_argument(
            "-p",
            "--pdfs",
            type=Path,
            help="PDF folder outside the vault (default: from config, if set)",
        )


def _resolve(parser, value, configured, flag):
    path = value or configured
    if path is None:
        parser.error(
            f"{flag} is required; pass it or set it with `obscat config {flag} PATH`"
        )
    return Path(path).expanduser()


def _pdf_dir(args, config):
    """The PDF folder outside the vault, or ``None`` to keep PDFs in the vault."""
    path = args.pdfs or config["pdf_folder_path"]
    return Path(path).expanduser() if path else None


def _cmd_config(args, config, parser):
    if args.bib or args.articles or args.pdfs:
        save_config(
            args.config,
            bib_file_path=args.bib,
            article_folder_path=args.articles,
            pdf_folder_path=args.pdfs,
        )
        config = load_config(args.config)
    print(f"config file:     {config_path(args.config)}")
    print(f"bib file:        {config['bib_file_path']}")
    print(f"articles folder: {config['article_folder_path']}")
    print(f"PDF folder:      {config['pdf_folder_path'] or '(in the vault)'}")


def _cmd_build(args, config, parser):
    bib = _resolve(parser, args.bib, config["bib_file_path"], "--bib")
    articles = _resolve(
        parser, args.articles, config["article_folder_path"], "--articles"
    )
    entries, missing = build_catalogue(
        bib, articles, args.full_path, _pdf_dir(args, config)
    )
    print(f"Wrote {len(entries)} notes to {articles}")
    if missing:
        print(f"{len(missing)} articles have no PDF, see {BASE_FILE}")


def _cmd_images(args, config, parser):
    articles = _resolve(
        parser, args.articles, config["article_folder_path"], "--articles"
    )
    if not articles.is_dir():
        raise ObscatError(f"Articles folder {articles} does not exist")
    layout = Layout(articles, _pdf_dir(args, config))
    rendered, failed = render_collages(layout, args.overwrite, args.dpi)
    print(f"Rendered {len(rendered)} previews")
    if removed := remove_frontpages(layout):
        print(f"Removed {removed} unused front page images")
    return 1 if failed else 0


def _cmd_move_pdfs(args, config, parser):
    bib = _resolve(parser, args.bib, config["bib_file_path"], "--bib")
    articles = _resolve(
        parser, args.articles, config["article_folder_path"], "--articles"
    )
    pdf_dir = _resolve(parser, args.pdfs, config["pdf_folder_path"], "--pdfs")
    moved, skipped = move_pdfs(articles, pdf_dir, keys=load_entries(bib))
    print(f"Moved {len(moved)} PDFs to {pdf_dir}")
    build_catalogue(bib, articles, pdf_dir=pdf_dir)
    return 1 if skipped else 0


def _cmd_add(args, config, parser):
    bib = _resolve(parser, args.bib, config["bib_file_path"], "--bib")
    articles = _resolve(
        parser, args.articles, config["article_folder_path"], "--articles"
    )

    bibtex = None
    if args.bibtex == "-":
        bibtex = sys.stdin.read()
    elif args.bibtex:
        bibtex = Path(args.bibtex).read_text(encoding="utf-8")

    key = add_article(
        args.pdf,
        bib,
        articles,
        bibtex=bibtex,
        doi=args.doi,
        arxiv=args.arxiv,
        key=args.key,
        move=args.move,
        pdf_dir=_pdf_dir(args, config),
    )
    print(f"Added {key} to {bib}")

    if not args.no_build:
        layout = Layout(articles, _pdf_dir(args, config))
        build_catalogue(bib, articles, pdf_dir=layout.pdf_dir)
        save_collage(layout.pdf(key), layout.collage(key))
        print(f"Updated the catalogue in {articles}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="obscat",
        description="Generate an article catalogue for Obsidian from your .bib file.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help=f"Config file (default: $OBSCAT_CONFIG or {config_path()})",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    config = commands.add_parser(
        "config", help="Show or set the .bib file, articles folder and PDF folder"
    )
    _add_path_options(config)
    config.set_defaults(func=_cmd_config)

    build = commands.add_parser(
        "build", help="Create or update the notes for all articles in the .bib file"
    )
    _add_path_options(build)
    build.add_argument(
        "--full-path", action="store_true", help="Use full paths in markdown links"
    )
    build.set_defaults(func=_cmd_build)

    images = commands.add_parser("images", help="Render the preview of every PDF")
    _add_path_options(images, bib=False)
    images.add_argument(
        "--overwrite", action="store_true", help="Re-render existing images"
    )
    images.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Resolution (default: {DEFAULT_DPI})",
    )
    images.set_defaults(func=_cmd_images)

    move = commands.add_parser(
        "move-pdfs",
        help="Move the PDFs from the vault to the PDF folder",
        description=(
            "Move <articles>/<key>/<key>.pdf to <pdfs>/<key>.pdf, replace the "
            "embedded PDF in each note by a link and update the notes."
        ),
    )
    _add_path_options(move)
    move.set_defaults(func=_cmd_move_pdfs)

    add = commands.add_parser(
        "add",
        help="Add a PDF: fetch its BibTeX entry, store it and update the catalogue",
        description=(
            "Add a PDF to the catalogue. The BibTeX entry is read from --bibtex, "
            "downloaded for --doi/--arxiv, or downloaded for a DOI or arXiv id "
            "found in the PDF."
        ),
    )
    add.add_argument("pdf", type=Path, help="The PDF to add")
    _add_path_options(add)
    source = add.add_mutually_exclusive_group()
    source.add_argument("--doi", help="DOI of the article")
    source.add_argument("--arxiv", help="arXiv id of the article, e.g. 2101.00001")
    source.add_argument(
        "--bibtex", metavar="FILE", help="File with the BibTeX entry ('-' for stdin)"
    )
    add.add_argument("--key", help="Citation key to use instead of the fetched one")
    add.add_argument(
        "--move", action="store_true", help="Move the PDF instead of copying it"
    )
    add.add_argument(
        "--no-build", action="store_true", help="Do not update the catalogue afterwards"
    )
    add.set_defaults(func=_cmd_add)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        return args.func(args, config, parser) or 0
    except (ObscatError, PybtexError) as error:
        print(f"obscat: error: {error}", file=sys.stderr)
        return 1
