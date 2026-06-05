"""Real Apify task runner for Google Maps-style source runs.

This uses a configured Apify task ID because actor inputs vary by actor. Create
and test the task in Apify first, then set APIFY_GOOGLE_MAPS_TASK_ID.
"""

from typing import Any

from pydantic import BaseModel, Field
import requests

from scripts.config import get_settings
from scripts.import_real_data import RealDataImportSummary, import_real_lead_rows
from scripts.real_safety import require_real_api_enabled


APIFY_TASK_ITEMS_URL = (
    "https://api.apify.com/v2/actor-tasks/{task_id}/run-sync-get-dataset-items"
)


class ApifyGoogleMapsRealRequest(BaseModel):
    """Approved Apify task-run input."""

    mandate_id: str
    approval_id: str
    query: str
    limit: int = 25
    task_input: dict[str, Any] = Field(default_factory=dict)


class ApifyGoogleMapsRealResult(BaseModel):
    """Import summary for one real Apify task run."""

    request: ApifyGoogleMapsRealRequest
    records_returned: int
    import_summary: RealDataImportSummary


def _item_to_import_row(item: dict[str, Any]) -> dict[str, Any]:
    """Map common Google Maps actor fields to local importer columns."""
    return {
        "company_name": item.get("title") or item.get("name") or item.get("company_name"),
        "website": item.get("website") or item.get("url"),
        "industry": item.get("categoryName") or item.get("category") or item.get("industry"),
        "city": item.get("city"),
        "province": item.get("state") or item.get("province"),
        "country": item.get("country"),
        "phone": item.get("phone") or item.get("phoneNumber"),
        "source": "apify_google_maps_real",
        "source_url": item.get("url") or item.get("searchPageUrl"),
        "google_place_id": item.get("placeId") or item.get("googlePlaceId"),
    }


def run_apify_google_maps_real(
    request: ApifyGoogleMapsRealRequest,
    timeout: int = 300,
) -> ApifyGoogleMapsRealResult:
    """Run the configured Apify task and import returned business records."""
    settings = get_settings()
    require_real_api_enabled("Apify", settings.apify_api_token, request.approval_id)
    if not settings.apify_google_maps_task_id:
        raise PermissionError("APIFY_GOOGLE_MAPS_TASK_ID is missing.")

    task_input = dict(request.task_input)
    task_input.setdefault("searchStringsArray", [request.query])
    task_input.setdefault("maxCrawledPlacesPerSearch", request.limit)
    response = requests.post(
        APIFY_TASK_ITEMS_URL.format(task_id=settings.apify_google_maps_task_id),
        params={"token": settings.apify_api_token},
        json=task_input,
        timeout=timeout,
    )
    response.raise_for_status()
    items = response.json()
    if not isinstance(items, list):
        raise ValueError("Apify dataset response was not a list of items.")
    rows = [_item_to_import_row(item) for item in items[: request.limit]]
    import_summary = import_real_lead_rows(request.mandate_id, rows)
    return ApifyGoogleMapsRealResult(
        request=request,
        records_returned=len(items),
        import_summary=import_summary,
    )
