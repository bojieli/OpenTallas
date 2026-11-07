"""DQ85-SUL0: equivalence slice proof gold bound vs replica bound (lane c_i vectors, cycle-exact).
usage: sul0_eqproof.py GOLD_BOUND GATE_BOUND OUT_DIR -> writes slice.v + eq.ys; run yosys eq.ys (bind_cells.sv on path)."""
import re, sys, os
g, h, o = sys.argv[1:4]
def slice_mod(path, name):
    t = open(path).read().split("\n")
    regs = [l for l in t if re.match(r"\s*ot_dp_st #\(\.W\(\d+\)\) u_bin_x_su_c_(p1_)?i\w* ", l)]
    wires = [l for l in t if re.match(r"\s*wire (\[\d+:0\] )?x_su_c_(p1_)?i_(q|eq)\w*;", l)]
    asg = [l for l in t if re.match(r"\s*assign x_su_c_(p1_)?i_eq = ", l)]
    body = []
    for k in range(4):
        line = [l for l in t if re.match(r"\s*qfd_qc_su_lane_w_l%d u_lane%d " % (k, k), l)][0]
        ci = re.search(r"\.c_i\((\{.*?\})\), \.c_o", line).group(1)
        body.append(f"  assign lane{k}_ci = {ci};")
    hdr = (f"module {name}(input clk, input rst_n, input [766:0] cland_x_su_c_i, input [765:0] cland_x_su_c_p1_i,\n"
           "  output [759:0] lane0_ci, output [759:0] lane1_ci, output [759:0] lane2_ci, output [759:0] lane3_ci,\n"
           "  output eq_a, output eq_b);\n")
    return hdr + "\n".join(wires + regs + asg + body) + "\n  assign eq_a = x_su_c_i_eq;\n  assign eq_b = x_su_c_p1_i_eq;\nendmodule\n"
os.makedirs(o, exist_ok=True)
open(os.path.join(o, "slice.v"), "w").write(slice_mod(g, "gold") + slice_mod(h, "gate"))
open(os.path.join(o, "eq.ys"), "w").write(
    "read_verilog -sv bind_cells.sv slice.v\nhierarchy -check\nsetattr -mod -unset keep_hierarchy *\nproc; flatten; async2sync; opt_clean\n"
    "miter -equiv -flatten -make_outputs gold gate miter\nhierarchy -top miter\n"
    "sat -verify -tempinduct -prove trigger 0 -seq 1 -maxsteps 6 -show-ports miter\n")
