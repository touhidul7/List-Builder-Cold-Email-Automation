"""Real Apollo People Search integration behind explicit safety gates.

Apollo People Search finds net-new people but does not return email addresses.
Any enrichment or verified email discovery must be added as a separate approved
step.
"""

from typing import Any

from pydantic import BaseModel, Field
import requests

from scripts.config import get_settings
from scripts.import_real_data import RealDataImportSummary, import_real_lead_rows
from scripts.real_safety import require_real_api_enabled


APOLLO_PEOPLE_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"


class ApolloPeopleSearchRequest(BaseModel):
    """Approved Apollo People Search input."""

    mandate_id: str
    approval_id: str
    q_keywords: str | None = None
    organization_locations: list[str] = Field(default_factory=list)
    person_titles: list[str] = Field(default_factory=list)
    page: int = 1
    per_page: int = 25


class ApolloPeopleSearchResult(BaseModel):
    """Result from one Apollo search import."""

    request: ApolloPeopleSearchRequest
    people_returned: int
    companies_inserted: int
    contacts_inserted: int
    import_summary: RealDataImportSummary


def _apollo_headers(api_key: str) -> dict[str, str]:
    """Return Apollo auth headers."""
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def _search_payload(request: ApolloPeopleSearchRequest) -> dict[str, Any]:
    """Build Apollo search payload from request fields."""
    payload: dict[str, Any] = {
        "page": request.page,
        "per_page": request.per_page,
    }
    if request.q_keywords:
        payload["q_keywords"] = request.q_keywords
    if request.organization_locations:
        payload["organization_locations"] = request.organization_locations
    if request.person_titles:
        payload["person_titles"] = request.person_titles
        payload["include_similar_titles"] = True
    return payload


def _person_to_import_row(person: dict[str, Any]) -> dict[str, Any]:
    """Map Apollo person/org fields to the local real-data importer shape."""
    organization = person.get("organization") or {}
    company_name = (
        organization.get("name")
        or person.get("organization_name")
        or person.get("current_organization_name")
        or "Unknown Apollo Company"
    )
    website = (
        organization.get("website_url")
        or organization.get("primary_domain")
        or person.get("organization_website_url")
    )
    return {
        "company_name": company_name,
        "website": website,
        "industry": organization.get("industry"),
        "city": organization.get("city") or person.get("city"),
        "province": organization.get("state") or person.get("state"),
        "country": organization.get("country") or person.get("country"),
        "source": "apollo_people_search",
        "source_url": person.get("linkedin_url") or organization.get("linkedin_url"),
        "apollo_company_id": organization.get("id") or person.get("organization_id"),
        "full_name": person.get("name"),
        "title": person.get("title"),
        "email": person.get("email"),
        "email_status": "unknown",
        "contact_source": "apollo_people_search",
    }


def run_apollo_people_search_real(
    request: ApolloPeopleSearchRequest,
    timeout: int = 30,
) -> ApolloPeopleSearchResult:
    """Run Apollo People Search and import returned people/companies locally."""
    settings = get_settings()
    require_real_api_enabled("Apollo", settings.apollo_api_key, request.approval_id)
    if request.per_page < 1 or request.per_page > 100:
        raise ValueError("Apollo per_page must be between 1 and 100.")

    response = requests.post(
        APOLLO_PEOPLE_SEARCH_URL,
        headers=_apollo_headers(settings.apollo_api_key),
        json=_search_payload(request),
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    people = data.get("people") or data.get("contacts") or []
    rows = [_person_to_import_row(person) for person in people]
    import_summary = import_real_lead_rows(request.mandate_id, rows)
    return ApolloPeopleSearchResult(
        request=request,
        people_returned=len(people),
        companies_inserted=import_summary.companies_inserted,
        contacts_inserted=import_summary.contacts_inserted,
        import_summary=import_summary,
    )
