import argparse
import csv
import json
import re
from pathlib import Path
from collections import Counter
from datetime import date


def clean(value):
    return (value or "").strip()


def normalize_title(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def normalize_doi(value):
    value = clean(value).casefold()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    return value.strip()


def parse_list(value):
    value = clean(value)
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    return [x.strip() for x in re.split(r"[;|]", value) if x.strip()]


def main():
    parser = argparse.ArgumentParser(description="Import research papers from CSV")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    with open(args.csv_file, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    taxonomy_path = Path("data/taxonomy.json")
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    known_topics = {
        topic.casefold()
        for domain in taxonomy.get("domains", [])
        for topic in domain.get("topics", [])
    }

    papers = []
    skipped = Counter()
    duplicates = 0
    unknown_countries = Counter()
    unknown_topics = Counter()
    seen_dois = set()
    seen_titles = set()

    aliases = {
        "paper_id": "id",
        "title": "title",
        "abstract": "abstract",
        "country": "affiliation_country",
        "year": "year",
        "date": "date",
        "doi": "doi",
        "organizations": "institutions",
        "topics": "topics",
        "methods": "methods",
    }

    for row in rows:
        title = clean(row.get("title"))
        abstract = clean(row.get("abstract"))

        if not abstract:
            skipped["no abstract"] += 1
            continue
        if not title:
            skipped["no title"] += 1
            continue

        doi = normalize_doi(row.get("doi"))
        title_key = normalize_title(title)

        if (doi and doi in seen_dois) or (title_key and title_key in seen_titles):
            duplicates += 1
            continue

        if doi:
            seen_dois.add(doi)
        if title_key:
            seen_titles.add(title_key)

        country = clean(row.get("affiliation_country"))
        country_aliases = {
            "usa": "United States",
            "u.s.": "United States",
            "u.s.a.": "United States",
            "us": "United States",
        }
        if country:
            country = country_aliases.get(country.casefold(), country)
            if country not in {"United States", "India", "Germany"}:
                unknown_countries[country] += 1

        topics = parse_list(row.get("topics"))
        known = []
        for topic in topics:
            if topic.casefold() in known_topics:
                known.append(topic)
            else:
                unknown_topics[topic] += 1
        if unknown_topics:
            pass
        if any(t.casefold() not in known_topics for t in topics):
            known.append("Other topics")

        methods = parse_list(row.get("methods"))
        organizations = parse_list(row.get("institutions"))

        year_text = clean(row.get("year"))
        publication_year = int(year_text) if year_text.isdigit() else None

        publication_date = clean(row.get("date"))
        if not publication_date and publication_year:
            publication_date = f"{publication_year}-01-01"

        paper = {
            "paper_id": clean(row.get("id")) or f"import-{len(papers)+1:05d}",
            "title": title,
            "abstract": abstract,
            "authors": [],
            "publication_date": publication_date or None,
            "publication_year": publication_year,
            "journal": None,
            "conference": None,
            "publisher": None,
            "doi": doi or None,
            "source_url": None,
            "open_access_url": None,
            "country": country or None,
            "organizations": organizations,
            "citation_count": None,
            "reference_count": None,
            "research_type": None,
            "derived": {
                "topics": known,
                "subtopics": [],
                "missions": [],
                "spacecraft": [],
                "technologies": [],
                "methods": methods,
                "entities": [],
                "keywords": [],
                "embedding_reference": None,
            },
            "is_synthetic": False,
        }
        papers.append(paper)

    report = {
        "rows_in": len(rows),
        "papers_out": len(papers),
        "skipped": dict(skipped),
        "duplicates_removed": duplicates,
        "columns_used": aliases,
        "countries_without_iso_code": dict(unknown_countries),
        "topics_outside_taxonomy": dict(unknown_topics),
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.dry_run:
        print("Dry run: nothing written.")
        return

    if not args.out:
        parser.error("Use --out FOLDER to save imported papers.")

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "papers.json").write_text(
        json.dumps(papers, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved {len(papers)} papers to {args.out / 'papers.json'}")


if __name__ == "__main__":
    main()
