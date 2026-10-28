"""Unit tests on a synthetic hierarchical netlist (no EDA tools needed).

Run:  python3 -m pytest -q opentools/hier/tests     (or python3 tests/test_ohier.py)
"""
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ohier import abstract as A        # noqa: E402
from ohier import budget as B          # noqa: E402
from ohier import emit as E            # noqa: E402
from ohier import hsta as H            # noqa: E402
from ohier import liberty as L         # noqa: E402
from ohier import netlist as N         # noqa: E402
from ohier import plan as PL           # noqa: E402
from ohier import schema as S          # noqa: E402
from ohier import verify as V          # noqa: E402

LIB = """library (t) {
  cell (INV) { area : 1.0; pin (A) { direction : input; } pin (Y) { direction : output; function : "!A"; } }
  cell (DFF) { area : 4.0; ff (IQ, IQN) { next_state : "D"; clocked_on : "CLK"; }
    pin (D) { direction : input; } pin (CLK) { direction : input; clock : true; }
    pin (Q) { direction : output; } }
  cell (RAM) { area : 400.0; memory () { type : ram; }
    pin (CLK) { direction : input; clock : true; }
    bus (DI) { direction : input; } bus (DO) { direction : output; } }
}
"""
LEF = """MACRO RAM
  CLASS BLOCK ;
  SIZE 10.0 BY 20.0 ;
END RAM
MACRO INV
  CLASS CORE ;
  SIZE 0.2 BY 0.27 ;
END INV
"""


def _lib():
    d = tempfile.mkdtemp()
    lp, fp = os.path.join(d, "t.lib"), os.path.join(d, "t.lef")
    open(lp, "w").write(LIB)
    open(fp, "w").write(LEF)
    cells = L.read_liberty([lp])
    macros = L.read_lef_macros([fp])
    L.mark_macros(cells, macros)
    return cells, macros


def _design(n_blk=6, depth=8):
    """top(clk, din, dout) -> chain of n_blk 'stage' instances, each:
    DFF -> depth x INV -> output; stage 0 and 3 also hold a RAM macro."""
    stage = {"ports": {"clk": {"direction": "input", "bits": [2]},
                       "i": {"direction": "input", "bits": [3]},
                       "o": {"direction": "output", "bits": [10 + depth]}},
             "cells": {}, "netnames": {"clk": {"bits": [2]}, "i": {"bits": [3]},
                                        "o": {"bits": [10 + depth]}}}
    stage["cells"]["r"] = {"type": "DFF", "connections": {"CLK": [2], "D": [3], "Q": [10]}}
    for j in range(depth):
        stage["cells"][f"g{j}"] = {"type": "INV", "connections": {"A": [10 + j], "Y": [11 + j]}}
    mem = dict(stage, cells=dict(stage["cells"]))
    mem["cells"]["ram"] = {"type": "RAM", "connections": {"CLK": [2], "DI": [10, 11], "DO": [40, 41]}}
    mem["cells"]["sink"] = {"type": "DFF", "connections": {"CLK": [2], "D": [40], "Q": [42]}}
    top = {"attributes": {"top": "00000000000000000000000000000001"},
           "ports": {"clk": {"direction": "input", "bits": [2]},
                     "din": {"direction": "input", "bits": [3]},
                     "dout": {"direction": "output", "bits": [100 + n_blk]}},
           "cells": {}, "netnames": {"clk": {"bits": [2]}, "din": {"bits": [3]}}}
    prev = 3
    for b in range(n_blk):
        nxt = 101 + b
        top["cells"][f"u{b}"] = {"type": "mem_stage" if b in (0, 3) else "stage",
                                 "connections": {"clk": [2], "i": [prev], "o": [nxt]}}
        top["netnames"][f"link{b}"] = {"bits": [nxt]}
        prev = nxt
    # tie-off cell to exercise constants
    top["cells"]["tie"] = {"type": "INV", "connections": {"A": ["0"], "Y": [200]}}
    return {"modules": {"top": top, "stage": stage, "mem_stage": mem}}


def _plan(k=3):
    cells, macros = _lib()
    data = _design()
    nl = N.flatten(data, "top", cells)
    o = PL.Options(k=k, cap_cells=40, period_ps=500, latency_ps=50, util=0.5, channel_um=2.0,
                   die_margin_um=2.0, unit_max_cells=12)
    plan, leaf_part, part_ports = PL.build_plan(nl, cells, macros, o)
    return cells, macros, data, nl, o, plan, leaf_part, part_ports


def test_liberty():
    cells, macros = _lib()
    assert cells["DFF"].sequential and not cells["INV"].sequential
    assert cells["INV"].pins == {"A": "input", "Y": "output"}
    assert cells["RAM"].is_macro and cells["RAM"].area == 400.0
    assert "CLK" in cells["DFF"].clock_pins
    assert macros["RAM"].width == 10.0 and macros["RAM"].height == 20.0


def test_flatten():
    cells, _ = _lib()
    nl = N.flatten(_design(), "top", cells)
    # 6 stages x (1 DFF + 8 INV) + 2 x (RAM + sink DFF) + tie
    assert len(nl.leaves) == 6 * 9 + 2 * 2 + 1
    assert nl.tree.n_macros == 2
    pins = nl.net_pins()
    clk = nl.ports["clk"]["bits"][0]
    assert len(pins[clk]) == 6 + 2 * 2       # every DFF + RAM clock
    names = {lf.name for lf in nl.leaves}
    assert "u3.ram" in names and "u5.g7" in names


def test_plan_regions_pins_budgets():
    cells, macros, data, nl, o, plan, leaf_part, part_ports = _plan(3)
    assert len(plan["regions"]) == 3
    assert S.validate(plan) == []
    assert plan["metrics"]["floorplan_macro_fit"]
    for r in plan["regions"]:
        assert r["cells"] <= o.cap_cells
        assert r["clock_region"] == r["id"]
    # each partition fully inside the die, pins on its own boundary
    regs = {r["id"]: r["bbox_um"] for r in plan["regions"]}
    for p in plan["pins"]:
        x0, y0, x1, y1 = regs[p["region"]]
        x, y = p["xy_um"]
        assert (abs(x - x0) < 1e-6 or abs(x - x1) < 1e-6 or abs(y - y0) < 1e-6 or abs(y - y1) < 1e-6)
        assert x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6
    # pins on one edge are at least one pitch apart
    by_edge = {}
    for p in plan["pins"]:
        by_edge.setdefault((p["region"], p["edge"]), []).append(p["offset_um"])
    for offs in by_edge.values():
        offs.sort()
        assert all(b - a >= o.pin_pitch_um - 1e-6 for a, b in zip(offs, offs[1:]))
    # a chain of stages: few crossing bits
    assert 1 <= plan["metrics"]["crossing_bits"] <= 4
    # budgets add up
    for b in plan["budgets"]:
        assert abs(b["src_budget_ps"] + b["wire_ps"] + b["dst_budget_ps"] - b["period_ps"]) < 0.5
    sdcs = PL.partition_sdcs(plan, part_ports, o)
    for txt in sdcs.values():
        assert "create_clock" in txt and "[get_ports {clk}]" in txt


def _read_emitted(text_by_module, top):
    """Tiny reader for the emitter's own Verilog format -> Yosys-like JSON."""
    mods = {}
    for text in text_by_module:
        for m in re.finditer(r"module (\S+) \((.*?)\);(.*?)endmodule", text, re.S):
            name, body = m.group(1).lstrip("\\"), m.group(3)
            bits = {}
            nxt = [2]

            def bit(sig):
                s = sig.strip()
                if s.startswith("1'b"):
                    return s[3:]
                if s not in bits:
                    bits[s] = nxt[0]
                    nxt[0] += 1
                return bits[s]

            ports = {}
            for d in re.finditer(r"^\s*(input|output)(?: \[(\d+):0\])? (\S+);", body, re.M):
                w = int(d.group(2)) + 1 if d.group(2) else 1
                pn = d.group(3).lstrip("\\")
                ports[pn] = {"direction": d.group(1),
                             "bits": [bit(f"{pn}[{i}]" if w > 1 else pn) for i in range(w)]}
            cells = {}
            for c in re.finditer(r"^\s*(\S+) (\\\S+ |\S+) \((.*)\);$", body, re.M):
                if c.group(1) in ("input", "output", "wire", "assign", "module"):
                    continue
                conns = {}
                for pc in re.finditer(r"\.(\w+)\((\{[^}]*\}|[^)]*)\)", c.group(3)):
                    e = pc.group(2)
                    sigs = [s.strip().lstrip("\\") for s in e.strip("{}").split(",")] if e.startswith("{") \
                        else [e.strip().lstrip("\\")]
                    conns[pc.group(1)] = [bit(s) for s in reversed(sigs)]
                cells[c.group(2).strip().lstrip("\\")] = {"type": c.group(1), "connections": conns}
            for a in re.finditer(r"assign (\S+) = (\S+);", body):
                pass   # no aliases in the synthetic design
            attrs = {"top": "1"} if name == top else {}
            mods[name] = {"attributes": attrs, "ports": ports, "cells": cells, "netnames": {}}
    return {"modules": mods}


def test_emit_is_structurally_equivalent():
    cells, macros, data, nl, o, plan, leaf_part, part_ports = _plan(3)
    texts = [E.top_verilog(nl, [r["module"] for r in plan["regions"]], part_ports)]
    for r in plan["regions"]:
        texts.append(E.partition_verilog(nl, leaf_part, r["id"], r["module"], part_ports[r["id"]]))
    part = _read_emitted(texts, "top")
    res = V.compare(data, part, "top", cells)
    assert res["equivalent"], res
    flat = _read_emitted([E.flat_verilog(nl)], "top")
    assert V.compare(data, flat, "top", cells, strip=r"^$")["equivalent"]


def test_verify_catches_a_swap():
    cells, macros, data, nl, o, plan, leaf_part, part_ports = _plan(3)
    texts = [E.top_verilog(nl, [r["module"] for r in plan["regions"]], part_ports)]
    for r in plan["regions"]:
        texts.append(E.partition_verilog(nl, leaf_part, r["id"], r["module"], part_ports[r["id"]]))
    part = _read_emitted(texts, "top")
    mod = next(m for n, m in part["modules"].items() if n.endswith("_P0"))
    c = next(c for c in mod["cells"].values() if c["type"] == "INV" and isinstance(c["connections"]["A"][0], int))
    c["connections"]["A"] = ["1"]
    assert not V.compare(data, part, "top", cells)["equivalent"]


def test_levelize():
    cells, _ = _lib()
    nl = N.flatten(_design(depth=8), "top", cells)
    arr, req, _ = B.levelize(nl, cells)
    out0 = nl.ports["dout"]["bits"][0]
    assert arr[out0] == 8        # 8 inverters after the last DFF
    din = nl.ports["din"]["bits"][0]
    assert req[din] == 0         # din feeds a DFF directly


def test_sta_parse_and_correlate():
    txt = """Endpoint                               Required    Arrival     Slack
--------------------------------------------------------------------
u_top_P0/a.b.r/D (DFF)   900.0  850.0  50.0
c.d.r/D                    900.0  910.5  -10.5
"""
    e = H.parse_end(txt)
    assert len(e) == 2
    a = {H.norm(k): v for k, v in e.items()}
    assert "a.b.r.D" in a
    b = {k: v + 5 for k, v in a.items()}
    c = H.correlate(a, b)
    assert c["n_common"] == 2 and c["mean_diff_ps"] == 5.0 and c["pearson_r"] == 1.0
    assert H.parse_scalars("OHIER_WNS_MAX -12.5\n")["WNS_MAX"] == -12.5
    bp = H.parse_bpins("u_x/a 12.5 3.0\nu_x/b INF -1e+30\n")
    assert bp == {"u_x/a": (12.5, 3.0), "u_x/b": (None, None)}
    assert H.norm("u_top_RRF/r_q_reg/D", ["u_top_RRF"]) == "r_q_reg.D"
    assert len(H.parse_end("u_a/r/D (DFF) 100.0 50.0 50.0 (MET)\nu_a/s/D (DFF) 100.0 150.0 -50.0 (VIOLATED)\n")) == 2
    assert "find_timing_paths -through $p" in H.tcl_etm(["a.lib"], ["e.lib"], "t.v", "t", "t.spef", ["u_a"], "d.sdc", "/o")


def test_shared_schema_roundtrip():
    """ohier writes a valid opentools.plan/1 doc: 1 region == 1 partition == 1 die-level block."""
    from common import plan as CP
    *_, plan, _, _ = _plan(3)
    d = tempfile.mkdtemp()
    S.save(plan, os.path.join(d, "plan.json"))
    P = CP.load(os.path.join(d, "plan.json"))          # shared validator
    assert P["schema"] == "opentools.plan/1"
    assert len(P["regions"]) == 3 and all(r["partition"] for r in P["regions"])
    blocks = {m["master"]: m for m in P["macros"]}
    for r in P["regions"]:
        m = blocks[r["partition"]]
        assert m["region"] == r["name"] and m["rect"] == r["rect"] and m["kind"] == "hard_core"
        x, y = m["clock_pins"][0]["xy"]
        assert m["rect"][0] - 1e-6 <= x <= m["rect"][2] + 1e-6 and m["rect"][1] - 1e-6 <= y <= m["rect"][3] + 1e-6
    sinks = CP.clock_sinks(P)
    assert len(sinks) == 3 and {s["region"] for s in sinks} == {r["name"] for r in P["regions"]}
    hv = S.load(os.path.join(d, "plan.json"))
    assert [r["module"] for r in hv["regions"]] == [r["module"] for r in plan["regions"]]


def _region_map_doc(rects=True):
    regs = [{"name": "RA", "partition": "top_RA"}, {"name": "RB", "partition": "top_RB"}]
    if rects:
        regs[0]["rect"] = [2.16, 2.16, 40.0, 60.0]
        regs[1]["rect"] = [42.0, 2.16, 80.0, 60.0]
    return {"schema": "opentools.plan/1", "name": "rm", "die": {"w": 82.0, "h": 62.0},
            "regions": regs, "clock": {"name": "clk", "period_ps": 500},
            "other_tool": {"keep": [1, 2, 3]},
            "hier": {"region_members": {"RA": ["u0", "u1", "u2"], "RB": ["u3", "u4"]}}}


def test_region_map_partitions():
    """Region-map mode: map regions are the partitions; unmapped glue follows its connections;
    map rects are binding; foreign fields survive."""
    cells, macros = _lib()
    nl = N.flatten(_design(), "top", cells)
    doc = _region_map_doc()
    base, rmap = S.region_map(doc)
    o = PL.Options(cap_cells=400, period_ps=500, latency_ps=50, util=0.5, die_margin_um=2.0, unit_max_cells=100)
    plan, leaf_part, part_ports = PL.build_plan(nl, cells, macros, o, region_map=rmap, die_wh=(82.0, 62.0))
    assert plan["metrics"]["mode"] == "region_map"
    names = {lf.name: leaf_part[i] for i, lf in enumerate(nl.leaves)}
    assert all(names[n] == 0 for n in names if n.split(".")[0] in ("u0", "u1", "u2"))
    assert all(names[n] == 1 for n in names if n.split(".")[0] in ("u3", "u4"))
    # u5 is unmapped glue: it is driven by u4 -> follows it into RB; the tie cell has no neighbours
    assert all(names[n] == 1 for n in names if n.startswith("u5."))
    assert plan["metrics"]["glue_items"] >= 1
    assert [r["module"] for r in plan["regions"]] == ["top_RA", "top_RB"]
    assert plan["regions"][0]["bbox_um"][0] >= 2.16 and plan["regions"][1]["bbox_um"][2] <= 80.0
    assert plan["metrics"]["crossing_bits"] == 1          # only link2 (u2 -> u3) crosses
    d = tempfile.mkdtemp()
    S.save(plan, os.path.join(d, "plan.json"), base=base)
    from common import plan as CP
    P = CP.load(os.path.join(d, "plan.json"))
    assert P["other_tool"] == {"keep": [1, 2, 3]}
    assert [r["rect"] for r in P["regions"]] == [doc["regions"][0]["rect"], doc["regions"][1]["rect"]]
    # a map region that straddles a subtree is split, never merged across regions
    doc2 = _region_map_doc(rects=False)
    doc2["hier"]["region_members"] = {"RA": ["u0", "u3.ram"], "RB": ["u3", "u4"]}
    _, rmap2 = S.region_map(doc2)
    plan2, lp2, _ = PL.build_plan(nl, cells, macros, o, region_map=rmap2)
    n2 = {lf.name: lp2[i] for i, lf in enumerate(nl.leaves)}
    assert n2["u3.ram"] == 0 and n2["u3.r"] == 1          # longest prefix wins
    assert plan2["metrics"]["floorplan_macro_fit"]


def test_region_map_cap():
    cells, macros = _lib()
    nl = N.flatten(_design(), "top", cells)
    _, rmap = S.region_map(_region_map_doc())
    o = PL.Options(cap_cells=20, unit_max_cells=100)
    try:
        PL.build_plan(nl, cells, macros, o, region_map=rmap, die_wh=(82.0, 62.0))
    except ValueError as e:
        assert "cap" in str(e)
    else:
        raise AssertionError("cell cap not enforced in region-map mode")


ETM = """library (blk) {
  cell ("blk") {
    pin("clk") { direction : input; clock : true;
      timing() { timing_type : min_clock_tree_path; cell_rise(scalar) { values("50.0"); } cell_fall(scalar) { values("51.0"); } }
      timing() { timing_type : max_clock_tree_path; cell_rise(scalar) { values("60.0"); } cell_fall(scalar) { values("61.5"); } }
    }
    pin("d_0_") { direction : input;
      timing() { related_pin : "clk"; timing_type : setup_rising; rise_constraint(scalar) { values("10"); } } }
    pin("d_1_") { direction : input; }
    pin("VSS") { direction : inout; }
    pin("q") { direction : output;
      timing() { related_pin : "clk"; timing_type : rising_edge; cell_rise(scalar) { values("80"); } } }
  }
}
"""
ABS_LEF = """MACRO blk
  CLASS BLOCK ;
  SIZE 10.8 BY 5.4 ;
  PIN clk
  END clk
  PIN d_0_
  END d_0_
  PIN d_1_
  END d_1_
  PIN q
  END q
  PIN VDD
  END VDD
END blk
"""


def test_abstract_check():
    reg = {"module": "blk", "bbox_um": [1.08, 1.08, 11.88, 6.48]}
    c = A.check(reg, ABS_LEF, ETM, ["clk", "d[0]", "d[1]", "q"])
    assert c["ok"], c["problems"]
    assert c["insertion_ps"] == {"min": 50.0, "max": 61.5}
    assert c["unconstrained_inputs"] == ["d_1_"]
    bad = A.check(dict(reg, bbox_um=[0, 0, 12.0, 5.4]), ABS_LEF, ETM, ["clk", "d[0]", "d[1]", "q", "x"])
    assert not bad["ok"] and len(bad["problems"]) == 3     # size, LEF pins, ETM pins


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("PASS", n)
