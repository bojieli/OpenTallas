"""Rung 2/3 gates for the V4.1 ROM layer die: integer macro map and packed floorplan."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_floorplan_pack as PK  # noqa: E402

MM = {v: json.loads(p.read_text()) for v, p in PK.MACROMAP.items()}
PACK = {v: json.loads((ROOT / f"results/floorplan/v41_pack_{v}.json").read_text()) for v in PK.MACROMAP}


@pytest.fixture(scope="module")
def built():
    return {v: PK.build(v) for v in PK.MACROMAP}


def test_macromap_payload_matches_prior_audit():
    ref = json.loads((ROOT / "results/floorplan/v41_spill_resolved_dense.json").read_text())
    exp = {(s["stage"], r["rank"]): r["payload_upper_bound_bytes"] for s in ref["stages"] for r in s["ranks"]}
    dies = MM["expanded_woa"]["layer_dies"]
    assert len(dies) == 112
    assert all(d["payload_bytes"] == exp[(d["stage"], d["rank"])] for d in dies)


def test_macromap_integer_and_consistent():
    for mm in MM.values():
        for d in mm["layer_dies"]:
            per_view = {}
            for g in d["macros_by_group"].values():
                for v, n in g.items():
                    assert isinstance(n, int) and n >= 0
                    per_view[v] = per_view.get(v, 0) + n
            assert {k: v for k, v in per_view.items() if v} == d["macros"]
            assert d["physical_macro_bytes"] >= d["payload_bytes"]


def test_busiest_bankmap_names_every_macro_once():
    bm = json.loads((ROOT / "results/floorplan/v41_die_bankmap_busiest_expanded_woa.json").read_text())
    die = next(d for d in MM["expanded_woa"]["layer_dies"]
               if (d["stage"], d["rank"]) == (bm["stage"], bm["rank"]))
    used = {}
    for e in bm["entries"]:
        if e["first"] is None:
            continue
        view, a = e["first"].split("#")
        _, b = e["last"].split("#")
        used.setdefault(view, []).append((int(a), int(b)))
    for view, spans in used.items():
        spans.sort()
        assert spans[0][0] == 0
        assert all(spans[i][1] + 1 == spans[i + 1][0] for i in range(len(spans) - 1))
        assert spans[-1][1] + 1 == die["macros"][view] == bm["macro_totals"][view]


def test_source_pins_current():
    for rec in list(MM.values()) + list(PACK.values()):
        for rel, digest in rec["source_sha256"].items():
            assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel


@pytest.mark.parametrize("variant", sorted(PK.MACROMAP))
def test_pack_regenerates_committed_record(variant):
    rec = PK.run(variant)
    old = PACK[variant]
    for k in ("instances", "soft_regions", "channel_rects", "capacity", "geometry"):
        assert rec[k] == json.loads(json.dumps(old[k])), k


@pytest.mark.parametrize("variant", sorted(PK.MACROMAP))
def test_pack_legal_and_closes_every_die(variant):
    rec = PACK[variant]
    assert rec["legality"]["errors"] == []
    assert rec["capacity"]["closes"] and not rec["capacity"]["overflow"]
    placed = {}
    for name, master, x, y, orient, group in rec["instances"]:
        placed.setdefault(group, {}).setdefault(master, 0)
        placed[group][master] += 1
    for d in MM[variant]["layer_dies"]:
        for g, views in d["macros_by_group"].items():
            for v, n in views.items():
                assert placed.get(g, {}).get(v, 0) >= n, (d["die"], g, v)
    assert rec["channels"]["overflow"] == []
    assert all(s["fits"] for s in rec["area"]["soft_region_fit"])
    assert rec["area"]["die_mm2"] <= 815.0


def test_hbm_phy_abstract_pin_defect_is_recorded():
    rec = PACK["expanded_woa"]
    assert any("ot_hbm3e_phy_v41x_aw30" in d for d in rec["legality"]["abstract_defects"])
    assert rec["legality"]["pin_access_legal"] is False


def _first(P, group):
    return next(m for m in P.hard if m["group"] == group)


def test_checker_rejects_overlap(built):
    B = built["expanded_woa"]
    P = copy.deepcopy(B["P"])
    roms = [m for m in P.hard if m["group"] == "ROM_MAC.expert"]
    roms[1]["x"], roms[1]["y"] = roms[0]["x"] + PK.X_STEP * 10, roms[0]["y"]
    assert any(e.startswith("overlap") for e in PK.legality(P, B["geometry"])["errors"])


def test_checker_rejects_off_grid(built):
    B = built["expanded_woa"]
    P = copy.deepcopy(B["P"])
    m = _first(P, "ROM_MAC.dense_QE")
    m["y"] = round(m["y"] + 0.27, 3)      # on the row grid, 12 nm off the M4 track phase
    errs = PK.legality(P, B["geometry"])["errors"]
    assert any(e.startswith("off_joint_grid") for e in errs)
    assert any(e.startswith("pins_off_track:ot_rom_8192x274_m8") for e in errs)


def test_checker_rejects_outside_die(built):
    B = built["expanded_woa"]
    P = copy.deepcopy(B["P"])
    _first(P, "UCIE")["x"] = B["geometry"]["die_w_um"] - 10
    assert any(e.startswith("outside_die") for e in PK.legality(P, B["geometry"])["errors"])


def test_packer_reports_overflow(monkeypatch):
    real = PK.required_slots

    def more(mm):
        need = real(mm)
        need["ROM_MAC.expert"][PK.WIDE] += 10_000
        return need

    monkeypatch.setattr(PK, "required_slots", more)
    B = PK.build("expanded_woa")
    assert not B["capacity"]["closes"] and B["capacity"]["overflow"]["ROM_MAC.expert"][PK.WIDE] > 0


def test_orfs_record_confirms_placement():
    rec = json.loads((ROOT / "results/floorplan/v41_pack_orfs_check_expanded_woa.json").read_text())
    assert rec["placement_legal"]
    c = rec["check"]
    assert c["overlaps"] == 0 and c["outside_die"] == 0 and c["off_site_grid"] == 0
    assert c["insts"] == len(PACK["expanded_woa"]["instances"])
    assert rec["inputs_sha256"]["macros.tcl"] == PACK["expanded_woa"]["views_sha256"]["v41_pack_expanded_woa_macros.tcl"]


def test_pdn_negative_records_preserved():
    full = json.loads((ROOT / "results/floorplan/v41_pack_orfs_pdn_fulldie_expanded_woa.json").read_text())
    assert full["verdict"].startswith("FAILED_OOM") and not full["pdn_generated"]
    win = json.loads((ROOT / "results/floorplan/v41_pack_orfs_pdn_window_blocks_expanded_woa.json").read_text())
    assert win["pdn"].startswith("status=PASS") and "PSM-0069" in win["psm"][0]
