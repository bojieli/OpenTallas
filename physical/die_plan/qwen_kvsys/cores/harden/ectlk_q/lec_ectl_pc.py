#!/usr/bin/env python3
"""lec_ectl_pc.py -- KV-HG-CDE 11-25: LEC of qkd_ectl3_kiss_st_cols_pc against qkd_ectl3_kiss_st_cols.
Both wrappers sit in one yosys design with the same inputs (the pc per-core ports driven from the old slices of one rsp_data bus); the hard quarters
u_q0..u_q3 are blackboxes (they are macros in every kit), the rest is flattened and wire-reduced.  PASS = every input pin of every quarter sees the
SAME signal in both wrappers and every wrapper output bit comes from the same quarter pin (or the same input) in both.
usage: lec_ectl_pc.py DIR   (DIR has columns.sv wrapper.sv qkd_ectl3_kiss_st_cols_pc.sv; writes lec_top.sv, lec.ys and, with --run, runs yosys in docker)"""
import json, re, subprocess, sys, os
d = sys.argv[1]
w = open(d + "/wrapper.sv").read()
i0 = re.search(r"^module qkd_ectl3_kiss_st_cols #\(", w, re.M).start(); hdr = w[i0:w.index("\n);", i0)]
ports = [(m.group(1), int(m.group(2)), m.group(3)) for m in re.finditer(r"(input|output) wire \[(\d+):0\] (\w+)", hdr)]
top = ["module lec_top ("]
decl, ing, inp = [], [], []
for dr, hi, n in ports:
    if n == "rsp_data":
        decl.append(f"    input wire [1023:0] rsp_data,")
    elif dr == "input":
        decl.append(f"    input wire [{hi}:0] {n},")
    else:
        decl.append(f"    output wire [{hi}:0] g_{n},\n    output wire [{hi}:0] p_{n},")
decl[-1] = decl[-1].rstrip(",")
body = ["\n".join(decl), ");"]
def conn(pref, pc):
    cs = []
    for dr, hi, n in ports:
        if n == "rsp_data":
            if not pc:
                cs.append(".rsp_data(rsp_data)")
        elif dr == "input":
            cs.append(f".{n}({n})")
        else:
            cs.append(f".{n}({pref}_{n})")
    if pc:
        cs += [".rsp_data_q0(rsp_data[511:0])", ".rsp_data_q1(rsp_data[1023:256])", ".rsp_data_q2(rsp_data[767:0])", ".rsp_data_q3(rsp_data[1023:512])"]
    return ",\n        ".join(cs)
body.append("    qkd_ectl3_kiss_st_cols u_g (\n        " + conn("g", False) + ");")
body.append("    qkd_ectl3_kiss_st_cols_pc u_p (\n        " + conn("p", True) + ");")
body.append("endmodule")
open(d + "/lec_top.sv", "w").write("\n".join(top + body) + "\n")
open(d + "/lec.ys", "w").write("""read_verilog -sv /w/columns.sv /w/wrapper.sv /w/qkd_ectl3_kiss_st_cols_pc.sv /w/lec_top.sv
hierarchy -top lec_top
blackbox qkd_ectlk_q0 qkd_ectlk_q1 qkd_ectlk_q2 qkd_ectlk_q3
hierarchy -top lec_top
flatten
opt_clean -purge
write_json /w/lec.json
""")
if "--run" in sys.argv:
    subprocess.check_call(["docker", "run", "--rm", "--cpus=2", "--memory=16g", "-v", d + ":/w", "opentallas/orfs:asap7lock-grtoff", "bash", "-lc",
                           "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l /w/lec.log /w/lec.ys"])
if "--judge" in sys.argv:
    J = json.load(open(d + "/lec.json"))["modules"]["lec_top"]
    cells = J["cells"]
    drv = {}   # bit id -> (quarter, port, idx)
    for cn, c in cells.items():
        m = re.search(r"u_(g|p)\.u_cols\.u_columns\.u_(q[0-3])$", cn)
        assert m, cn
        for pn, bits in c["connections"].items():
            if c["port_directions"][pn] == "output":
                for i, b in enumerate(bits):
                    if isinstance(b, int):
                        drv[b] = (m.group(2), pn, i)
    bad = 0
    by = {}
    for cn, c in cells.items():
        m = re.search(r"u_(g|p)\.u_cols\.u_columns\.u_(q[0-3])$", cn)
        by.setdefault(m.group(2), {})[m.group(1)] = c
    nin = 0
    for q, gp in sorted(by.items()):
        assert set(gp) == {"g", "p"}, q
        for pn, bits in gp["g"]["connections"].items():
            if gp["g"]["port_directions"][pn] == "input":
                nin += len(bits)
                if bits != gp["p"]["connections"][pn]:
                    bad += 1; print("INPUT DIFF", q, pn)
    # outputs: top output bits
    nout = 0
    for pn, pd in J["ports"].items():
        if pd["direction"] == "output" and pn.startswith("g_"):
            gb, pb = pd["bits"], J["ports"]["p_" + pn[2:]]["bits"]
            for i, (x, y) in enumerate(zip(gb, pb)):
                nout += 1
                nx = drv.get(x, ("top", x))
                ny = drv.get(y, ("top", y))
                if (isinstance(x, int) and x in drv and isinstance(y, int) and y in drv and drv[x] == drv[y]) or (nx[0] == "top" and ny[0] == "top" and x == y) or (x == y):
                    continue
                if isinstance(x, str) and x == y:
                    continue
                bad += 1
                if bad < 10: print("OUTPUT DIFF", pn, i, nx, ny)
    print("LEC", "PASS" if bad == 0 else "FAIL", "quarter input bits", nin, "output bits", nout, "diffs", bad)
    sys.exit(1 if bad else 0)
