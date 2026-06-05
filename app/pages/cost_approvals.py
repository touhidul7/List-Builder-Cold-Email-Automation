"""Cost approval page."""

import json
import math
from typing import Any

import pandas as pd
import streamlit as st

from app.ui_helpers import render_dataframe, show_dry_run_banner, success_box
from app.utils import fetch_table, get_mandates_df, short_id
from scripts.cost_approval import CostApprovalRequest, format_cost_approval_message
from scripts.db import get_connection


def _load_approvals(mandate_id: str | None, status: str) -> pd.DataFrame:
    query = "SELECT * FROM cost_approvals"
    clauses: list[str] = []
    params: list[str] = []
    if mandate_id:
        clauses.append("mandate_id = ?")
        params.append(mandate_id)
    if status != "All":
        clauses.append("approval_status = ?")
        params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC, rowid DESC"
    return fetch_table(query, tuple(params))


def _optional_value(value: Any) -> Any | None:
    """Convert pandas/SQLite missing values into plain None."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    return value


def _optional_int(value: Any) -> int | None:
    """Convert an optional numeric value to int without passing NaN to Pydantic."""
    value = _optional_value(value)
    return int(value) if value is not None else None


def _optional_float(value: Any, default: float = 0) -> float:
    """Convert an optional numeric value to float with a safe default."""
    value = _optional_value(value)
    return float(value) if value is not None else default


def _request_from_row(row: pd.Series) -> CostApprovalRequest:
    notes = json.loads(_optional_value(row.get("notes")) or "{}")
    return CostApprovalRequest(
        mandate_id=_optional_value(row.get("mandate_id")),
        action_type=_optional_value(row.get("action_type")) or "paid_action",
        action_description=_optional_value(row.get("action_description")) or "",
        provider=_optional_value(row.get("provider")) or "",
        estimated_cost=_optional_float(row.get("estimated_cost")),
        estimated_credits=_optional_int(row.get("estimated_credits")),
        reason=notes.get("reason") or "Local review requested.",
        expected_output=notes.get("expected_output") or "Provider output.",
        alternatives=notes.get("alternatives"),
        risk=notes.get("risk"),
    )


def _update_approval(approval_id: str, status: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE cost_approvals
            SET
                approval_status = ?,
                approved_by = 'Streamlit User',
                approved_at = CASE WHEN ? = 'approved' THEN CURRENT_TIMESTAMP ELSE NULL END
            WHERE id = ?
            """,
            (status, status, approval_id),
        )
        connection.commit()


def render() -> None:
    """Render local approval review and mock approve/reject actions."""
    st.title("Cost Approvals")
    show_dry_run_banner()
    mandates = get_mandates_df()
    selected_mandate = st.selectbox("Mandate filter", ["All"] + ([] if mandates.empty else mandates["id"].tolist()))
    status = st.selectbox("Approval status", ["All", "pending", "approved", "rejected"])
    approvals = _load_approvals(None if selected_mandate == "All" else selected_mandate, status)
    display_df = approvals.copy()
    if not display_df.empty:
        display_df["short_id"] = display_df["id"].map(short_id)
        display_df = display_df[
            ["short_id", "provider", "action_type", "action_description", "estimated_cost", "approval_status", "approved_by", "created_at"]
        ]
    render_dataframe(display_df, "Cost Approval Records")

    pending = approvals[approvals["approval_status"] == "pending"] if not approvals.empty else approvals
    if pending.empty:
        return
    labels = {f"{short_id(row['id'])} | {row['provider']} | {row['action_type']}": row for _, row in pending.iterrows()}
    selected = st.selectbox("Select pending approval", list(labels.keys()))
    row = labels[selected]
    st.text(format_cost_approval_message(_request_from_row(row)))
    st.caption("Approval is local/mock only. It does not run any paid action automatically.")
    col1, col2 = st.columns(2)
    if col1.button("Approve Mock"):
        _update_approval(row["id"], "approved")
        success_box("Approval marked approved locally.")
        st.rerun()
    if col2.button("Reject Mock"):
        _update_approval(row["id"], "rejected")
        success_box("Approval marked rejected locally.")
        st.rerun()
