#!/usr/bin/env python3
"""Shared box-quality accounting for completion/evidence gates.

The box report marks a row with ``y_waived_recomposition`` when a taller,
flow-native section legitimately moves a child on the Y axis.  That waiver is
axis-scoped: it may remove a Y-only row from pass-rate accounting, but it must
never erase an X/W/H failure or inflate the pass count above the denominator.
"""
from __future__ import annotations


def _is_y_waived(item: dict) -> bool:
    notes = item.get("notes") or ""
    return bool(
        item.get("y_waived_recomposition")
        or "y_waived_recomposition" in notes
    )


def _is_y_only_waiver(item: dict) -> bool:
    """Return True only when the row has no non-Y failure left to judge."""
    if not _is_y_waived(item):
        return False
    failed_axes = item.get("failed_axes")
    if failed_axes is not None and any(axis != "y" for axis in failed_axes):
        return False
    # Compatibility with older reports that retained the original Y failure.
    # Current box_diff removes Y, leaves failed_axes empty, then sets pass.
    return bool(item.get("pass")) or bool(failed_axes)


def _has_nonwaived_failure(item: dict) -> bool:
    failed_axes = item.get("failed_axes")
    if failed_axes is not None:
        for axis in failed_axes:
            if axis != "y" or not _is_y_waived(item):
                return True
    return not bool(item.get("pass"))


def evaluate_box_quality(items: list[dict], manifest: dict) -> dict:
    """Compute waiver-safe rate and critical failure groups.

    ``items`` is authoritative; summary counters are deliberately ignored
    because legacy reports counted Y-waived passes in the numerator while
    removing them only from the denominator.
    """
    elements = {
        element.get("id"): element
        for element in manifest.get("elements", []) or []
        if element.get("id")
    }
    y_waiver_rows = [item for item in items if _is_y_waived(item)]
    y_only_waived = [item for item in items if _is_y_only_waiver(item)]
    eligible = [item for item in items if not _is_y_only_waiver(item)]
    passed = [item for item in eligible if not _has_nonwaived_failure(item)]
    failed = [item for item in eligible if _has_nonwaived_failure(item)]
    rate = len(passed) / len(eligible) if eligible else 1.0

    # Construction from subset counts guarantees the public invariant.  Keep
    # the assertion close to the calculation so future edits cannot recreate
    # the observed 24/21 (>1.0) regression silently.
    assert 0.0 <= rate <= 1.0

    fv_failures: list[str] = []
    section_or_priority_failures: list[str] = []
    for item in failed:
        item_id = item.get("id")
        meta = elements.get(item_id, {})
        qa_priority = meta.get("qaPriority") or item.get("qaPriority")
        priority = meta.get("priority") or item.get("priority")
        if qa_priority == "fv-critical":
            fv_failures.append(item_id)
        elif qa_priority == "section-critical" or priority in ("critical", "high"):
            section_or_priority_failures.append(item_id)

    return {
        "total": len(items),
        "eligible": len(eligible),
        "passed": len(passed),
        "failed": len(failed),
        "yWaiverRows": len(y_waiver_rows),
        "yOnlyWaived": len(y_only_waived),
        "rate": rate,
        "fvCriticalFailures": list(dict.fromkeys(fv_failures)),
        "sectionOrPriorityFailures": list(
            dict.fromkeys(section_or_priority_failures)
        ),
    }
