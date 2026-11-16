"""TOOLS-CONVERGE-1116 (COORD): every die's adopted plan of record validates against THIS tree's schema (structure).
A key the die tree's private schema.py knew and main's did not made main reject plan B6gG3b ('plan invalid').  adopted_plans.json
lists the plans on the fleet; a path that is not on this host is skipped (the gate runs on a build host), the keys test always runs."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402

PLANS = {k: v for k, v in json.loads((HERE / "adopted_plans.json").read_text()).items() if not k.startswith("_")}


def test_keys_every_adopted_plan_needs_are_in_the_schema():
    props = schema.SCHEMA["properties"]
    assert "relay_polylines" in props["partition_types"]["additionalProperties"]["properties"]
    for k in ("gutter_block_um", "gutter_block_min_span_um", "gutter_block_types"):
        assert k in props["budgets"]["properties"]
    assert "tap_offset" in props["clock"]["properties"]


@pytest.mark.parametrize("die", sorted(PLANS))
def test_adopted_plan_is_valid_structure(die):
    p = Path(PLANS[die])
    if not p.is_file():
        pytest.skip(f"{p} not on this host")
    errs = schema.validate_structure(json.loads(p.read_text()))
    assert errs == [], f"{die}: {len(errs)} schema errors, first: {errs[:3]}"
