#!/usr/bin/env python3
"""rst_reach_lockstep.py -- reset-cone lockstep + mutant check for rst_reach_construct (C-RST-RELAY-REACH).

For every START raw the construct pass re-pointed (report types[*].raw_repick / edge_repoints / local_taps) the NEW raw net is built
from the ACTUAL emitted reset relay cone (reset_tree.rtl_lines of the OUTPUT plan) and compared cycle by cycle with the reference
consumer tap (rst_n_t0 of the same type, same edge: all consumer taps release on one wavefront) under a pseudo-random reset.
Control: each cone's one-edge-early mutant (the driver of the net) must be CAUGHT, or the check fails (a vacuous lockstep).
  rst_reach_lockstep.py PLAN_OUT REPORT TREE OUT_DIR [--tag TAG] [--orig ORIGINAL_PLAN] [--max-per-type K]   -> OUT_DIR/<tag>.sv, runs iverilog/vvp, exit 0 = PASS
"""
import json, os, re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_rtl, reset_tree, schema  # noqa: E402

def main():
    plan_p, rep_p, tree, out = sys.argv[1:5]
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "rstreach"
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    os.chdir(tree)
    os.environ.update(OT_REPO_ROOT=tree, OT_PLAN_ROOT=str(Path(sys.argv[sys.argv.index("--orig") + 1] if "--orig" in sys.argv else plan_p).parent), OT_RESET_POOL_J="4")
    kmax = int(sys.argv[sys.argv.index("--max-per-type") + 1]) if "--max-per-type" in sys.argv else 0   # RSTSPREAD terminals checked per type (0 = all)
    rep = json.load(open(rep_p))
    orig = sys.argv[sys.argv.index("--orig") + 1] if "--orig" in sys.argv else plan_p   # die_plan.json sits next to the ORIGINAL plan
    plan = schema.Plan(json.load(open(plan_p)), orig)
    cases = {}
    for tn, v in rep["types"].items():
        for where, was, now in v.get("raw_changes", []):
            if re.fullmatch(r"rst_n_t\d+", str(now)):
                cases.setdefault(tn, set()).add(now)
        nt = v.get("new_taps") or ([f"rst_n_t{i}" for i in range(v["before"]["n_taps"], v["after"]["n_taps"])] if "before" in v and "after" in v else [])
        for now in nt:      # RSTSPREAD terminals: every new local tap must release with rst_n_t0
            cases.setdefault(tn, set()).add(now)
    if not cases:
        print("LOCKSTEP no re-pointed rst_n_t raws; nothing to compare"); return 0
    reset_tree.prewarm(plan, sorted(cases), jobs=4)
    modules, n, bad = [], 0, []
    for tn in sorted(cases):
        T = reset_tree.for_type(plan, tn)
        drivers = {}
        for line in reset_tree.rtl_lines(T):
            h = re.search(r"\b(ot_dp_rrelay(?:_nl|_drive)?)\s+\w+\s*\(\s*\.clk\(clk\),\s*\.d\((\w+)\),\s*\.q\((\w+)\)\);", line)
            if h:
                drivers[h.group(3)] = (h.group(1), h.group(2))
            g = re.search(r"\b(ot_dp_rgate)\s+\w+\s*\(\s*\.clk\(clk\),\s*\.d\((\w+)\),\s*\.run\((\w+)\),\s*\.q\((\w+)\)\);", line)
            if g:      # mission-role gated tap (reset AND run): the run chain is built too, run_root is a second stimulus
                drivers[g.group(4)] = (g.group(1), g.group(2), g.group(3))
        ref = "rst_n_t0"
        for b in sorted(cases[tn]):
            if b not in drivers or ref not in drivers:
                bad.append(f"{tn}: {b if b not in drivers else ref} is not an emitted relay output"); continue
            mutant = drivers[b][1]
            wires = {}
            def emit(q):
                if q in ("rst_root_n", "run_root") or q in wires or q not in drivers: return
                dr = drivers[q]; cell, d = dr[0], dr[1]; emit(d)
                if len(dr) == 3:
                    emit(dr[2]); wires[q] = f"{cell} u_{q} (.clk(clk), .d({d}), .run({dr[2]}), .q({q}));"
                else:
                    wires[q] = f"{cell} u_{q} (.clk(clk), .d({d}), .q({q}));"
            for q in (ref, b, mutant): emit(q)
            modules.append(f"module cone_{n}(input clk, input rst_root_n, input run_root, output a, b, mut);\n"
                + "\n".join(f"wire {q}; {i}" for q, i in wires.items())
                + f"\nassign a = {ref}; assign b = {b}; assign mut = {mutant}; endmodule\n")
            n += 1
    if bad:
        print("LOCKSTEP FAIL", *bad[:10], sep="\n  "); return 1
    insts = "\n".join(f"cone_{i} lane_{i}(clk, d, rr, a[{i}], b[{i}], mut[{i}]);" for i in range(n))
    tb = f"""module tb; reg clk=0, d=0, rr=0; reg [{n-1}:0] seen=0; wire [{n-1}:0] a, b, mut; {insts}
task check; begin if ((^a) === 1'bx || (^b) === 1'bx || a !== b) $fatal(1, "lockstep mismatch a=%h b=%h", a, b); seen = seen | (a ^ mut); end endtask
integer i; initial begin for(i=0;i<160;i=i+1) begin d = (i%13 >= 4) ^ (i%19 == 0); rr = (i%7 >= 2); #4 clk=1; #1 if(i>40) check; #4 clk=0; #1 if(i>40) check; end
 if (seen !== {{{n}{{1'b1}}}}) $fatal(1,"control did not catch all one-edge-early mutants: %h", seen);
 $display("RST_REACH_LOCKSTEP_PASS cones={n} controls={n}"); $finish; end endmodule
"""
    sv = out / f"{tag}.lockstep.sv"
    sv.write_text(gen_rtl.CELLS + gen_rtl.LOCKUP_CELLS + "\n".join(modules) + tb)
    r = subprocess.run(["iverilog", "-g2012", "-s", "tb", str(sv), "-o", str(out / f"{tag}.vvp")], capture_output=True, text=True)
    if r.returncode: print(r.stderr[:800]); return 1
    r = subprocess.run(["vvp", str(out / f"{tag}.vvp")], capture_output=True, text=True)
    print(r.stdout[-400:], r.stderr[-300:]); return 0 if "LOCKSTEP_PASS" in r.stdout else 1

sys.exit(main())
