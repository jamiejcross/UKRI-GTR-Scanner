#!/usr/bin/env python3
"""Fill in missing grant_offer and lead_org values by re-fetching from GTR API.

Reads the existing CSV, identifies rows with missing data, fetches the
FUND and LEAD_ORG endpoints with retry/backoff, and rewrites the CSV.
"""

import httpx
import csv
import time
import sys
import datetime

GTR_API = "https://gtr.ukri.org/gtr/api"
HEADERS = {"Accept": "application/json", "User-Agent": "ukri-gtr-scanner/1.0"}
CSV_PATH = "/Users/jamie.cross/Documents/UKRI-GTR-Scanner/data/uofg_sps_staff_gtr_projects.csv"


def fetch_with_retry(client, url, max_retries=5):
    """Fetch URL with exponential backoff on 429 errors."""
    for attempt in range(max_retries):
        try:
            r = client.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"    Rate limited, waiting {wait}s... (attempt {attempt+1})", file=sys.stderr)
                time.sleep(wait)
                continue
            if r.status_code == 404:
                # Resource doesn't exist — not retryable
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"    Rate limited, waiting {wait}s... (attempt {attempt+1})", file=sys.stderr)
                time.sleep(wait)
                continue
            if e.response.status_code == 404:
                return None
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            print(f"    ERROR: {e}", file=sys.stderr)
            return None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            print(f"    ERROR: {e}", file=sys.stderr)
            return None
    return None


def epoch_ms_to_date(val):
    """Convert epoch milliseconds to YYYY-MM-DD string."""
    if val is None:
        return ""
    try:
        if isinstance(val, (int, float)):
            return datetime.datetime.fromtimestamp(val / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        pass
    return ""


def main():
    # Read existing CSV
    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} projects from CSV", file=sys.stderr)

    missing_grant = [r for r in rows if not r.get("grant_offer")]
    missing_org = [r for r in rows if not r.get("lead_org")]
    print(f"Missing grant_offer: {len(missing_grant)}", file=sys.stderr)
    print(f"Missing lead_org: {len(missing_org)}", file=sys.stderr)

    # Collect all project IDs that need enrichment
    needs_work = set()
    for r in rows:
        if not r.get("grant_offer") or not r.get("lead_org"):
            needs_work.add(r["id"])

    if not needs_work:
        print("All fields populated! Nothing to do.", file=sys.stderr)
        return

    print(f"\nRe-enriching {len(needs_work)} projects...", file=sys.stderr)

    org_cache = {}
    fund_cache = {}

    with httpx.Client() as client:
        for idx, row in enumerate(rows):
            if row["id"] not in needs_work:
                continue

            pid = row["id"]
            print(f"  [{idx+1}] {row['title'][:60]}...", file=sys.stderr, flush=True)

            # Fetch the project to get links
            proj = fetch_with_retry(client, f"{GTR_API}/projects/{pid}")
            if not proj:
                print(f"    SKIP: could not fetch project", file=sys.stderr)
                continue

            links = proj.get("links", {}).get("link", [])
            time.sleep(0.3)

            # ── Fix grant_offer ──
            if not row.get("grant_offer"):
                fund_links = [l for l in links if l.get("rel") == "FUND"]
                total_value = 0
                for fl in fund_links:
                    fund_href = fl.get("href", "")
                    fund_id = fund_href.rstrip("/").split("/")[-1] if fund_href else ""
                    if not fund_id:
                        continue

                    if fund_id in fund_cache:
                        total_value += fund_cache[fund_id]
                        continue

                    fund_data = fetch_with_retry(client, f"{GTR_API}/funds/{fund_id}")
                    if fund_data:
                        amount = (fund_data.get("valuePounds") or {}).get("amount", 0)
                        total_value += (amount or 0)
                        fund_cache[fund_id] = amount or 0
                    else:
                        fund_cache[fund_id] = 0
                    time.sleep(0.3)

                if total_value:
                    row["grant_offer"] = f"{total_value:.0f}"
                    print(f"    → grant_offer: £{total_value:,.0f}", file=sys.stderr)

            # ── Fix lead_org ──
            if not row.get("lead_org"):
                lead_org_links = [l for l in links if l.get("rel") == "LEAD_ORG"]
                if lead_org_links:
                    org_href = lead_org_links[0].get("href", "")
                    org_id = org_href.rstrip("/").split("/")[-1] if org_href else ""

                    if org_id:
                        if org_id in org_cache:
                            name = org_cache[org_id]
                        else:
                            org_data = fetch_with_retry(client, f"{GTR_API}/organisations/{org_id}")
                            if org_data:
                                name = org_data.get("name", "")
                                org_cache[org_id] = name
                            else:
                                name = ""
                                org_cache[org_id] = ""
                            time.sleep(0.3)

                        if name:
                            row["lead_org"] = name
                            print(f"    → lead_org: {name}", file=sys.stderr)

    # Rewrite CSV
    fieldnames = list(rows[0].keys())
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    final_grant = sum(1 for r in rows if r.get("grant_offer"))
    final_org = sum(1 for r in rows if r.get("lead_org"))
    print(f"\nDone! grant_offer: {final_grant}/{len(rows)}, lead_org: {final_org}/{len(rows)}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
