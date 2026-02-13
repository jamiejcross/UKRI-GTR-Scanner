#!/usr/bin/env python3
"""Search GTR for UofG School of Social & Political Sciences staff projects.

Uses the /persons endpoint to find actual PI/Co-I links, then fetches
each linked project. Follows FUND and LEAD_ORG links to get grant values,
dates, and organisation names. Filters to Active + Closed from 2020 onwards.
"""

import httpx
import csv
import datetime
import time
import sys
import re

GTR_API = "https://gtr.ukri.org/gtr/api"
HEADERS = {"Accept": "application/json", "User-Agent": "ukri-gtr-scanner/1.0"}

# Academic staff (Dr/Professor) from the School of Social & Political Sciences
STAFF = [
    ("Lateef", "Akanni"), ("Huseyn", "Aliyev"), ("Katherine", "Allison"), ("Joao", "Almeida"),
    ("Maia", "Almeida-Amir"), ("Luca", "Anceschi"), ("Luke", "Armstrong"), ("Sarah", "Armstrong"),
    ("Maha Rafi", "Atal"), ("Erdem", "Avsar"), ("Les", "Back"), ("Nick", "Bailey"),
    ("Petar", "Bankov"), ("Matt", "Barlow"), ("Susan", "Batchelor"), ("Patrick", "Bayer"),
    ("Silvia", "Behrens"), ("Karen", "Bell"), ("Elisa", "Belle"), ("Karolina", "Benghellab"),
    ("Julie", "Berg"), ("Sara", "Bernard"), ("Richard", "Berry"), ("Ross", "Beveridge"),
    ("Mehdi", "Beyad"), ("Blair", "Biggar"), ("Ellen", "Bishop"), ("Christopher", "Blyth"),
    ("Anna", "Bochorishvili"), ("Oona", "Brooks"), ("Eleanor", "Brown"), ("Richard", "Brunner"),
    ("Louis", "Bujnoch"), ("Christopher", "Bunn"), ("Laura", "Bunt-MacRury"), ("Michele", "Burman"),
    ("Nicola", "Burns"), ("Eamonn", "Butler"), ("Anna", "Calori"), ("Maurizio", "Carbone"),
    ("Christopher", "Carman"), ("Nicole", "Cassie"), ("Charlotte", "Cator"), ("Felicity", "Cawley"),
    ("Stephanie", "Chambers"), ("Ammon", "Cheskin"), ("Ioana Cerasella", "Chis"),
    ("Ionut", "Cioarta"), ("Christopher", "Claassen"), ("Hannah-Louise", "Clark"),
    ("Anna", "Clover"), ("Ellie", "Conway"), ("Vanessa", "Cook"), ("John", "Cox"),
    ("Fiona", "Crawford"), ("Fabiola", "Creed"), ("Rhys", "Crilley"), ("Jamie", "Cross"),
    ("Amy", "Cullen"), ("Jane", "Cullingworth"), ("Karen", "Cuthbert"), ("Alicia", "Davis"),
    ("Sopio", "Davituri"), ("Matt", "Dawson"), ("Lluis", "de Nadal Alsina"),
    ("Anna", "Dekalchuk"), ("Natalie", "Dewison"), ("Sophia", "Dingli"),
    ("Jane", "Duckett"), ("Jane", "Duncan"), ("Alice", "Earley"),
    ("Jo", "Edson Ferrie"), ("Rosemary", "Elliot"), ("Kirstie", "English"),
    ("Benjamin", "Faude"), ("Jeffrey", "Fear"), ("Taras", "Fedirko"),
    ("Anna", "Feigenbaum"), ("Angus", "Ferguson"), ("Adrian", "Florea"),
    ("Emma", "Flynn"), ("Alistair", "Fraser"), ("Michael", "Frazer"),
    ("Yahya", "Gamalaldin"), ("Alan", "Gardner"), ("Anna", "Gawlewicz"),
    ("Michail", "Georgiou"), ("Sergiu", "Gherghina"), ("Ken", "Gibb"),
    ("Robert", "Gibb"), ("Ewan", "Gibbs"), ("Lucrezia", "Gigante"),
    ("Allan", "Gillies"), ("Caitlin", "Gormley"), ("Cindy", "Gray"),
    ("Ian", "Greener"), ("Joe", "Greenwood-Hau"), ("Sotiria", "Grek"),
    ("Craig", "Gurney"), ("Catherine", "Happer"), ("Helen", "Hardman"),
    ("Annette", "Hastings"), ("Jonathan", "Havercroft"), ("Kristin", "Hay"),
    ("Naomi", "Head"), ("Michael", "Heaney"), ("Philipp", "Heinrich"),
    ("Alison", "Heppenstall"), ("Clementine", "Hill OConnor"), ("Dominic", "Hinde"),
    ("Isaac", "Hoff"), ("Andrew", "Hoolachan"), ("Adnan", "Hossain"),
    ("Michael", "Howcroft"), ("Mo", "Hume"), ("Harvey", "Humphrey"),
    ("Benjamin", "Hunter"), ("Salome", "Ietter"), ("Mahnoz", "Illias"),
    ("Richard", "Illingworth"), ("Andy", "Inch"), ("Greti-Iulia", "Ivana"),
    ("Nina", "Ivashinenko"), ("Gareth", "James"), ("Kelly", "Johnson"),
    ("Andrew", "Johnstone"), ("Uisce", "Jordan"), ("Simon", "Joss"),
    ("Andrew", "Judge"), ("Marcin", "Kaczmarski"), ("Amin", "Kamete"),
    ("Georgios", "Karyotis"), ("Anne", "Kerr"), ("Ewan", "Kerr"),
    ("Shamil", "Khairov"), ("Wooseok", "Kim"), ("Nikolas", "Kirby"),
    ("Carl", "Knight"), ("Kelly", "Kollman"), ("Ana Ines", "Langer"),
    ("Scott", "Lavery"), ("Louise", "Lawson"), ("Sam", "Lawton"),
    ("Catherine", "Lefevre"), ("Luning", "Li"), ("Robert", "Lineira"),
    ("Pengyuan", "Liu"), ("Nicola", "Livingstone"), ("Michael", "Loader"),
    ("Cassandra", "Lovelock"), ("Zubeida", "Lowton"), ("Hayes", "Mabweazara"),
    ("Rhys", "Machold"), ("Mhairi", "Mackenzie"), ("Rebecca", "Madgin"),
    ("Alice", "Mah"), ("Diego Maria", "Malara"), ("Laura", "Martin"),
    ("David", "McArthur"), ("Maureen", "McBride"), ("Alison", "McCandlish"),
    ("Gerard", "McCartney"), ("Katharine", "McCrossan"), ("Michelle", "McGachie"),
    ("Rachael", "McLellan"), ("Clare", "McManus"), ("Fergus", "McNeill"),
    ("Jeff", "Meek"), ("Nasar", "Meer"), ("Paula", "Meth"),
    ("Christopher", "Miller"), ("Nughmana", "Mirza"), ("Jenny", "Morrison"),
    ("Ashli", "Mullen"), ("Gareth", "Mulvey"), ("Neil", "Munro"),
    ("Souvik", "Naha"), ("Shalini", "Nair"), ("Anja", "Neundorf"),
    ("Ida", "Norberg"), ("Tinashe", "Nyamunda"), ("Philip", "OBrien"),
    ("Erica", "ONeill"), ("Tunbosun", "Oyedokun"), ("Aykut", "Ozturk"),
    ("Niccole", "Pamphilis"), ("Plamena", "Panayotova"), ("Carolina", "Pantoliano"),
    ("Sergi", "Pardos-Prado"), ("Jonathan", "Parker"), ("Sion", "Parkinson"),
    ("Dominic", "Pasura"), ("Ian", "Paterson"), ("Kirsteen", "Paton"),
    ("Ruth", "Patrick"), ("Serena", "Pattaro"), ("Fred", "Paxton"),
    ("Timothy", "Peace"), ("Charlotte", "Pearson"), ("Stephanie", "Perazzone"),
    ("Jim", "Phillips"), ("Teresa", "Piacentini"), ("Giovanni", "Picker"),
    ("Lucy", "Pickering"), ("Ilona", "Pinter"), ("Joao", "Porto de Albuquerque"),
    ("Federica", "Prina"), ("Rhona", "Ramsay"), ("Corey", "Ranford-Robinson"),
    ("Paul", "Reilly"), ("Bernhard", "Reinsberg"), ("Gerda", "Reith"),
    ("Jude", "Robinson"), ("Neil", "Rollings"), ("Duncan", "Ross"),
    ("Patricia", "Rossini"), ("Cairsti", "Russell"), ("Emma", "Russell"),
    ("Jade", "Saab"), ("Nomatter", "Sande"), ("Jay", "Sarkar"),
    ("Madhu", "Satsangi"), ("Kristina", "Saunders"), ("Leyla", "Sayfutdinova"),
    ("Michael", "Scanlan"), ("Marguerite", "Schinkel"), ("Tilman", "Schwarze"),
    ("Francesca", "Scrinzi"), ("Kenneth", "Searle"), ("Bilge", "Serin"),
    ("Patrick", "Shea"), ("Michael", "Sinclair"), ("Andrew", "Smith"),
    ("Craig", "Smith"), ("David", "Smith"), ("Emiline", "Smith"),
    ("Bob", "Smith"), ("Holly", "Snape"), ("Miriam", "Snellgrove"),
    ("Corina", "Snitar"), ("Ty", "Solomon"), ("Thees", "Spreckelsen"),
    ("Francesca", "Stella"), ("Mark", "Stephens"), ("Alasdair", "Stewart"),
    ("Ellen", "Stewart"), ("Gavin", "Stewart"), ("Joanna", "Stewart"),
    ("Yu", "Sun"), ("Janos Mark", "Szakolczai"), ("Joanna", "Szostek"),
    ("Gerald", "Tambula"), ("Rebecca", "Tapscott"), ("Giuseppe", "Telesca"),
    ("Alexander", "Tertzakian"), ("Linda", "Thomas"), ("Harriet", "Thomson"),
    ("Michael", "Toomey"), ("Mark", "Tranmer"), ("Morag", "Treanor"),
    ("Myrto", "Tsakatika"), ("Lito", "Tsitsou"), ("Judith", "Tsouvalis"),
    ("Daria", "Ukhova"), ("Vladimir", "Unkovski-Korica"), ("Evelyn", "Uribe Navarrete"),
    ("Sean", "Vanatta"), ("Zsuzsanna", "Varga"), ("Jose Rafael", "Verduzco-Torres"),
    ("Satnam", "Virdee"), ("Ariadne", "Vromen"), ("David", "Waite"),
    ("Matthew", "Waites"), ("Hua", "Wang"), ("Yang", "Wang"),
    ("Heather", "Wardle"), ("Alister", "Wedderburn"), ("Bridgette", "Wessels"),
    ("James", "White"), ("Theo", "Williams"), ("Tim", "Winzler"),
    ("Phillippa", "Wiseman"), ("Mark", "Wong"), ("Sharon", "Wright"),
    ("Helen", "Yaffe"), ("Souleymane", "Yameogo"), ("Jing", "Yao"),
    ("Graeme", "Young"), ("Katherine", "Younger"), ("Qunshan", "Zhao"),
    ("Jingyi", "Zhu"), ("Mingyu", "Zhu"), ("Liyuan", "Zhuang"),
    ("Hayley", "Connell"), ("Yvonne", "Cunningham"), ("Gillian", "Fergie"),
    ("Evi", "Germeni"), ("Sharon", "Greenwood"), ("Emma", "Lawlor"),
    ("Sara", "MacDonald"), ("Nicola", "McEwen"), ("Kate", "ODonnell"),
    ("Victoria", "Palmer"),
    # Emeritus/honorary
    ("David", "Adams"), ("Christopher", "Berry"), ("David", "Clapham"),
    ("Terence", "Cox"), ("Bridget", "Fowler"), ("Michael", "French"),
    ("Brian", "Girvin"), ("Keith", "Kintrea"), ("Mark", "Livingston"),
    ("Moira", "Munro"), ("Hugh", "Murphy"), ("Malcolm", "Nicolson"),
    ("Joan", "Orme"), ("Gregory", "Philo"), ("Adriana Mihaela", "Soaita"),
    ("Ray", "Stokes"), ("Geoffrey", "Swain"), ("Jim", "Tomlinson"),
    ("Patricio", "Troncoso"), ("Gerasimos", "Tsourapas"), ("Ya Ping", "Wang"),
    ("Nicholas", "Watson"), ("David", "Webster"), ("Sally", "Wyke"),
]

# Roles that indicate PI or Co-I involvement
PI_COI_ROLES = {"PI_PER", "COI_PER", "FELLOW_PER"}

# ── Thematic tagging ──────────────────────────────────────────────────────────
TAG_PATTERNS = {
    "Governance & Policy": [
        r"\bgovern(ance|ment|ing)\b", r"\bpolic(y|ies|ing)\b",
        r"\bregulat(ion|ory|e)\b", r"\blegislat(ion|ive)\b",
        r"\bdemocra(cy|tic)\b", r"\bparliament\b", r"\belection\b",
        r"\bvoting\b", r"\bpublic administ\b", r"\bbureaucra\b",
        r"\bpolitical part(y|ies)\b",
    ],
    "Health & Wellbeing": [
        r"\bhealth\b", r"\bwellbeing\b", r"\bwell-being\b",
        r"\bmental health\b", r"\bepidemiolog\b", r"\bpandemic\b",
        r"\bdisease\b", r"\bmedic(al|ine)\b", r"\bclinical\b",
        r"\bNHS\b", r"\bpublic health\b", r"\bdisabilit(y|ies)\b",
        r"\bpatient\b", r"\bcare\b.*\b(social|health)\b",
    ],
    "Inequality & Social Justice": [
        r"\binequali(ty|ties)\b", r"\bjustice\b", r"\bpoverty\b",
        r"\bdeprivation\b", r"\bexclusion\b", r"\bmarginal\b",
        r"\bdiscriminat\b", r"\bracis(m|t)\b", r"\bgender\b.*\b(gap|inequal|pay)\b",
        r"\bhuman rights\b", r"\bsocial (justice|mobili)\b",
        r"\bredistribut\b",
    ],
    "Migration & Citizenship": [
        r"\bmigra(tion|nt|nts)\b", r"\brefugee\b", r"\basylum\b",
        r"\bdiaspora\b", r"\bcitizenship\b", r"\bimmigra\b",
        r"\bborder(s|ing)?\b", r"\bdisplace(d|ment)\b",
        r"\bethnicit(y|ies)\b", r"\bmulticultur\b", r"\bintegrati(on|ng)\b.*\b(migr|refug|immig)\b",
    ],
    "Environment & Sustainability": [
        r"\benvironment\b", r"\bclimate\b", r"\bsustainab\b",
        r"\bcarbon\b", r"\brenewable\b", r"\benergy transition\b",
        r"\bnet.?zero\b", r"\bbiodivers\b", r"\becolog(y|ical)\b",
        r"\bpollut\b", r"\bgreen\b.*\b(econom|deal|polic)\b",
        r"\bnatural resource\b",
    ],
    "Culture & Heritage": [
        r"\bcultur(e|al)\b", r"\bheritage\b", r"\bidentit(y|ies)\b",
        r"\bmuseum\b", r"\bart(s|istic)?\b", r"\bmedia\b",
        r"\bjournalis\b", r"\bfilm\b", r"\bnarrative\b",
        r"\bhistori(c|cal)\b", r"\bmemor(y|ial)\b", r"\bcommemorat\b",
    ],
    "Conflict & Security": [
        r"\bconflict\b", r"\bsecurit(y|ies)\b", r"\bwar\b",
        r"\bpeace\b", r"\bviolen(ce|t)\b", r"\bterroris\b",
        r"\bextremis\b", r"\bgeopolit\b", r"\bmilitar(y|ism)\b",
        r"\bnuclear\b", r"\bcyber\b.*\bsecurit\b",
        r"\bdefence\b",
    ],
    "Global Health": [
        r"\bglobal health\b", r"\btropical\b", r"\binfect(ion|ious)\b",
        r"\bvaccin\b", r"\bAIDS\b", r"\bHIV\b", r"\bmalaria\b",
        r"\btuberculosis\b", r"\bWHO\b", r"\bhealth system\b",
        r"\blow.income countr\b", r"\bglobal south\b.*\bhealth\b",
        r"\bpandemic\b", r"\bCOVID\b", r"\bcovid\b",
    ],
    "Economy & Development": [
        r"\beconom(y|ic|ics)\b", r"\bdevelopment\b",
        r"\btrade\b", r"\bfinancial\b", r"\bmarket\b",
        r"\bglobali(s|z)ation\b", r"\baid\b.*\b(develop|international)\b",
        r"\bgrowth\b", r"\bindustr(y|ial)\b", r"\blabour\b",
        r"\bemploy(ment|ee)\b", r"\bworkforce\b",
    ],
    "Housing & Urban": [
        r"\bhousing\b", r"\bhomeless\b", r"\burban\b",
        r"\bcit(y|ies)\b", r"\bneighbourhood\b", r"\bneighborhood\b",
        r"\bplanning\b.*\b(urban|city|town|spatial)\b",
        r"\bgentrific\b", r"\btenant\b", r"\brent(al|ing|er)?\b",
        r"\binfrastructure\b",
    ],
    "Data & Digital": [
        r"\bdata\b", r"\bdigital\b", r"\balgorithm\b",
        r"\bartificial intelligence\b", r"\b(AI|ML)\b", r"\bmachine learning\b",
        r"\bcomput(er|ing|ational)\b", r"\bautomati(on|c|ed)\b",
        r"\bplatform\b", r"\bsocial media\b", r"\bonline\b",
        r"\bsurveillance\b", r"\bprivacy\b", r"\bcyber\b",
        r"\bbig data\b", r"\bsmart\b.*\b(city|cities|technolog)\b",
        r"\bdata(set|base|driven)\b", r"\btech(nolog)\b",
        r"\binternet\b", r"\bsensor\b",
    ],
    "Gender & Equality": [
        r"\bgender\b", r"\bfeminis\b", r"\bwomen\b",
        r"\bmasculinit\b", r"\bsex(ual|ualit)\b", r"\bLGBT\b",
        r"\bqueer\b", r"\btransgend\b", r"\bpatriarch\b",
        r"\bgender.based violence\b", r"\breproducti\b",
        r"\bmaternal\b", r"\bequali(ty|ties)\b", r"\bdiversi(ty|ties)\b",
        r"\binclusi(on|ve)\b", r"\bintersection\b",
        r"\bgender\b.*\b(gap|pay|inequal|equal|norm|role|identit)\b",
        r"\bwomen\b.*\b(right|empower|particip|represent)\b",
    ],
}


def tag_project(title, abstract):
    """Assign up to 3 thematic tags based on title + abstract text."""
    text = f"{title} {abstract}".lower()
    scores = {}
    for tag, patterns in TAG_PATTERNS.items():
        count = 0
        for pat in patterns:
            count += len(re.findall(pat, text, re.IGNORECASE))
        if count > 0:
            scores[tag] = count
    top = sorted(scores, key=scores.get, reverse=True)[:3]
    return "; ".join(top)


# ── GTR API helpers ───────────────────────────────────────────────────────────

def epoch_ms_to_date(val):
    """Convert epoch milliseconds to YYYY-MM-DD string."""
    if val is None:
        return ""
    try:
        if isinstance(val, (int, float)):
            return datetime.datetime.fromtimestamp(val / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
        elif isinstance(val, str) and len(val) >= 4:
            return val[:10]  # already a date string
    except Exception:
        pass
    return ""


def find_person_projects(first, last, client):
    """Search GTR persons endpoint and return (project_id, role) pairs."""
    query = f"{first} {last}"
    try:
        r = client.get(
            f"{GTR_API}/persons",
            params={"q": query, "s": 100},
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ERROR searching persons {query}: {e}", file=sys.stderr)
        return []

    persons = data.get("person", [])
    project_links = []

    for person in persons:
        p_first = (person.get("firstName") or "").strip().lower()
        p_last = (person.get("surname") or "").strip().lower()

        # Match: surname must match exactly, first name must start with the same
        if p_last != last.lower():
            continue
        if not p_first.startswith(first.split()[0].lower()):
            continue

        links = person.get("links", {}).get("link", [])
        for link in links:
            rel = link.get("rel", "")
            href = link.get("href", "")
            if rel in PI_COI_ROLES and "/projects/" in href:
                project_id = href.rstrip("/").split("/")[-1]
                project_links.append((project_id, rel))

    return project_links


def fetch_project(project_id, client):
    """Fetch full project details by ID."""
    try:
        r = client.get(
            f"{GTR_API}/projects/{project_id}",
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ERROR fetching project {project_id}: {e}", file=sys.stderr)
        return None


def extract_fund_info(project_data, client, fund_cache):
    """Extract start_date, end_date, and grant_offer from FUND links.

    The project response includes FUND links with start/end timestamps.
    We fetch the fund endpoint for the grant value (valuePounds.amount).
    Returns (start_date, end_date, grant_offer_gbp).
    """
    links = project_data.get("links", {}).get("link", [])
    fund_links = [l for l in links if l.get("rel") == "FUND"]

    if not fund_links:
        return "", "", ""

    # Use the first fund link; dates are on the link itself
    fund_link = fund_links[0]
    start_date = epoch_ms_to_date(fund_link.get("start"))
    end_date = epoch_ms_to_date(fund_link.get("end"))

    # If multiple fund links, find the widest date range and sum values
    all_starts = []
    all_ends = []
    total_value = 0

    for fl in fund_links:
        s = fl.get("start")
        e = fl.get("end")
        if s:
            all_starts.append(s)
        if e:
            all_ends.append(e)

        # Fetch fund for grant value
        fund_href = fl.get("href", "")
        fund_id = fund_href.rstrip("/").split("/")[-1] if fund_href else ""

        if fund_id and fund_id in fund_cache:
            total_value += fund_cache[fund_id]
        elif fund_id:
            try:
                # Use https version of the URL
                fund_url = f"{GTR_API}/funds/{fund_id}"
                r = client.get(fund_url, headers=HEADERS, timeout=30)
                r.raise_for_status()
                fund_data = r.json()
                amount = (fund_data.get("valuePounds") or {}).get("amount", 0)
                if amount:
                    total_value += amount
                fund_cache[fund_id] = amount or 0
                time.sleep(0.1)
            except Exception as e:
                print(f"    WARN: could not fetch fund {fund_id}: {e}", file=sys.stderr)
                fund_cache[fund_id] = 0

    # Use earliest start and latest end across all fund links
    if all_starts:
        start_date = epoch_ms_to_date(min(all_starts))
    if all_ends:
        end_date = epoch_ms_to_date(max(all_ends))

    grant_offer = f"{total_value:.0f}" if total_value else ""

    return start_date, end_date, grant_offer


def extract_lead_org(project_data, client, org_cache):
    """Extract lead organisation name from LEAD_ORG link."""
    links = project_data.get("links", {}).get("link", [])
    lead_org_links = [l for l in links if l.get("rel") == "LEAD_ORG"]

    if not lead_org_links:
        return ""

    org_href = lead_org_links[0].get("href", "")
    org_id = org_href.rstrip("/").split("/")[-1] if org_href else ""

    if not org_id:
        return ""

    if org_id in org_cache:
        return org_cache[org_id]

    try:
        org_url = f"{GTR_API}/organisations/{org_id}"
        r = client.get(org_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        org_data = r.json()
        name = org_data.get("name", "")
        org_cache[org_id] = name
        time.sleep(0.1)
        return name
    except Exception as e:
        print(f"    WARN: could not fetch org {org_id}: {e}", file=sys.stderr)
        org_cache[org_id] = ""
        return ""


def extract_grant_ref(project_data):
    """Extract the RCUK grant reference (e.g. ES/T012345/1)."""
    identifiers = project_data.get("identifiers", {}).get("identifier", [])
    for ident in identifiers:
        if ident.get("type") == "RCUK":
            return ident.get("value", "")
    return ""


def is_recent_enough(project_data):
    """Check if project is Active or Closed from 2020+.

    Uses FUND link dates since project-level start/end are often None.
    """
    status = project_data.get("status", "")
    if status == "Active":
        return True
    if status == "Closed":
        # Try project-level end date first
        end = project_data.get("end")
        if end and isinstance(end, (int, float)):
            year = datetime.datetime.fromtimestamp(end / 1000, tz=datetime.timezone.utc).year
            return year >= 2020

        # Fall back to FUND link end dates
        links = project_data.get("links", {}).get("link", [])
        fund_ends = [
            l.get("end") for l in links
            if l.get("rel") == "FUND" and l.get("end")
        ]
        if fund_ends:
            latest_end = max(fund_ends)
            if isinstance(latest_end, (int, float)):
                year = datetime.datetime.fromtimestamp(latest_end / 1000, tz=datetime.timezone.utc).year
                return year >= 2020

        # No end date but Closed — include to be safe
        return True
    return False


def main():
    # project_id -> { "project": dict, "staff": {name: role} }
    all_projects = {}
    fetched_cache = {}  # cache fetched projects
    org_cache = {}  # cache organisation name lookups
    fund_cache = {}  # cache fund value lookups

    with httpx.Client() as client:
        total = len(STAFF)
        for i, (first, last) in enumerate(STAFF):
            name = f"{first} {last}"
            print(f"[{i+1}/{total}] Searching: {name}", file=sys.stderr, flush=True)

            project_links = find_person_projects(first, last, client)

            if project_links:
                print(f"  Found {len(project_links)} project links", file=sys.stderr)

            for project_id, role in project_links:
                role_label = {"PI_PER": "PI", "COI_PER": "Co-I", "FELLOW_PER": "Fellow"}.get(role, role)

                # Fetch project if not cached
                if project_id not in fetched_cache:
                    proj = fetch_project(project_id, client)
                    fetched_cache[project_id] = proj
                    time.sleep(0.2)
                else:
                    proj = fetched_cache[project_id]

                if not proj:
                    continue

                if not is_recent_enough(proj):
                    continue

                if project_id not in all_projects:
                    all_projects[project_id] = {"project": proj, "staff": {}}
                all_projects[project_id]["staff"][name] = role_label

            time.sleep(0.3)

        # ── Phase 2: Enrich with fund values and lead org names ───────────
        print(f"\nEnriching {len(all_projects)} projects with fund/org data...",
              file=sys.stderr, flush=True)

        enriched = {}
        for idx, (pid, entry) in enumerate(all_projects.items()):
            proj = entry["project"]
            if (idx + 1) % 25 == 0 or idx == 0:
                print(f"  [{idx+1}/{len(all_projects)}] Enriching...",
                      file=sys.stderr, flush=True)

            start_date, end_date, grant_offer = extract_fund_info(proj, client, fund_cache)
            lead_org = extract_lead_org(proj, client, org_cache)
            grant_ref = extract_grant_ref(proj)

            enriched[pid] = {
                "start_date": start_date,
                "end_date": end_date,
                "grant_offer": grant_offer,
                "lead_org": lead_org,
                "grant_ref": grant_ref,
            }

    # Write CSV
    outpath = "/Users/jamie.cross/Documents/UKRI-GTR-Scanner/data/uofg_sps_staff_gtr_projects.csv"
    fieldnames = [
        "title", "id", "grant_ref", "status", "grant_category", "funder",
        "grant_offer", "lead_org", "start_date", "end_date",
        "staff_members", "roles", "abstract", "tags",
    ]

    with open(outpath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for pid, entry in sorted(
            all_projects.items(), key=lambda x: x[1]["project"].get("title", "")
        ):
            proj = entry["project"]
            staff_roles = entry["staff"]
            extra = enriched.get(pid, {})

            staff_str = "; ".join(sorted(staff_roles.keys()))
            roles_str = "; ".join(f"{n} ({r})" for n, r in sorted(staff_roles.items()))
            abstract = proj.get("abstractText", "") or ""
            tags = tag_project(proj.get("title", ""), abstract)

            writer.writerow({
                "title": proj.get("title", ""),
                "id": pid,
                "grant_ref": extra.get("grant_ref", ""),
                "status": proj.get("status", ""),
                "grant_category": proj.get("grantCategory", ""),
                "funder": proj.get("leadFunder", ""),
                "grant_offer": extra.get("grant_offer", ""),
                "lead_org": extra.get("lead_org", ""),
                "start_date": extra.get("start_date", ""),
                "end_date": extra.get("end_date", ""),
                "staff_members": staff_str,
                "roles": roles_str,
                "abstract": abstract,
                "tags": tags,
            })

    print(f"\nDone! Wrote {len(all_projects)} projects to {outpath}", file=sys.stderr)
    print(f"  Org cache: {len(org_cache)} organisations", file=sys.stderr)
    print(f"  Fund cache: {len(fund_cache)} funds", file=sys.stderr)


if __name__ == "__main__":
    main()
