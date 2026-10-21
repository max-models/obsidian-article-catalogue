# obsidian-article-catalogue

Generate an article catalogue for [Obsidian](https://obsidian.md) from your `.bib` file.

For every article in the bibliography you get a note `@<citekey>.md` with the
metadata as [properties](https://obsidian.md/help/properties) (title, authors,
year, journal, DOI, ...), an embedded preview of the first pages, the PDF and the
BibTeX entry. Write your own notes directly in it: rebuilding only updates the
properties. An [Obsidian Base](https://obsidian.md/help/bases) gives sortable
tables of all articles and of the articles you don't have the PDF for yet.

## Installation

```
pip install git+https://github.com/max-models/obsidian-article-catalogue
```

or, for development:

```
git clone git@github.com:max-models/obsidian-article-catalogue.git
cd obsidian-article-catalogue
pip install -e ".[dev]"
```

## Setup

Tell `obscat` where your bibliography and the articles folder in your vault are.
This only needs to be done once:

```
obscat config -b ~/Obsidian/my_vault/media/bibliography/references.bib \
              -a ~/Obsidian/my_vault/media/articles
```

Run `obscat config` to show the current settings. They are stored in your user
config folder (`obscat --help` shows where); use `--config FILE` or the
`OBSCAT_CONFIG` environment variable to use another file. Every command also
accepts `-b`/`-a` to override the configured paths.

## Usage

```
obscat add paper.pdf        # add a new article
obscat build                # create or update the notes from the .bib file
obscat images               # render preview images for all PDFs
```

### Adding an article

```
obscat add ~/Downloads/paper.pdf
```

This

1. finds the DOI or arXiv id in the PDF and downloads the BibTeX entry
   (from doi.org or arxiv.org),
2. appends the entry to your `.bib` file,
3. copies the PDF to `<articles>/<key>/<key>.pdf`,
4. creates the note and renders the preview images.

If the identifier can't be found automatically, pass it with `--doi 10.1017/...`
or `--arxiv 2101.00001`, or give the entry yourself with `--bibtex entry.bib`
(`--bibtex -` reads it from stdin). Use `--key` to choose a different citation
key, `--move` to move instead of copy the PDF, and `--no-build` to skip step 4.

### Vault layout

```
articles/
├── Articles.base                 # views: all articles, by journal, missing PDF
└── <key>/
    ├── @<key>.md                 # the note for the article
    ├── <key>.pdf                 # the article
    ├── <key>.pdf.jpg             # collage of the first 16 pages
    ├── <key>.pdf_frontpage.jpg   # the first page
    ├── <key>.bib                 # the BibTeX entry
    └── <key>.html                # link to the article online
```

`@article` and `@inproceedings` entries are catalogued, as well as arXiv preprints
(`@misc` with `archivePrefix = {arXiv}`).

### Notes

Link to an article with `[[@key]]`; typing its title also finds it, because the
title is added as an alias. The note body is only written when the note is
created. On every `obscat build` the properties that come from the .bib file
(`title`, `aliases`, `authors`, `year`, `month`, `journal`, `doi`, `url`,
`citekey`, `has_pdf`) are updated, and everything else is kept: the body, your
own properties (e.g. `status`, `tags`) and your own aliases.

Authors are links (`[[Jane Doe]]`), so creating a note for an author lists all
of their papers in its backlinks.

`Articles.base` is only written if it doesn't exist, so you can change its views.

### Upgrading from older versions

Older versions named notes after the title, kept your notes in `<key>_notes.md`
and generated `article_catalogue.md` and `Missing articles.md`. The first
`obscat build` migrates this: the contents and properties of `<key>_notes.md`
are moved into the `## Notes` section of `@<key>.md`, and the old generated
files are deleted. Links elsewhere in your vault to the old title-named notes or
to `<key>_notes` need to be changed to `[[@key]]`.

## Development

```
pytest
ruff check src tests
ruff format src tests
```
