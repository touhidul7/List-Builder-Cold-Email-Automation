"""Tests for SOP production-readiness reporting."""

from typer.testing import CliRunner

from main import app
from scripts.config import Settings
from scripts.production_readiness import get_readiness_items, summarize_readiness


def test_readiness_inventory_includes_core_sop_areas() -> None:
    settings = Settings()
    items = get_readiness_items(settings)
    areas = {item.area for item in items}

    assert "Mandate" in areas
    assert "Claude Code" in areas
    assert "Web UI" in areas
    assert "Consulti" in areas
    assert "Winnr" in areas
    assert summarize_readiness(items)["done"] >= 1


def test_readiness_cli_is_read_only_and_renders_checklist() -> None:
    result = CliRunner().invoke(app, ["readiness"])

    assert result.exit_code == 0
    assert "SOP Production Readiness" in result.output
    assert "Requirement Checklist" in result.output
    assert "Claude Code" in result.output

