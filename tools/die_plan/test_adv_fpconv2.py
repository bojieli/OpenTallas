"""tests of adv_fpconv2.py (FP-CONVERGE-S81): pass case and mutant for each check."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fpconv2 as F2  # noqa: E402
import plan_advisory as PA  # noqa: E402


def core(inst, x, y, w, h):
    return {"inst": inst, "origin_um": [x, y], "outline_um": [w, h]}


def base():
    t = {"outline_um": [1000.0, 800.0], "hard_cores": [core("a", 100, 100, 200, 200)],
         "internal_stations": [{"bits": 8, "regs_um": [[500.0, 500.0]]}],
         "ft_slots": [{"name": "ft0", "width": 4, "regs_um": [[50.0, 20.0], [50.0, 700.0]], "bit_site_cell_um": [1.0, 1.0],
                       "bit_sites_um": [[[60.0, 30.0]]]}]}
    return {"partition_types": {"T": t}}


def n(name, raw):
    return [x for x in F2.findings_by_check[name](raw, "p.json") if "summary" not in x]


def test_rank_pile():
    r = base()
    assert n("RANK-PILE-PINFACE", r) == []
    r["partition_types"]["T"]["internal_stations"] = [{"bits": 2100, "regs_um": [[305.0, 150.0]]}]   # 5 um from core face a
    assert len(n("RANK-PILE-PINFACE", r)) == 1
    r["partition_types"]["T"]["internal_stations"] = [{"bits": 2100, "regs_um": [[700.0, 600.0]]}]   # same pile, no core face near
    assert n("RANK-PILE-PINFACE", r) == []


def test_ft_site_legal():
    r = base()
    assert n("FT-SITE-LEGAL", r) == [] and F2.legal_gate(r) == []
    t = r["partition_types"]["T"]
    t["ft_slots"][0]["regs_um"].append([1100.0, 5.0])
    assert len(n("FT-SITE-LEGAL", r)) == 1 and len(F2.legal_gate(r, {"T"})) == 1 and F2.legal_gate(r, {"U"}) == []
    r = base()
    r["partition_types"]["T"]["ft_slots"][0]["regs_um"].append([150.0, 150.0])                        # inside core a
    assert "1 in a core" in n("FT-SITE-LEGAL", r)[0]
    r = base()
    r["partition_types"]["T"]["ft_slots"][0]["regs_um"].append([50.0, 20.0])                          # duplicate reg
    assert "1 duplicate" in n("FT-SITE-LEGAL", r)[0]


def test_placed_reach(tmp_path):
    p = tmp_path / "placed_scan.json"
    p.write_text(json.dumps({"bits_over_cycle": 0, "bits_over_reach": 500, "limit_um": 405, "cycle_um": 580}))
    assert F2.placed_reach(p)[0] is False
    p.write_text(json.dumps({"bits_over_cycle": 3064, "bits_over_reach": 7813, "limit_um": 405, "cycle_um": 580, "groups_need_station": 76}))
    stop, line = F2.placed_reach(p)
    assert stop and "STOP" in line and line.startswith("WARN ADV-PLACED-REACH")
    assert F2.placed_reach_decision(p, "route", {}) [0] is False                                       # report-only by default
    assert F2.placed_reach_decision(p, "route", {"OT_PLACED_REACH_STOP": "1"})[0] is True
    assert F2.placed_reach_decision(p, "place", {"OT_PLACED_REACH_STOP": "1"})[0] is False             # only route-goal kits


def test_launch_scope():
    k = dict(type="T", goal="route", bound_plan_sha="a" * 40, wave_plan_sha="a" * 40, touched_types=["T"], signed=False,
             open_functional_row=False, fp_clean=True)
    assert F2.launch_scope(k) == []
    assert any("!=" in x for x in F2.launch_scope(dict(k, bound_plan_sha="b" * 40)))
    assert any("outside" in x for x in F2.launch_scope(dict(k, touched_types=["U"])))
    assert any("not FP-clean" in x for x in F2.launch_scope(dict(k, fp_clean=False)))
    assert F2.launch_scope(dict(k, goal="place", fp_clean=False)) == []


def test_row_ledger(tmp_path):
    ap = {"ops_a.json": "s" * 64, "ops_b.json": "t" * 64, "ops_c.json": "u" * 64}
    led = {"ops_a.json": dict(sha256="s" * 64, owner="X", types="T", pre_verdict="PASS"),
           "ops_b.json": dict(sha256="z" * 64, owner="", types="T", pre_verdict="PASS")}
    out = F2.row_ledger(ap, led)
    assert any("ops_c.json" in x and "not in the ledger" in x for x in out)
    assert any("ops_b.json" in x and "ledger sha" in x for x in out) and any("lacks owner" in x for x in out)
    assert not any("ops_a.json" in x for x in out)
    tsv = tmp_path / "l.tsv"
    tsv.write_text("file\tsha256\towner\ttypes\tpre_verdict\nops_a.json\t" + "s" * 64 + "\tX\tT\tPASS\n")
    assert list(F2.read_ledger(tsv)) == ["ops_a.json"]


def test_registered_and_runs_on_plan_advisory():
    names = [c[0] for c in PA.CHECKS]
    assert "RANK-PILE-PINFACE" in names and "FT-SITE-LEGAL" in names
    out = PA.run(base(), "p.json", checks=["RANK-PILE-PINFACE", "FT-SITE-LEGAL"], jobs=1)
    assert any("summary 0 types" in x for x in out)
