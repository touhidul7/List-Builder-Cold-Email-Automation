"""DRY_RUN-only mock Apify Google Maps lead generation."""

import json
from pathlib import Path
import re
import uuid

from pydantic import BaseModel

from scripts.config import get_settings
from scripts.db import get_connection
from scripts.dedupe_leads import find_duplicate_company
from scripts.fingerprint import create_company_fingerprint, extract_root_domain


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


class GoogleMapsLead(BaseModel):
    """Synthetic local-business lead shaped like a Maps scraper result."""

    company_name: str
    website: str | None = None
    root_domain: str | None = None
    phone: str | None = None
    city: str | None = None
    province: str | None = None
    country: str | None = None
    category: str | None = None
    google_maps_url: str | None = None
    google_place_id: str | None = None
    source: str = "apify_google_maps"
    source_url: str | None = None


def _query_location(query: str) -> tuple[str, str, str]:
    """Infer a synthetic city, province, and country from the query."""
    lowered = query.lower()
    if "oakville" in lowered:
        return "Oakville", "Ontario", "Canada"
    if "toronto" in lowered or "gta" in lowered:
        return "Toronto", "Ontario", "Canada"
    if "ontario" in lowered:
        return "Toronto", "Ontario", "Canada"
    if "new york" in lowered:
        return "New York", "New York", "United States"
    return "Toronto", "Ontario", "Canada"


def _lead_templates(query: str) -> tuple[list[str], str, str]:
    """Return synthetic name templates, category, and domain slug."""
    lowered = query.lower()
    if "commercial cleaning" in lowered or "janitorial" in lowered:
        return (
            [
                "Ontario Commercial Cleaning Group",
                "Toronto Janitorial Services",
                "GTA Facility Cleaning Co",
                "Maple Office Cleaning",
            ],
            "Commercial cleaning",
            "cleaning",
        )
    if "gym" in lowered or "fitness" in lowered:
        return (
            [
                "Oakville Performance Fitness",
                "GTA Health Club",
                "Toronto Strength Studio",
            ],
            "Gym",
            "fitness",
        )
    return (
        [
            "Maple Local Business Group",
            "Ontario Service Partners",
            "GTA Business Solutions",
        ],
        "Local business",
        "business",
    )


def generate_mock_google_maps_leads(
    query: str,
    limit: int = 25,
) -> list[GoogleMapsLead]:
    """Generate deterministic fake Maps leads without calling Apify."""
    if limit < 0:
        raise ValueError("Mock lead limit cannot be negative.")
    templates, category, domain_slug = _lead_templates(query)
    city, province, country = _query_location(query)
    leads: list[GoogleMapsLead] = []
    for index in range(1, limit + 1):
        base_name = templates[(index - 1) % len(templates)]
        company_name = f"{base_name} {index:02d}"
        website = f"https://example-{domain_slug}-{index}.ca"
        maps_url = f"https://maps.example.test/place/mock-{domain_slug}-{index}"
        leads.append(
            GoogleMapsLead(
                company_name=company_name,
                website=website,
                root_domain=extract_root_domain(website),
                phone=f"+1 416-555-{1000 + index:04d}",
                city=city,
                province=province,
                country=country,
                category=category,
                google_maps_url=maps_url,
                google_place_id=f"fake-place-{domain_slug}-{index:03d}",
                source_url=maps_url,
            )
        )
    return leads


def save_google_maps_leads(
    mandate_id: str,
    source_run_id: str,
    leads: list[GoogleMapsLead],
) -> int:
    """Insert synthetic non-duplicate Maps leads into local SQLite."""
    inserted = 0
    for lead in leads:
        duplicate = find_duplicate_company(
            company_name=lead.company_name,
            website=lead.website,
            root_domain=lead.root_domain,
            city=lead.city,
            province=lead.province,
            phone=lead.phone,
            google_place_id=lead.google_place_id,
            source_url=lead.source_url or lead.google_maps_url,
        )
        if any(match.confidence == "high" for match in duplicate.matches):
            continue

        root_domain = lead.root_domain or extract_root_domain(lead.website)
        company_id = str(uuid.uuid4())
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO companies (
                    id,
                    mandate_id,
                    company_name,
                    website,
                    root_domain,
                    industry,
                    city,
                    province,
                    country,
                    phone,
                    source,
                    source_url,
                    google_place_id,
                    apify_run_id,
                    source_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    mandate_id,
                    lead.company_name,
                    lead.website,
                    root_domain or None,
                    lead.category,
                    lead.city,
                    lead.province,
                    lead.country,
                    lead.phone,
                    lead.source,
                    lead.source_url or lead.google_maps_url,
                    lead.google_place_id,
                    source_run_id,
                    create_company_fingerprint(
                        lead.company_name,
                        root_domain or lead.website,
                        lead.city,
                        lead.phone,
                    ),
                ),
            )
            connection.commit()
        inserted += 1
    return inserted


def run_apify_google_maps_mock(
    mandate_id: str,
    source_run_id: str,
    query: str,
    limit: int = 25,
) -> dict:
    """Generate, save, and record one synthetic Google Maps run."""
    settings = get_settings()
    if not settings.dry_run:
        raise PermissionError("Google Maps mock runner requires DRY_RUN=true.")

    leads = generate_mock_google_maps_leads(query, limit)
    inserted = save_google_maps_leads(mandate_id, source_run_id, leads)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    safe_source_run_id = re.sub(r"[^A-Za-z0-9_-]", "_", source_run_id)
    raw_path = RAW_DATA_DIR / f"{safe_source_run_id}_google_maps_mock.json"
    raw_path.write_text(
        json.dumps([lead.model_dump() for lead in leads], indent=2),
        encoding="utf-8",
    )
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE source_runs
            SET
                status = 'completed_mock',
                raw_output_path = ?,
                records_found = ?,
                records_imported = ?,
                started_at = COALESCE(started_at, CURRENT_TIMESTAMP),
                finished_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (str(raw_path), len(leads), inserted, source_run_id),
        )
        connection.commit()
    return {
        "source_run_id": source_run_id,
        "provider": "Apify Google Maps mock",
        "query": query,
        "records_found": len(leads),
        "records_imported": inserted,
        "raw_output_path": str(raw_path),
        "status": "completed_mock",
    }
