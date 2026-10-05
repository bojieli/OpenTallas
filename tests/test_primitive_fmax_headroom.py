"""The pre-redesign primitive Fmax headroom record is rebuilt from its committed routes."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import summarize_primitive_fmax_headroom as S  # noqa: E402

RECORD = json.loads(S.OUTPUT.read_text())


def test_record_matches_a_rebuild_from_committed_routes():
    rebuilt = S.build()
    strip = lambda d: {k: v for k, v in d.items() if k != "producer"}  # noqa: E731
    assert strip(rebuilt) == strip(RECORD)


def test_labelled_pre_redesign_and_not_a_limiter():
    assert "PRE-REDESIGN" in RECORD["label"]
    assert any("not the design's clock limiter" in s for s in RECORD["not_a_claim"])


def test_every_planned_route_is_landed_or_listed_as_not_landed():
    plan = json.loads(S.PLAN.read_text())
    for row in RECORD["primitives"]:
        planned = {j["job"] for j in plan if j["variant"] == row["primitive"]}
        seen = {r["job"] for r in row["sweep_routes"]} | {r["job"] for r in row["sweep_routes_not_landed"]}
        assert planned == seen, row["primitive"]


def test_best_figures_are_consistent_and_closed_false_is_flagged():
    for row in RECORD["primitives"]:
        b, c = row["best_any"], row["best_closed"]
        assert b is not None, row["primitive"]
        if c:
            assert c["fmax_mhz"] <= b["fmax_mhz"]
        assert row["best_any_is_closed_false"] == (not b["closed"])
        landed = [r for r in row["sweep_routes"] if r["fmax_mhz"]]
        pub = row["published"]["fmax_mhz"] if row["published"] else None
        assert b["fmax_mhz"] == max([r["fmax_mhz"] for r in landed] + ([pub] if pub else []))
