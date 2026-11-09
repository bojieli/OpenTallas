#!/usr/bin/env python3
"""HBM-PLAN-1: formal proof (yosys sat, free initial state) that an ot_dp_st chain of k stations equals the
qn_alternate form (stn x (k - k%2) + plain st when odd) on q and eq at every cycle >= k+1, for each k; plus mutants
(all-stn on an odd chain, one plain st dropped from an even chain's pairing) that must FAIL.
usage: qn_chain_proof.py BIND_CELLS.sv STN_SRC.sv OUTDIR KMAX"""
import subprocess, sys, os, json, re
cells, stnsrc, out, kmax = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
os.makedirs(out, exist_ok=True)
stn = re.search(r"module ot_dp_stn.*?endmodule", open(stnsrc).read(), re.S).group(0)
W = 1
def chain(name, mods):
    k = len(mods)
    s = [f"module {name}(input clk, input rst_n, input [{W-1}:0] d, input ea, output [{W-1}:0] q, output eq);"]
    s.append(f"  wire [{W-1}:0] x0 = d; wire e0 = ea;")
    for i, m in enumerate(mods):
        s.append(f"  wire [{W-1}:0] x{i+1}; wire e{i+1};")
        s.append(f"  {m} u{i} (.clk(clk), .rst_n(rst_n), .d(x{i}), .ea(e{i}), {'.qn' if m == 'ot_dp_stn' else '.q'}(x{i+1}), .eq(e{i+1}));")
    s.append(f"  assign q = x{k}; assign eq = e{k};\nendmodule")
    return "\n".join(s)
def form(k):
    return ["ot_dp_stn"] * (k - k % 2) + ["ot_dp_st"] * (k % 2)
res = {}
for k in range(1, kmax + 1):
    cases = {"rule": form(k)}
    if k % 2: cases["mut_all_stn"] = ["ot_dp_stn"] * k
    else: cases["mut_one_stn"] = ["ot_dp_stn"] + ["ot_dp_st"] * (k - 1)
    for tag, mods in cases.items():
        v = os.path.join(out, f"k{k}_{tag}.v")
        open(v, "w").write("\n".join([chain("gold", ["ot_dp_st"] * k), chain("gate", mods), stn]))
        ys = (f"read_verilog -sv {cells} {v}; hierarchy -check; setattr -mod -unset keep_hierarchy; proc; flatten; async2sync; miter -equiv -flatten -make_outputs gold gate m; "
              f"hierarchy -top m; sat -seq {k + 12} -prove-skip {k} -prove trigger 0 -show-ports -verify m")
        p = subprocess.run(["yosys", "-q", "-p", ys], capture_output=True, text=True)
        txt = p.stdout + p.stderr
        open(v[:-2] + ".log", "w").write(txt)
        if p.returncode == 0: r = "PASS"
        elif "counter-example" in txt.lower() or "proof did fail" in txt.lower(): r = "FAIL"
        else: r = "ERROR"
        res[f"k{k}_{tag}"] = r
print(json.dumps(res))
good = all(v == "PASS" for k, v in res.items() if k.endswith("_rule")) and all(v == "FAIL" for k, v in res.items() if "_mut_" in k)
json.dump(dict(results=res, verdict="PASS" if good else "FAIL"), open(os.path.join(out, "chain_proof.json"), "w"), indent=1)
print("VERDICT", "PASS" if good else "FAIL")
