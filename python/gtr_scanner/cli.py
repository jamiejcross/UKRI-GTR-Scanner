"""Command-line tool for searching the UKRI Gateway to Research."""

import argparse
import asyncio
import csv
import json
import sys
from dataclasses import asdict

from gtr_scanner.client import search_projects, search_all_pages


def main():
    parser = argparse.ArgumentParser(
        description="Search UKRI Gateway to Research for funded projects"
    )
    parser.add_argument("query", help="Search keywords (supports OR/AND, quoted phrases)")
    parser.add_argument("--all-pages", action="store_true", help="Fetch all result pages")
    parser.add_argument("--max-pages", type=int, default=None, help="Max pages to fetch")
    parser.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    parser.add_argument("--format", choices=["table", "csv", "json"], default="table")
    parser.add_argument("--status", help="Filter by project status (e.g. Active, Closed)")
    parser.add_argument("--exclude", nargs="+", help="Exclude projects whose title or abstract contain these keywords")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")

    args = parser.parse_args()

    if args.all_pages:
        projects = asyncio.run(search_all_pages(args.query, max_pages=args.max_pages))
        total = len(projects)
    else:
        result = asyncio.run(search_projects(args.query, page=args.page))
        projects = result.projects
        total = result.total_results

    if args.status:
        status_filter = args.status.lower()
        projects = [p for p in projects if (p.status or "").lower() == status_filter]

    if args.exclude:
        exclude_lower = [kw.lower() for kw in args.exclude]
        projects = [
            p for p in projects
            if not any(
                kw in (p.title or "").lower() or kw in (p.abstract or "").lower()
                for kw in exclude_lower
            )
        ]

    out = open(args.output, "w", newline="") if args.output else sys.stdout

    try:
        if args.format == "json":
            data = [asdict(p) for p in projects]
            json.dump(data, out, indent=2)
            out.write("\n")

        elif args.format == "csv":
            if projects:
                fieldnames = list(asdict(projects[0]).keys())
                writer = csv.DictWriter(out, fieldnames=fieldnames)
                writer.writeheader()
                for p in projects:
                    writer.writerow(asdict(p))

        else:  # table
            print(f"Found {total} projects ({len(projects)} on this page):\n", file=out)
            for p in projects:
                value = f"£{p.grant_offer:,.0f}" if p.grant_offer else "N/A"
                print(f"  {p.title}", file=out)
                print(f"    Funder: {p.funder_name or 'N/A'}  |  Grant: {value}", file=out)
                print(f"    Lead Org: {p.lead_org or 'N/A'}", file=out)
                print(f"    Dates: {p.start_date or '?'} → {p.end_date or '?'}", file=out)
                print(file=out)
    finally:
        if args.output:
            out.close()

    if args.output:
        print(f"Wrote {len(projects)} projects to {args.output}")


if __name__ == "__main__":
    main()
