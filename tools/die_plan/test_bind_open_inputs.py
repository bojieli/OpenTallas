"""BIND-UNDRIVEN-IN 11-23: strict bind sees leaf input ports the as-built instance leaves unconnected."""
import json
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import bind_elab as E  # noqa: E402
from test_bind import EX, HAVE_YOSYS, plan_copy, report  # noqa: E402

SHARE = """module share #(parameter integer RXW = 1043)(
 input wire clk, input wire [RXW-1:0] phy_rx, output wire q);
 assign q = ^phy_rx;
endmodule
"""


def binder(tmp_path, ports, params=None, leaf=None, ytype="share", module="share", ties=(), dead=(), bumps=None):
    (tmp_path / "share.sv").write_text(SHARE)
    c = E.Cell("p0.u", module, dict(params or {}), dict(ports), {k: "input" for k in ports}, "leaf", ytype)
    B = bind.Binder.__new__(bind.Binder)
    B.F = NS(cells=[c], leaf_inputs=leaf if leaf is not None else {"share": ({"clk": 1, "phy_rx": 1043}, False)})
    B.G = NS(kind=["leaf"], dirs=[{k: "input" for k in ports}])
    B.ab = dict(rtl_roots=[], files=["share.sv"])
    B.base = str(tmp_path)
    B.cpart, B.parts = {0: "P0"}, {"P0": dict(type="T")}
    B.R = NS(part_of=lambda p: "P0" if p.startswith("p0") else None)
    B.param_defaults = {("share", "share"): {"RXW": 1043}}
    B._leaf_master0, B._leaf_before = {"p0.u": "share"}, {}
    B.rewire, B.errors, B.warns = {}, [], []
    B.proven_dead = NS(allows=lambda t, cell, pn, i, d=(): (pn, i) in dead)
    from dead_inputs import DeclaredTies
    B.declared_ties = DeclaredTies(dict(declared_ties=list(ties)))
    B._bumps = {"P0": bumps} if bumps else {}
    return B


def audit(B):
    cnt = defaultdict(int)
    B.open_input_audit(cnt)
    return cnt


def bits(n):
    return list(range(10, 10 + n))


def test_absent_port_fails(tmp_path):
    B = binder(tmp_path, {"clk": [1]})
    assert audit(B)["undriven"] == 1043
    assert B.errors[0].startswith("UNDRIVEN_OPEN p0.u.phy_rx[1042:0] (share, type T): 1043")


def test_override_width_is_the_instance_width(tmp_path):
    """QC coll_ucie: RXW=597 with 597 bits connected is fully driven (the stub's default 1043 is not its width)"""
    B = binder(tmp_path, {"clk": [1], "phy_rx": bits(597)}, {"RXW": 597})
    assert audit(B)["undriven"] == 0 and not B.errors


def test_override_wider_than_default_is_seen(tmp_path):
    B = binder(tmp_path, {"clk": [1], "phy_rx": bits(1043)}, {"RXW": 1050})
    assert audit(B)["undriven"] == 7 and B.open_inputs[0]["bits"] == list(range(1043, 1050))


def test_narrow_connection_without_override_fails(tmp_path):
    B = binder(tmp_path, {"clk": [1], "phy_rx": bits(1000)})
    assert audit(B)["undriven"] == 43


def test_dead_and_bump_are_declarations(tmp_path):
    B = binder(tmp_path, {"clk": [1]}, dead={("phy_rx", i) for i in range(1043)})
    c = audit(B)
    assert c["undriven"] == 0 and c["open_input_dead"] == 1043
    B = binder(tmp_path, {"clk": [1]}, bumps=[dict(ci=0, pin="phy_rx", dir="input")])
    c = audit(B)
    assert c["undriven"] == 0 and c["open_input_bump"] == 1043


def test_bad_bump_declaration_excuses_nothing_and_does_not_stop_the_audit(tmp_path):
    B = binder(tmp_path, {"clk": [1]})

    def bad():
        raise bind.BindError("bump_ports bad")
    B.bump_pins = bad
    assert audit(B)["undriven"] == 1043


def test_declared_tie_is_connected_and_partial_tie_is_not_enough(tmp_path):
    row = dict(types=["T"], module="share", port="phy_rx", bits=[0, 1042], value="0", proof="x")
    B = binder(tmp_path, {"clk": [1]}, ties=[row])
    c = audit(B)
    assert c["undriven"] == 0 and c["open_input_tied"] == 1043 and B.F.cells[0].ports["phy_rx"] == ["0"] * 1043
    B = binder(tmp_path, {"clk": [1]}, ties=[dict(row, bits=[0, 1000])])
    assert audit(B)["undriven"] == 1043 and "phy_rx" not in B.F.cells[0].ports


def test_source_leaf_of_a_composed_core_is_judged(tmp_path):
    B = binder(tmp_path, {"clk": [1]}, ytype="comp", module="comp")
    B._leaf_before = {"p0.m": E.Cell("p0.m", "share", {}, {"clk": [1]}, {}, "leaf", "share")}
    B._leaf_master0["p0.m"] = "share"
    c = audit(B)
    assert c["undriven"] == 1043 and c["open_input_derived"] == 1 and B.open_inputs[0]["source_leaf"]
    assert not B.open_inputs_unjudged


def test_leaf_without_any_interface_is_listed(tmp_path):
    B = binder(tmp_path, {"clk": [1]}, ytype="ghost", module="ghost")
    assert audit(B)["undriven"] == 0
    assert len(B.open_inputs_unjudged) == 1 and B.warns[0].startswith("OPEN_INPUT_UNJUDGED 1 ")


def tiny(tmp_path, edit_plan=lambda p: None, cut=True):
    plan, out = plan_copy(tmp_path, "die_plan.json", edit_plan), tmp_path / "o"
    assert bind.main(["elab", str(plan), "--out", str(out), "--mem", "4"]) == 0
    if cut:
        f = out / "asbuilt.json"
        y = json.loads(f.read_text())
        n = 0
        for m in y["modules"].values():
            for c in (m.get("cells") or {}).values():
                if c["type"].endswith("lf_b") or "\\lf_b" in c["type"]:
                    n += c["connections"].pop("id", None) is not None
        assert n == 1 or n == 2
        f.write_text(json.dumps(y))
    rc = bind.main(["bind", str(plan), "--out", str(out), "--mem", "4", "--strict"])
    return rc, report(out), out


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys")
def test_strict_bind_fails_on_an_omitted_leaf_input(tmp_path):
    rc, r, out = tiny(tmp_path)
    oi = json.loads((out / "bind_open_inputs.json").read_text())
    assert rc != 0 and r["proof"]["undriven"] == oi["n_undriven"] == 8 and r["proof"]["unbound"] >= 8
    assert any(e.startswith("UNDRIVEN_OPEN ") and ".id[3:0] (lf_b" in e for e in r["errors"])


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys")
def test_declared_tie_on_an_omitted_input_is_emitted(tmp_path):
    def edit(p):
        p["asbuilt"]["declared_ties"] = [dict(types=list(p["partition_types"]), module="lf_b", port="id", bits=[0, 3],
                                              value="0", proof="test")]
    rc, r, out = tiny(tmp_path, edit)
    assert r["proof"]["undriven"] == 0 and not any("UNDRIVEN_OPEN" in e for e in r["errors"])
    assert json.loads((out / "bind_open_inputs.json").read_text())["tied"] == 8
    body = (out / "rtl" / "bt_ta.sv").read_text()
    i = body.index("lf_b u_u_b")
    assert ".id(" in body[i:i + 600], body[i:i + 600]
