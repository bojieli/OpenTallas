#!/usr/bin/env python3
"""Recover the three IQF ring reset parents without re-running the whole die binder.

Only the three named child reset inputs change. The current plan's generated
reset-grid index and collector declaration must agree; the actual source relay
graph must prove equal depth on one clock. A small actual-relay lockstep plus a
wrong-depth mutant runs before the corrected source is written. This is a
recovery coupon, not whole-die bind authority or physical timing qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "tools" / "die_plan"))
import reset_tree as RT
import schema as S

BUSES = ("ft1_i", "idx_i0", "ql_i0")


def prepare(plan, source):
    tn = "iqf__t1"
    t = plan["partition_types"][tn]
    rows = t["clock"]["landing_contract"]["collector_local_sources"]
    assert {r["name"] for r in rows} == set(BUSES), "unexpected IQF ring set"
    taps = RT._taps(S.Plan(plan), tn)
    # The relay statements are copied verbatim into the proof below.
    relays = []
    for m in re.finditer(r"\bot_dp_rrelay\s+(u_rst_in|u_rrl_\d+)\s*\(([^;]+)\);", source):
        ports = dict(re.findall(r"\.(\w+)\s*\(\s*(\w+)\s*\)", m[2]))
        assert set(ports) == {"clk", "d", "q"} and ports["clk"] == "clk"
        relays.append(dict(name=m[1], **ports, statement=m[0]))
    assert relays and len({r["q"] for r in relays}) == len(relays)
    depth = {"arst_n": 0}
    while True:
        more = {r["q"]: depth[r["d"]] + 1 for r in relays if r["d"] in depth}
        before = len(depth)
        depth.update(more)
        if len(depth) == before:
            break
    assert len(depth) == len(relays) + 1, "non-tree or missing reset source"
    changes = []
    for bus in BUSES:
        row = next(r for r in rows if r["name"] == bus)
        x, y = row["xy_um"]
        tap = min(range(len(taps)), key=lambda i: abs(taps[i][1] - x) + abs(taps[i][2] - y))
        assert tap == row["tap"], "plan grid differs from collector contract"
        target = f"rst_n_t{tap}"
        pat = (r"\bot_dp_clk_landing\s*#\(\.W\((\d+)\)\)\s+u_cland_"
               + re.escape(bus) + r"\s*\((.*?)\);")
        matches = list(re.finditer(pat, source, re.S))
        assert len(matches) == 1, f"expected exactly one source instance for {bus}"
        m = matches[0]
        rst = list(re.finditer(r"\.rst_n\(\s*(\w+)\s*\)", m[2]))
        assert len(rst) == 1 and rst[0][1] == "rst_n_t0", "unexpected original reset parent"
        slot = next((s for s in t.get("ft_slots", []) if s["name"] + "_i" == bus), None)
        b = next((b for b in t.get("buses", []) if b["name"] == bus), None)
        width = (slot if slot is not None else b)["width"] + 1
        assert int(m[1]) == width, "source width differs from plan plus epoch"
        assert depth[target] == depth["rst_n_t0"], "reset release depth changes"
        start = m.start(2) + rst[0].start(1)
        end = m.start(2) + rst[0].end(1)
        changes.append(dict(bus=bus, old="rst_n_t0", new=target, source_depth=depth[target],
                            start=start, end=end, plan_tap=tap, width=width))
    corrected = source
    for c in sorted(changes, key=lambda c: c["start"], reverse=True):
        corrected = corrected[:c["start"]] + c["new"] + corrected[c["end"]:]
    # Reversing the three exact substitutions must recover every original byte.
    reverse = corrected
    for bus in BUSES:
        c = next(c for c in changes if c["bus"] == bus)
        pat = r"(\bu_cland_" + re.escape(bus) + r"\s*\(.*?\.rst_n\()" + c["new"] + r"(\))"
        reverse, n = re.subn(pat, lambda m: m[1] + c["old"] + m[2], reverse, count=1, flags=re.S)
        assert n == 1
    assert reverse == source, "non-reset source bytes changed"
    return corrected, changes, relays, depth


def prove(relays, depth, changes, cells, outdir):
    definitions = list(re.finditer(r"\bmodule\s+ot_dp_rrelay\b.*?\bendmodule\b", cells, re.S))
    assert len(definitions) == 1, "need exact source relay module"
    # Check the semantic mechanism used in the equal-depth argument.
    assert re.search(r"always\s*@\(posedge clk\)\s*q\s*<=\s*d\s*;", definitions[0][0])
    mutant = next(k for k in sorted(depth) if depth[k] == depth["rst_n_t0"] - 1)
    outdir.mkdir(parents=True, exist_ok=True)
    wires = ", ".join(r["q"] for r in relays)
    checks = "\n".join(f"if (rst_n_t0 !== {c['new']}) errors=errors+1;" for c in changes)
    tb = definitions[0][0] + f"""
`timescale 1ps/1ps
module tb;
reg clk=0, arst_n=0; integer i, errors=0, mutants=0, checks=0;
always begin #416 clk=1; #417 clk=0; end
wire {wires};
{chr(10).join(r['statement'] for r in relays)}
initial begin
 for(i=0;i<128;i=i+1) begin
  @(negedge clk); arst_n = (i>=10 && i<40) || (i>=55 && i<90) || i>=105;
  @(posedge clk); #1;
  if(i>=8) begin
   {checks}
   checks=checks+{len(changes)};
   if(rst_n_t0 !== {mutant}) mutants=mutants+1;
  end
 end
 $display("LOCKSTEP checks=%0d errors=%0d wrong_depth_mutant=%0d",checks,errors,mutants);
 if(errors || !mutants) $fatal(1,"reset equivalence or mutant control failed");
 $finish;
end
endmodule
"""
    src = outdir / "reset_miter.sv"
    src.write_text(tb)
    subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", str(outdir / "miter"), str(src)], check=True)
    r = subprocess.run(["vvp", str(outdir / "miter")], check=True, text=True, capture_output=True)
    (outdir / "miter.log").write_text(r.stdout + r.stderr)
    return dict(log=r.stdout.strip(), wrong_depth_parent=mutant,
                scope="actual relay network input equivalence; identical child source by substitution")


def main():
    p = argparse.ArgumentParser()
    for key in ("plan", "source", "cells", "out", "report", "coupon"):
        p.add_argument("--" + key, required=True, type=Path)
    a = p.parse_args()
    source = a.source.read_text()
    corrected, changes, relays, depth = prepare(json.loads(a.plan.read_text()), source)
    proof = prove(relays, depth, changes, a.cells.read_text(), a.coupon)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    assert a.out.resolve() != a.source.resolve(), "preserve original source"
    a.out.write_text(corrected)
    report = dict(source=str(a.source), source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  out_sha256=hashlib.sha256(corrected.encode()).hexdigest(), substitutions=changes,
                  unchanged_other_bytes=True, added_data_cycles=0, added_reset_cycles=0, proof=proof,
                  remaining="full bind authority, fresh PLACE and all physical gates remain open")
    a.report.write_text(json.dumps(report, indent=2) + "\n")
    print(proof["log"])


if __name__ == "__main__":
    main()
