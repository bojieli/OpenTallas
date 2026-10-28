"""DIE-KV-7 R8 strap-pad bank LEC (OWNER 2026-10-28): for every used (W, DMAX, count) constant of the strap-pad sites
(r8.py check --strap-pads -> stats.strap_used_constants), gate = ot_dp_dly_cnt #(W, DMAX) with strap_cnt tied to count,
gold = ot_dp_dly #(W, D=count) (the binder's fixed pad; count 0 = wire).  Plus one MUTANT per (W, DMAX): the tie flipped
to a different legal count, which must be DECIDED not-equivalent (unproven $equiv cells); a TIMEOUT / tool error is
UNDECIDED and never counts as caught.
usage: run_lec.py CHECK_JSON BANK_SV DLY_SV OUT_DIR [--jobs N] [--timeout S]"""
import argparse
import concurrent.futures
import json
import re
import subprocess
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("check")
ap.add_argument("bank")
ap.add_argument("dly")
ap.add_argument("out")
ap.add_argument("--jobs", type=int, default=6)
ap.add_argument("--timeout", type=int, default=1800)
a = ap.parse_args()
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=True)
consts = [tuple(x) for x in json.load(open(a.check))["stats"]["strap_used_constants"]]
(out / "bank.sv").write_text(Path(a.bank).read_text())
(out / "dly.sv").write_text(Path(a.dly).read_text())
(out / "harness.sv").write_text("""module gold #(parameter integer W = 1, parameter integer C = 0) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    generate if (C == 0) begin : g0 assign q = d; end
    else begin : gd ot_dp_dly #(.W(W), .D(C)) u_dly (.clk(clk), .d(d), .q(q)); end endgenerate
endmodule
module gate #(parameter integer W = 1, parameter integer DMAX = 1, parameter integer C = 0) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    ot_dp_dly_cnt #(.W(W), .DMAX(DMAX)) u_bank (.clk(clk), .strap_cnt(C[3:0]), .d(d), .q(q));
endmodule
""")


def run(job):
    w, dmax, c, kind, tie = job
    tag = f"w{w}_d{dmax}_c{c}_{kind}"
    seq = dmax + 1
    script = (f"read_verilog -sv /work/dly.sv /work/bank.sv /work/harness.sv; "
              f"chparam -set W {w} -set C {c} gold; chparam -set W {w} -set DMAX {dmax} -set C {tie} gate; "
              f"hierarchy -check; proc; memory_map; setattr -mod -unset keep_hierarchy; flatten gold gate; "
              f"opt_clean; equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple -seq {seq}; "
              f"equiv_induct -seq {seq + 1}; equiv_status -assert")
    cmd = ["docker", "run", "--rm", "--memory=4g", "--cpus=1", "-v", f"{out}:/work", "-w", "/work",
           "openroad/orfs:asap7lock", "bash", "-lc",
           'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec yosys -Q -T -p "$1"', "bash", script]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
        log, rc = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        log, rc = "TIMEOUT", 124
    (out / f"{tag}.log").write_text(log)
    proven = rc == 0 and "Equivalence successfully proven" in log
    m = re.findall(r"ERROR: Found (\d+) unproven \$equiv cells", log)
    decided_diff = rc not in (0, 124) and bool(m) and int(m[-1]) > 0
    ok = proven if kind == "eq" else decided_diff
    res = dict(tag=tag, width=w, dmax=dmax, count=c, tie=tie, kind=kind, rc=rc, proven=proven,
               unproven=int(m[-1]) if m else None, timeout=rc == 124, pass_=ok,
               undecided=(not proven and not decided_diff), tail=log.splitlines()[-3:])
    print(json.dumps({k: v for k, v in res.items() if k != "tail"}), flush=True)
    return res


jobs = [(w, d, c, "eq", c) for w, d, c in consts]
for w, d in sorted({(w, d) for w, d, _ in consts}):
    c = min(c for ww, dd, c in consts if (ww, dd) == (w, d))
    jobs.append((w, d, c, "mutant", c + 1 if c + 1 <= d else c - 1))
with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
    rows = list(ex.map(run, jobs))
eq = [r for r in rows if r["kind"] == "eq"]
mu = [r for r in rows if r["kind"] == "mutant"]
rep = dict(schema="opentallas.r8_strap_lec.v1", check=str(Path(a.check).resolve()), used_constants=len(consts),
           equivalent=sum(r["pass_"] for r in eq), mutants=len(mu), mutants_caught=sum(r["pass_"] for r in mu),
           undecided=sum(r["undecided"] for r in rows),
           verdict="PASS" if all(r["pass_"] for r in rows) else "FAIL", rows=rows)
(out / "receipt.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps({k: v for k, v in rep.items() if k != "rows"}))
raise SystemExit(0 if rep["verdict"] == "PASS" else 1)
