"""Async client for the UKRI Gateway to Research API."""

import httpx
from dataclasses import dataclass


GTR_API_BASE = "https://gtr.ukri.org/gtr/api"
USER_AGENT = "ukri-gtr-scanner/1.0"


@dataclass
class Project:
    title: str
    abstract: str
    id: str
    grant_category: str | None = None
    grant_offer: float | None = None
    start_date: str | None = None
    end_date: str | None = None
    funder_name: str | None = None
    lead_org: str | None = None
    tech_abstract: str | None = None
    potential_impact: str | None = None
    status: str | None = None


@dataclass
class SearchResult:
    projects: list[Project]
    total_results: int
    page: int
    total_pages: int


def _parse_project(data: dict) -> Project | None:
    """Parse a project from the GTR API /projects endpoint."""
    title = data.get("title")
    if not title:
        return None

    # Extract lead participant funding info
    grant_offer = None
    lead_org = None
    participants = (data.get("participantValues") or {}).get("participant", [])
    for p in participants:
        if p.get("role") == "LEAD_PARTICIPANT":
            lead_org = p.get("organisationName")
            grant_offer = p.get("grantOffer")
            break
    # Fallback: use first participant
    if not lead_org and participants:
        lead_org = participants[0].get("organisationName")
        grant_offer = participants[0].get("grantOffer")

    return Project(
        title=title,
        abstract=data.get("abstractText", ""),
        id=data.get("id", ""),
        grant_category=data.get("grantCategory"),
        grant_offer=grant_offer,
        start_date=data.get("start"),
        end_date=data.get("end"),
        funder_name=data.get("leadFunder"),
        lead_org=lead_org,
        tech_abstract=data.get("techAbstractText"),
        potential_impact=data.get("potentialImpact"),
        status=data.get("status"),
    )


async def search_projects(
    query: str,
    page: int = 1,
    page_size: int = 100,
) -> SearchResult:
    """Search GTR projects by keyword query.

    Args:
        query: Search term(s). Supports OR/AND operators and quoted phrases.
        page: Page number (1-indexed).
        page_size: Results per page (max 100).
    """
    url = f"{GTR_API_BASE}/projects"
    params = {
        "q": query,
        "p": page,
        "s": min(page_size, 100),
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        body = response.json()

    total_results = body.get("totalSize", 0)
    total_pages = body.get("totalPages", 0)
    current_page = body.get("page", page)
    project_list = body.get("project", [])

    projects = []
    for item in project_list:
        proj = _parse_project(item)
        if proj:
            projects.append(proj)

    return SearchResult(
        projects=projects,
        total_results=total_results,
        page=current_page,
        total_pages=total_pages,
    )


async def get_project_by_id(project_id: str) -> Project | None:
    """Fetch a single project by its GTR ID."""
    url = f"{GTR_API_BASE}/projects/{project_id}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

    return _parse_project(data)


async def search_all_pages(
    query: str,
    max_pages: int | None = None,
    page_size: int = 100,
) -> list[Project]:
    """Search and paginate through all results.

    Args:
        query: Search term(s).
        max_pages: Limit number of pages to fetch. None for all.
        page_size: Results per page (max 100).
    """
    first = await search_projects(query, page=1, page_size=page_size)
    all_projects = list(first.projects)

    total_pages = first.total_pages
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    for page_num in range(2, total_pages + 1):
        result = await search_projects(query, page=page_num, page_size=page_size)
        all_projects.extend(result.projects)

    return all_projects
