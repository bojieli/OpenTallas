#!/usr/bin/env python3
"""Entry-phase bench for changed hd_serdes partitions (P-RESET-RECEIPT, HEAD-PROBE-R3 11-27).

Reads reset_entry_phase and id_straps.strap_rst_ph of every hd_serdes partition that differs between OLD and NEW plan FROM THE PLANS, generates an iverilog
bench that instantiates the real ot_dp_rrelay_ph (pin_entry_phase.CELL_RTL) once per (partition, old|new) with ph = the plan's strap value, simulates the
release ordering (ph=1 releases one cycle before ph=0) and checks the plan's own consistency (strap = h mod 2, release_delta = -ceil(h/2)).
It proves cell polarity and the plan-field arithmetic.  The whole-cycle part of reset_entry_phase is a label: PENDING die STA on the plan.

  python3 -I entry_phase_bench.py OLD_PLAN NEW_PLAN OUTDIR TOOLS_DIE_PLAN   -> OUTDIR/{ot_dp_rrelay_ph.sv,tb.sv,bench.log,entry_phase_evidence.json}
"""
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

FIELDS = (("reset_entry_phase", lambda p: p.get("reset_entry_phase")),
          ("id_straps.strap_rst_ph", lambda p: (p.get("id_straps") or {}).get("strap_rst_ph")))
T = 1000


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(old_plan, new_plan, out, tools):
    sys.path.insert(0, str(tools))
    import pin_entry_phase as PE
    import head_native_release as H
    old, new = json.loads(Path(old_plan).read_text()), json.loads(Path(new_plan).read_text())
    op = {p["name"]: p for p in old["partitions"] if p["type"] == "hd_serdes"}
    np_ = {p["name"]: p for p in new["partitions"] if p["type"] == "hd_serdes"}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cell = PE.CELL_RTL
    (out / "ot_dp_rrelay_ph.sv").write_text(cell)
    rows, cases = [], []
    for name in sorted(np_):
        mine = []
        for fld, get in FIELDS:
            a, b = get(op.get(name, {})), get(np_[name])
            if a != b:
                mine.append(dict(partition=name, field=fld, old=a, new=b))
        rows += mine
        if mine:
            for ver, part in (("old", op.get(name)), ("new", np_[name])):
                if part is None:
                    continue
                h = int(part.get("reset_entry_phase", 0))
                st = int((part.get("id_straps") or {}).get("strap_rst_ph", 0))
                assert st == h % 2, (name, ver, "plan strap != reset_entry_phase mod 2", st, h)
                assert PE.release_delta(h) == -math.ceil(h / 2)
                cases.append(dict(partition=name, version=ver, h=h, strap=st, release_delta=PE.release_delta(h), expect_cycles=1 if st else 2))
    lines = ["`timescale 1ps/1ps", "module tb;", "  localparam T = %d;" % T, "  reg clk = 0; always #(T/2) clk = ~clk;",
             "  reg d = 0;", "  integer t0;"]
    for i, c in enumerate(cases):
        lines.append("  wire q%d; ot_dp_rrelay_ph u%d (.clk(clk), .ph(1'b%d), .d(d), .q(q%d)); integer r%d = -1; "
                     "always @(posedge q%d) if (r%d < 0) r%d = $time;" % (i, i, c["strap"], i, i, i, i, i))
    lines.append("  initial begin @(posedge clk); #1 t0 = $time; d = 1; #(5*T);")
    for i, c in enumerate(cases):
        lines.append('    $display("CASE %s %s ph=%d cycles=%%0d", (r%d - t0 + T/2)/T);' % (c["partition"], c["version"], c["strap"], i))
    lines += ['    $display("BENCH_DONE"); $finish; end', "endmodule"]
    (out / "tb.sv").write_text("\n".join(lines) + "\n")
    r = subprocess.run(["iverilog", "-g2012", "-o", str(out / "tb.vvp"), str(out / "ot_dp_rrelay_ph.sv"), str(out / "tb.sv")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    v = subprocess.run(["vvp", str(out / "tb.vvp")], capture_output=True, text=True)
    log = v.stdout
    got = {(m[0], m[1]): int(m[2]) for m in re.findall(r"CASE (\S+) (\S+) ph=\d+ cycles=(-?\d+)", log)}
    ok = v.returncode == 0 and "BENCH_DONE" in log and bool(cases) and all(got.get((c["partition"], c["version"])) == c["expect_cycles"] for c in cases)
    for c in cases:
        c["sim_cycles"] = got.get((c["partition"], c["version"]))
    log += "\n" + ("ENTRY_PHASE_BENCH PASS" if ok else "ENTRY_PHASE_BENCH FAIL") + "\n"
    (out / "bench.log").write_text(log)
    ev = dict(schema="opentallas.entry_phase_evidence.v1", plan_digest=H.digest(new), old_plan_digest=H.digest(old),
              cell_sha256=sha(cell.encode()), rows=rows, cases=cases, verdict="PASS" if ok else "FAIL", log="bench.log",
              pass_marker="ENTRY_PHASE_BENCH PASS",
              artifacts={n: sha((out / n).read_bytes()) for n in ("ot_dp_rrelay_ph.sv", "tb.sv", "bench.log")},
              not_proven="whole-cycle part of reset_entry_phase (a label), seam setup/hold at the new capture edge, START entry, strap tie in "
                         "the generated die top: PENDING die STA / bind check on the plan digest")
    (out / "entry_phase_evidence.json").write_text(json.dumps(ev, indent=1) + "\n")
    print("ENTRY_PHASE_EVIDENCE", ev["verdict"], len(rows), "rows", out / "entry_phase_evidence.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
