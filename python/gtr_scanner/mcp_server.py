"""MCP server exposing GTR search tools to Claude Code."""

from mcp.server.fastmcp import FastMCP

from gtr_scanner.client import search_projects, get_project_by_id, search_all_pages

mcp = FastMCP("gtr")


@mcp.tool()
async def gtr_search(query: str, page: int = 1) -> str:
    """Search UKRI Gateway to Research for funded projects.

    Args:
        query: Search keywords. Supports OR/AND and quoted phrases,
               e.g. '"climate change" OR biodiversity'.
        page: Page number (1-indexed). Each page returns up to 100 results.
    """
    result = await search_projects(query, page=page)

    lines = [
        f"Found {result.total_results} projects "
        f"(page {result.page}/{result.total_pages}):\n"
    ]

    for p in result.projects:
        value = f"£{p.grant_offer:,.0f}" if p.grant_offer else "N/A"
        lines.append(f"## {p.title}")
        lines.append(f"- **ID**: {p.id}")
        lines.append(f"- **Status**: {p.status or 'N/A'}")
        lines.append(f"- **Funder**: {p.funder_name or 'N/A'}")
        lines.append(f"- **Grant**: {value}")
        lines.append(f"- **Lead Org**: {p.lead_org or 'N/A'}")
        lines.append(f"- **Dates**: {p.start_date or '?'} → {p.end_date or '?'}")
        if p.abstract:
            abstract = p.abstract[:300] + "..." if len(p.abstract) > 300 else p.abstract
            lines.append(f"- **Abstract**: {abstract}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def gtr_project_detail(project_id: str) -> str:
    """Get full details of a single GTR project by its ID.

    Args:
        project_id: The GTR project UUID.
    """
    p = await get_project_by_id(project_id)
    if not p:
        return f"No project found with ID: {project_id}"

    value = f"£{p.grant_offer:,.0f}" if p.grant_offer else "N/A"
    lines = [
        f"# {p.title}",
        f"- **ID**: {p.id}",
        f"- **Status**: {p.status or 'N/A'}",
        f"- **Category**: {p.grant_category or 'N/A'}",
        f"- **Funder**: {p.funder_name or 'N/A'}",
        f"- **Grant**: {value}",
        f"- **Dates**: {p.start_date or '?'} → {p.end_date or '?'}",
        "",
        "## Abstract",
        p.abstract or "N/A",
    ]

    if p.tech_abstract:
        lines.extend(["", "## Technical Abstract", p.tech_abstract])
    if p.potential_impact:
        lines.extend(["", "## Potential Impact", p.potential_impact])

    return "\n".join(lines)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
