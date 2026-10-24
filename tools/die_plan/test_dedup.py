"""TYPE-DEDUP transform tests (dedup.py).   python3 -m pytest -q tools/die_plan/test_dedup.py"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import dedup  # noqa: E402
import gen  # noqa: E402
import schema  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan_typegeo.json").read_text())


def part(p, n):
    return next(x for x in p["partitions"] if x["name"] == n)


def port(p, pid):
    return next(x for x in p["ports"] if x["id"] == pid)


def dup_mid(mut=None):
    """pm2 on a copy 'mid_b' of type 'mid' (a near-duplicate a die generator would emit)."""
    p = copy.deepcopy(EX)
    p["partition_types"]["mid_b"] = copy.deepcopy(p["partition_types"]["mid"])
    p["partition_types"]["mid_b"]["module"] = "tiny_mid_part_b"
    part(p, "pm2")["type"] = "mid_b"
    if mut:
        mut(p)
    assert schema.validate(p) == []
    return p


def g0_errors(p):
    R, _ = check.run(p, completeness=True)
    return [i["msg"] for i in R.errors()]


def test_exact_duplicate_merges_and_verifies():
    p = dup_mid()
    rep = dedup.analyze(p)
    assert rep["types_before"] == 4 and rep["types_after"] == 3
    (g,) = rep["exact_groups"]
    assert g["canon"] == "mid" and g["members"][0]["type"] == "mid_b"
    assert g["members"][0]["instances"] == {"pm2": ["R0", "R0"]}
    new, prov = dedup.apply(p, rep)
    assert "mid_b" not in new["partition_types"] and part(new, "pm2")["type"] == "mid"
    assert prov["merged"]["mid_b"]["into"] == "mid" and prov["reordered_ports"] == []
    assert dedup.verify(p, new) == []
    assert g0_errors(new) == []
    # the input is never edited
    assert part(p, "pm2")["type"] == "mid_b" and "mid_b" in p["partition_types"]


def test_different_netlist_not_grouped():
    def mut(p):
        p["partition_types"]["mid_b"]["contents"][0]["module"] = "other_core"
    rep = dedup.analyze(dup_mid(mut))
    assert rep["exact_groups"] == [] and rep["types_after"] == 4


def test_params_difference_is_strap_candidate_not_merged():
    def mut(p):
        p["partition_types"]["mid"]["contents"][0]["params"] = {"IDX": 0}
        p["partition_types"]["mid_b"]["contents"][0]["params"] = {"IDX": 1}
    rep = dedup.analyze(dup_mid(mut))
    assert rep["exact_groups"] == []
    (s,) = rep["strap_candidates"]
    assert s["types"] == ["mid", "mid_b"] and s["params"] == {"u_m": {"IDX": [0, 1]}}


def test_ft_population_family_reported():
    def mut(p):
        t = p["partition_types"]["mid_b"]
        t["ft_slots"] = [s for s in t["ft_slots"] if s["name"] != "fr"]
        # keep the plan valid: r lane goes pb -> pm1 directly is not abutted, so drop it from the example
        p["ports"] = [x for x in p["ports"] if x["id"] not in ("r0", "r1", "r2")]
        p["lanes"] = [x for x in p["lanes"] if x["id"] != "r"]
        for tn in ("src", "sink"):
            p["partition_types"][tn]["buses"] = [b for b in p["partition_types"][tn]["buses"]
                                                 if b["name"] not in ("r_i", "r_o")]
        t2 = p["partition_types"]["mid"]
        t2["ft_slots"] = [s for s in t2["ft_slots"] if s["name"] != "fr"]
        t2["ft_slots"].append(dict(name="fz", in_face="E", out_face="W", width=4, stations=1))
        p["partition_types"]["mid_b"]["ft_slots"].append(dict(name="fz", in_face="E", out_face="W", width=5,
                                                              stations=1))
    p = copy.deepcopy(EX)
    p["partition_types"]["mid_b"] = copy.deepcopy(p["partition_types"]["mid"])
    part(p, "pm2")["type"] = "mid_b"
    mut(p)
    rep = dedup.analyze(p)       # (plan need not validate for the classification)
    assert rep["exact_groups"] == []
    assert rep["ft_population"] and rep["ft_population"][0]["types"] == 2


def test_geometry_mismatch_blocks():
    def mut(p):
        b = next(x for x in p["partition_types"]["mid_b"]["buses"] if x["name"] == "cfg_o")
        b["window_um"] = [610.0, 615.0]
        sb = next(x for x in p["partition_types"]["sink"]["buses"] if x["name"] == "cfg_i")
        sb["window_um"] = [610.0, 615.0]
    p = dup_mid(mut)
    rep = dedup.analyze(p)
    (g,) = rep["exact_groups"]
    assert g["members"] == [] and g["blocked"][0]["type"] == "mid_b"
    assert "c2" in g["blocked"][0]["reason"] or "pin table" in g["blocked"][0]["reason"]
    assert rep["types_after"] == 4


def _order_variant(p):
    """mid / mid_b without ft-slot geometry; x1 / x2 carry port geometry, and pm2's fx_o bits run lsb_high (the sink
    declares x_i lsb_high to match): mid_b's pin table is mid's up to the bit order of fx_o."""
    for tn in ("mid", "mid_b"):
        for s_ in p["partition_types"][tn]["ft_slots"]:
            for k in ("in_window_um", "out_window_um", "layers", "order"):
                s_.pop(k, None)
    geo = dict(face="E", layers=["M6", "M4"], window_um=[400.0, 420.0])
    port(p, "x1").update(geo, order="lsb_low")
    port(p, "x2").update(geo, order="lsb_high")
    next(b for b in p["partition_types"]["sink"]["buses"] if b["name"] == "x_i")["order"] = "lsb_high"
    for pid, src in (("r0", 2592.0), ("r1", 1728.0), ("r2", 864.0)):
        port(p, pid).update(face="W", layers=["M6", "M4"], window_um=[500.0, 510.0])


def test_bit_order_needs_fix_order():
    p = dup_mid(_order_variant)
    assert g0_errors(p) == []
    rep = dedup.analyze(p)
    assert rep["types_after"] == 4 and "pin table" in rep["exact_groups"][0]["blocked"][0]["reason"]
    rep = dedup.analyze(p, fix_order=True)
    assert rep["types_after"] == 3
    new, prov = dedup.apply(p, rep)
    assert prov["reordered_ports"] == ["x2"] and prov["pin_table_touched_types"] == ["sink"]
    assert port(new, "x2")["order"] == "lsb_low"
    assert next(b for b in new["partition_types"]["sink"]["buses"] if b["name"] == "x_i")["order"] == "lsb_low"
    assert dedup.verify(p, new) == []
    assert g0_errors(new) == []
    # the lane / latency netlist is untouched
    assert new["lanes"] == p["lanes"] and new.get("latency") == p.get("latency")


def test_order_parity():
    """port order XOR unit order = mirror flip: two R0 instances sharing a unit force equal orders on x1 / x2; an MX
    instance (E/W pins mirrored) forces opposite orders."""
    p = dup_mid(_order_variant)
    uf, ok, _ = dedup.order_system(p, {q["name"]: (q["type"], q["orient"]) for q in p["partitions"]}, {})
    assert ok
    # parity sanity: x1 XOR x2 must be 0 when pm1 and pm2 share the fx_o unit and both are R0
    parts = {q["name"]: (q["type"], q["orient"]) for q in p["partitions"]}
    parts["pm2"] = ("mid", "R0")
    alias = {("mid_b", "bus:fx_o"): ("mid", "bus:fx_o"), ("mid_b", "bus:fx_i"): ("mid", "bus:fx_i"),
             ("mid_b", "bus:cfg_i"): ("mid", "bus:cfg_i"), ("mid_b", "bus:cfg_o"): ("mid", "bus:cfg_o"),
             ("mid_b", "bus:fr_i"): ("mid", "bus:fr_i"), ("mid_b", "bus:fr_o"): ("mid", "bus:fr_o")}
    uf, ok, _ = dedup.order_system(p, parts, alias)
    assert ok
    a, pa = uf.find(("p", "x1"))
    b, pb = uf.find(("p", "x2"))
    assert a == b and pa == pb
    # an R180 pm2 would mirror the E/W fx pins: the same unit then demands the opposite order -> parity differs
    parts["pm2"] = ("mid", "MX")
    uf, ok, _ = dedup.order_system(p, parts, alias)
    a, pa = uf.find(("p", "x1"))
    b, pb = uf.find(("p", "x2"))
    assert a == b and pa != pb


def test_bound_rtl_gate(tmp_path):
    p = dup_mid()
    (tmp_path / "tiny_mid_part.sv").write_text("// a\nmodule tiny_mid_part(input a); wire [3:0] w; endmodule\n")
    (tmp_path / "tiny_mid_part_b.sv").write_text("// b\nmodule tiny_mid_part_b(input a); wire [3:0] w; endmodule\n")
    rep = dedup.analyze(p, rtl_dirs=[tmp_path])
    assert rep["types_after"] == 3 and rep["exact_groups"][0]["members"][0]["rtl"]["status"] == "same"
    (tmp_path / "tiny_mid_part_b.sv").write_text("module tiny_mid_part_b(input a); wire [4:0] w; endmodule\n")
    rep = dedup.analyze(p, rtl_dirs=[tmp_path])
    assert rep["types_after"] == 4 and "bound RTL differs" in rep["exact_groups"][0]["blocked"][0]["reason"]
    rep = dedup.analyze(p, rtl_dirs=[tmp_path], plan_only=True)
    assert rep["types_after"] == 3 and rep["exact_groups"][0]["members"][0]["rtl"]["status"] == "differs"


def test_cli_apply_writes_copy_and_refuses_inplace(tmp_path):
    p = dup_mid()
    src = tmp_path / "in" / "die_plan.json"
    src.parent.mkdir()
    src.write_text(json.dumps(p))
    out = tmp_path / "out" / "die_plan.json"
    out.parent.mkdir()
    assert gen.main(["dedup", str(src), "--out-plan", str(out)]) == 0
    new = json.loads(out.read_text())
    assert len(new["partition_types"]) == 3
    prov = json.loads((out.parent / "dedup_provenance.json").read_text())
    assert prov["verify"]["exact"] and prov["merged"]["mid_b"]["into"] == "mid"
    assert json.loads(src.read_text()) == p
    assert dedup.main(["apply", str(src), "--out-plan", str(src)]) == 2
