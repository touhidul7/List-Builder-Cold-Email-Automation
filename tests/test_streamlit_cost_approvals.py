"""Regression tests for the Streamlit cost approvals page helpers."""

import math

import pandas as pd

from app.pages.cost_approvals import _request_from_row


def test_request_from_row_converts_nan_estimated_credits_to_none() -> None:
    request = _request_from_row(
        pd.Series(
            {
                "mandate_id": "mandate-1",
                "action_type": "search",
                "action_description": "Run approved source search",
                "provider": "apollo",
                "estimated_cost": 10.0,
                "estimated_credits": math.nan,
                "notes": "{}",
            }
        )
    )

    assert request.estimated_credits is None
