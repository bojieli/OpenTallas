"""C-STRAP-REACH: HEAD count-strap groups seated at their own load cluster; the reach / opposite-face check.
Synthetic one-type plan + published RTL (no tool tree needed), plus mutants: each mutation of the checker / seater must fail _core."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import head_count_strap_reach as R  # noqa: E402
SRC = (HERE / "head_count_strap_reach.py").read_text()
SITES_SRC = (HERE / "head_count_strap_sites.py").read_text()

SV = """
module ot_s81hd_syn (input clk);
    ot_dp_clk_landing_cas #(.W(5)) u_cland_a_i (
        .fclk(fclk_in_a_i), .t_rst_n(cland_fstart_in_a_i), .strap_k(strap_ca_k_a_i), .d({cland_dn_ready_a_i, x}), .q(q));
    ot_dp_clk_landing_cas #(.W(5)) u_cland_b_i (
        .fclk(fclk_in_b_i), .t_rst_n(cland_fstart_in_b_i), .strap_k(strap_ca_k_b_i), .d({cland_dn_ready_b_i, y}), .q(r));
    ot_dp_landing_origin u_cland_origin (
        .clk(clk), .p_start(cland_tstart_in), .strap_efall(strap_ca_efall), .strap_pad(strap_ca_pad), .start(s));
endmodule
"""


def plan_type(a_sites, b_sites, ef_sites=None, pad_sites=None):
    def pin(n, x, y):
        return {"name": n, "xy_um": [x, y]}
    return {"module": "ot_s81hd_syn", "outline_um": [1000.0, 600.0],
            "clock": {"start_capture_um": [500.0, 300.0], "landing_contract": {"pins": [
                pin("fclk_in_a_i", 2.0, 100.0), pin("cland_fstart_in_a_i", 2.0, 104.0), pin("cland_dn_ready_a_i", 2.0, 108.0),
                pin("fclk_in_b_i", 998.0, 500.0), pin("cland_fstart_in_b_i", 998.0, 504.0), pin("cland_dn_ready_b_i", 998.0, 508.0),
                pin("cland_tstart_in", 20.0, 20.0)]}},
            "count_straps": [
                {"name": "strap_ca_k_a_i", "width": 2, **({"sites_um": a_sites} if a_sites else {})},
                {"name": "strap_ca_k_b_i", "width": 2, **({"sites_um": b_sites} if b_sites else {})},
                {"name": "strap_ca_efall", "width": 1, **({"sites_um": ef_sites} if ef_sites else {})},
                {"name": "strap_ca_pad", "width": 1, **({"sites_um": pad_sites} if pad_sites else {})}]}


def _core(mod):
    """the facts every working build must show; the mutants must break at least one"""
    t = plan_type([[8.64, 100.0], [8.64, 104.0]], [[8.64, 100.0], [8.64, 104.0]], [[500.0, 296.0]], [[20.0, 590.0]])
    an = mod.group_anchors(t, SV)
    assert set(an) == {"strap_ca_k_a_i", "strap_ca_k_b_i", "strap_ca_efall", "strap_ca_pad"}
    assert abs(an["strap_ca_k_a_i"][0] - 2.0) < 1e-6 and abs(an["strap_ca_k_a_i"][1] - 104.0) < 1e-6      # centroid of its 3 pins
    assert an["strap_ca_efall"][:2] == (500.0, 300.0)                                                    # start_capture_um
    st = {r["strap"]: r["status"] for r in mod.group_findings(t, an)}
    assert st == {"strap_ca_k_a_i": "PASS", "strap_ca_k_b_i": "REPRODUCE", "strap_ca_efall": "PASS", "strap_ca_pad": "REPRODUCE"}
    # opposite face only: Manhattan 380 < limit, seat at the E face, anchor at the W face
    t3 = {"module": "m", "outline_um": [400.0, 400.0], "clock": {"start_capture_um": [10.0, 200.0]},
          "count_straps": [{"name": "strap_ca_pad", "width": 1, "sites_um": [[390.0, 200.0]]}]}
    r3 = mod.group_findings(t3, {"strap_ca_pad": (10.0, 200.0, "x")})[0]
    assert r3["status"] == "REPRODUCE" and r3["opposite_face"]
    t4 = {"module": "m", "outline_um": [400.0, 400.0], "count_straps": [{"name": "strap_ca_pad", "width": 1, "sites_um": [[200.0, 200.0]]}]}
    assert mod.group_findings(t4, {})[0]["status"] == "NOEVIDENCE"
    assert mod.group_findings(plan_type(None, None), an)[0]["status"] == "NOSEAT"
    t5 = {"module": "m", "outline_um": [1000.0, 1000.0], "count_straps": [{"name": "s", "width": 2, "sites_um": [[10.0, 10.0], [700.0, 10.0]]}]}
    assert mod.group_findings(t5, {"s": (10.0, 10.0, "x")})[0]["status"] == "REPRODUCE"     # one far bit is enough


def test_core():
    _core(R)


def _mutant(src, old, new):
    assert old in src, old
    spec = importlib.util.spec_from_loader("mut_reach", loader=None)
    mod = importlib.util.module_from_spec(spec)
    exec(compile(src.replace(old, new, 1), "mut", "exec"), mod.__dict__)
    return mod


MUTANTS = [
    ("limit_disabled", "LIMIT_UM = 405.0", "LIMIT_UM = 4050.0"),
    ("opposite_dropped", "row[\"status\"] = \"REPRODUCE\" if (max(d) > limit or opp)", "row[\"status\"] = \"REPRODUCE\" if (max(d) > limit)"),
    ("mean_not_max", "row[\"status\"] = \"REPRODUCE\" if (max(d) > limit", "row[\"status\"] = \"REPRODUCE\" if (min(d) > limit"),
    ("single_pin_anchor", "xs = [pins[i] for i in sorted(ids) if i in pins]\n            if xs:\n                out[m.group(1)] = (sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs), f\"{inst} landing pins x{len(xs)}\")",
     "xs = [pins[i] for i in sorted(ids) if i in pins][:1]\n            if xs:\n                out[m.group(1)] = (xs[0][0], xs[0][1], f\"{inst} landing pins x{len(xs)}\")"),
    ("efall_pin_not_capture", "sc = ck.get(\"start_capture_um\")", "sc = None"),
    ("faces_same", "return {fa, fb} in ({\"W\", \"E\"}, {\"S\", \"N\"})", "return False"),
    ("noseat_as_pass", "row[\"status\"] = \"NOSEAT\"", "row[\"status\"] = \"PASS\""),
]


@pytest.mark.parametrize("name,old,new", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_mutant_killed(name, old, new):
    with pytest.raises(AssertionError):
        _core(_mutant(SRC, old, new))


def test_check_cli_blocks(tmp_path, capsys):
    (tmp_path / "published").mkdir()
    (tmp_path / "published" / "ot_s81hd_syn.sv").write_text(SV)
    bad = {"partition_types": {"hd_syn": plan_type([[8.64, 100.0], [8.64, 104.0]], [[8.64, 100.0], [8.64, 104.0]], [[500.0, 296.0]], [[20.0, 590.0]])}}
    (tmp_path / "plan.json").write_text(json.dumps(bad))
    assert R.main(["check", str(tmp_path / "plan.json")]) == 1
    good = {"partition_types": {"hd_syn": plan_type([[8.64, 100.0], [8.64, 104.0]], [[990.0, 500.0], [990.0, 504.0]], [[500.0, 296.0]], [[500.0, 304.0]])}}
    (tmp_path / "plan.json").write_text(json.dumps(good))
    assert R.main(["check", str(tmp_path / "plan.json")]) == 0
    lines = R.findings_for_pre(bad, tmp_path / "plan.json", level="FAIL")
    assert lines and lines[0].startswith("FAIL STRAP-REACH hd_syn: 2/4")
    assert R.findings_for_pre(good, tmp_path / "plan.json", level="FAIL") == []


def test_seat_groups_rules():
    import head_count_strap_sites as CS
    blocked = [[0.0, 90.0, 20.0, 110.0]]
    occupied = [(25.92, 100.0)]
    out = CS.seat_groups([("a", 6, (2.0, 100.0)), ("b", 1, (2.0, 100.0))], 1000.0, 600.0, blocked, occupied)
    pts = [tuple(p) for v in out.values() for p in v]
    assert len(out["a"]) == 6 and len(out["b"]) == 1 and len(set(pts)) == 7
    for x, y in pts:
        assert abs(x / 4.32 - round(x / 4.32)) < 1e-6 and abs(y / 4.32 - round(y / 4.32)) < 1e-6
        assert not (0.0 <= x <= 20.0 and 90.0 <= y <= 110.0)            # blocked rect
        assert not (abs(x - 25.92) < 2.16 and abs(y - 100.0) < 2.16)    # occupied pin
        assert abs(x - 2.0) + abs(y - 100.0) < 60.0                    # at its own anchor
    again = CS.seat_groups([("a", 6, (2.0, 100.0)), ("b", 1, (2.0, 100.0))], 1000.0, 600.0, blocked, [(25.92, 100.0)])
    assert again == out
    with pytest.raises(ValueError, match="no room"):
        CS.seat_groups([("z", 3, (50.0, 50.0))], 30.0, 30.0, [[0.0, 0.0, 30.0, 30.0]], [])


SEAT_MUTANTS = [
    ("blocked_ignored", "if any(a <= x <= c and b <= y <= e for a, b, c, e in blocked):\n                    continue", "if False:\n                    continue"),
    ("occupied_ignored", "if any(abs(x - a) < 2.16 and abs(y - b) < 2.16 for a, b in occupied):", "if False:"),
    ("farthest_first", "for d, x, y in cand:", "for d, x, y in reversed(cand):"),
]


@pytest.mark.parametrize("name,old,new", SEAT_MUTANTS, ids=[m[0] for m in SEAT_MUTANTS])
def test_seat_mutant_killed(name, old, new, monkeypatch):
    assert old in SITES_SRC, old
    src = SITES_SRC.replace(old, new, 1)
    # seat_groups only needs the stdlib + the reach module: run the mutated file with the heavy imports stubbed
    src = src.replace("import gen_phys as G\nimport schema as S\n", "G = S = None\n")
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("mut_sites", loader=None))
    mod.__dict__["__file__"] = str(HERE / "head_count_strap_sites.py")
    exec(compile(src, "mut_sites", "exec"), mod.__dict__)
    monkeypatch.setitem(sys.modules, "head_count_strap_sites", mod)
    with pytest.raises((AssertionError, ValueError, TypeError)):
        test_seat_groups_rules()
