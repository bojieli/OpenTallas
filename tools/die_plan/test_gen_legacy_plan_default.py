#!/usr/bin/env python3
"""gen_core_kit_legacy: --plan default is the plan of record; a stale plan always warns (FORM-S81-2 11-05)."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py"
spec = importlib.util.spec_from_file_location("gen_core_kit_legacy", SRC)
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def main():
    # default: a module of the plan of record
    p, note = G.resolve_plan(None, {}, "dsdv_eng_rr_e")
    assert p == G.DEFAULT_PLAN and "default" in note, note
    # default: a module only the old plan has falls back, loudly
    p, note = G.resolve_plan(None, {}, "ot_s81dv_xfin")
    assert p == G.STALE_PLAN and note.startswith("WARNING"), note
    # explicit stale plan: honoured, loudly
    p, note = G.resolve_plan(str(G.STALE_PLAN), {}, "dsdv_eng_rr_e")
    assert p == G.STALE_PLAN and note.startswith("WARNING"), note
    # explicit other plan and recipe plan are silent, and the recipe wins
    p, note = G.resolve_plan("/x/plan.json", {}, "m")
    assert str(p) == "/x/plan.json" and not note.startswith("WARNING"), note
    p, note = G.resolve_plan("/x/plan.json", {"plan": "a/b.json"}, "m")
    assert p == G.REPO / "a/b.json" and "recipe" in note, note
    # slice default: only the recipe's own slice file
    rec = {"ref_tile": "physical/die_plan/s81/h2_2249/coll_e"}
    assert G.default_master_slice(rec, "dsfd_coll_lane_e_safe8_ntf")
    assert G.default_master_slice(rec, "other") is None and G.default_master_slice({}, "x") is None
    print("PASS")


if __name__ == "__main__":
    main()
