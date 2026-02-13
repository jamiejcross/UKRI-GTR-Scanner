#!/usr/bin/env python3
"""Re-tag existing CSV with updated TAG_PATTERNS (12 categories).

Reads the CSV, re-applies tag_project() from the updated search_staff.py,
and overwrites the tags column. No API calls needed.
"""

import csv
import sys
import os

# Import from search_staff.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search_staff import tag_project

CSV_PATH = "/Users/jamie.cross/Documents/UKRI-GTR-Scanner/data/uofg_sps_staff_gtr_projects.csv"

def main():
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Loaded {len(rows)} rows", file=sys.stderr)

    for row in rows:
        old_tags = row.get("tags", "")
        new_tags = tag_project(row.get("title", ""), row.get("abstract", ""))
        row["tags"] = new_tags

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Count new tags
    tag_counts = {}
    for row in rows:
        for t in row["tags"].split(";"):
            t = t.strip()
            if t:
                tag_counts[t] = tag_counts.get(t, 0) + 1

    print(f"\nUpdated tags for {len(rows)} projects:", file=sys.stderr)
    for t, c in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"  {c:4d}  {t}", file=sys.stderr)


if __name__ == "__main__":
    main()
