"""die_trial STA stand-ins carry every port the die top connects (DIE-FT 2026-10-25): the QC die STA linked
1844 instance pins (rst_o_<k> / start_i / start_o_<k>, plus extra buses of variant types sharing one module) to
nothing (OpenSTA Warning 201), so the reset / START wavefront seams were untimed.  Every reset / START input now gets a
face flop (through the boundary-hold contract cell), every reset / START output a face-flop QN, and variant types
sharing a module get ONE union stand-in."""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta as D  # noqa: E402
import die_trial as T  # noqa: E402
import gen_rtl  # noqa: E402
import schema as S  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def plan(variant=False):
    raw = copy.deepcopy(TINY)
    raw["reset"].update(release="wavefront", start="broadcast")
    for ty in raw["partition_types"].values():
        ty.pop("sources", None)
    if variant:                                   # pm2 = a second plan type under the SAME module as pm1
        raw["partition_types"]["mid2"] = copy.deepcopy(raw["partition_types"]["mid"])
        next(p for p in raw["partitions"] if p["name"] == "pm2")["type"] = "mid2"
    assert S.validate(raw) == []
    return S.Plan(raw)


def standins(P):
    return {mod: T.standin_netlist(P, tns[0], also=tns[1:]) for mod, tns in T.standin_groups(P).items()}


def module_ports(v):
    return dict((n, d) for d, n in re.findall(r"^  (input|output) (?:\[\d+:0\] )?(\w+);", v, re.M))


def die_top_conns(P):
    top = gen_rtl.die_top(P, gen_rtl.bus_epochs(P), {})
    for m in re.finditer(r"^    (\S+) (\S+) \(\n(.*?)\n    \);", top, re.M | re.S):
        yield m.group(1), m.group(2), re.findall(r"\.(\w+)\(", m.group(3))


@pytest.mark.parametrize("variant", [False, True])
def test_every_die_top_connection_links(variant):
    P = plan(variant)
    sv = standins(P)
    seen = set()
    for mod, inst, conns in die_top_conns(P):
        ports = module_ports(sv[mod][0])
        missing = [c for c in conns if c not in ports]
        assert not missing, (inst, missing)       # == OpenSTA Warning 201 count 0
        seen |= {c for c in conns if re.fullmatch(r"rst_o_\d+|start_i|start_o_\d+", c)}
    assert {"start_i", "rst_o_0", "start_o_0"} <= seen


def test_reset_start_face_flops():
    P = plan()
    bh = D.bhold_cell(T.gen_phys.seam_hold(P)["seam_ps"])
    for mod, (v, k) in standins(P).items():
        ports = module_ports(v)
        assert ports["arst_n"] == "input"
        for n, d in ports.items():
            if n == "arst_n" or n == "start_i":
                # input: port -> contract cell -> face flop D, clocked from a contract-latency tap net
                h = re.search(rf"{bh} (h\d+) \(\.A\({n}\), \.Y\((d\d+)\)\);", v)
                assert h and re.search(rf"\.CLK\(ck_\w+\), \.D\({h.group(2)}\)", v), (mod, n)
            elif re.fullmatch(r"(rst|start)_o_\d+", n):
                assert d == "output" and re.search(rf"\.CLK\(ck_\w+\), \.D\(1'b0\), \.QN\({n}\)\);", v), (mod, n)
        assert len(re.findall(r"\.CLK\(", v)) == k
        # standin_add_contract (legacy clock form) still converts the bare netlist, reset / START inputs included
        tn = T.standin_groups(P)[mod][0]
        bare, kb = T.standin_netlist(P, tn, hold_contract=False, clock_contract=False)
        ref, _ = T.standin_netlist(P, tn, clock_contract=False)
        conv, nin = T.standin_add_contract(bare, T.gen_phys.seam_hold(P)["seam_ps"])
        assert kb == k and conv.count(bh) == ref.count(bh) == v.count(bh) == nin
        assert re.search(rf"{bh} h\d+ \(\.A\(arst_n\)", conv)


def test_union_refuses_direction_conflict():
    P = plan(variant=True)
    b = next(x for x in P.types["mid2"]["buses"] if x["dir"] == "out")
    b["dir"] = "in"
    with pytest.raises(ValueError, match="bus"):
        T.standin_netlist(P, "mid", also=["mid2"])
