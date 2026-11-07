#!/usr/bin/env python3
"""HBM-FORM-SPLIT-14-SUX 11-06: derive the full_x lock-step bench from the exp_x bench (= HBM-FORM-SPLIT-13 fullx_bench/mk_bench.py
with the side-pipe depth N = S as an argument; it was fixed at 3 for vA).
    mk_bench_fx.py SHELL_DIR TB_IN OUT_DIR N"""
import sys
SH, TBIN, O, N = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
def sub1(t, a, b):
    assert t.count(a) == 1, (a[:90], t.count(a)); return t.replace(a, b)
SIDE_DECL = "    output wire lane_side_v,\n    output wire [31:0] lane_side_x,\n"
def fs(name_in, name_out):
    t = open(f"{SH}/{name_in}").read()
    t = t.replace("ot_hbm_su_pg_lane_exp_x_core", "ot_hbm_su_pg_lane_full_x_core")
    t = sub1(t, "    output wire lane_coll,\n", "    output wire lane_coll,\n" + SIDE_DECL)
    t = sub1(t, "    wire [0:0] lane_coll__f;\n",
             "    wire [0:0] lane_side_v__f;\n    (* keep *) ot_hbm_face_reg #(.W(1)) u_bout_lane_side_v (.clk(bank_clk), .d(lane_side_v__f), .q(lane_side_v));\n"
             "    wire [31:0] lane_side_x__f;\n    (* keep *) ot_hbm_face_reg #(.W(32)) u_bout_lane_side_x (.clk(bank_clk), .d(lane_side_x__f), .q(lane_side_x));\n"
             "    wire [0:0] lane_coll__f;\n")
    t = sub1(t, ".lane_coll(lane_coll__f),", ".lane_coll(lane_coll__f), .lane_side_v(lane_side_v__f), .lane_side_x(lane_side_x__f),")
    open(f"{O}/{name_out}", "w").write(t)
fs("x_old__fs.sv", "xf_old__fs.sv")
fs("x_new__fs.sv", "xf_new__fs.sv")
t = open(f"{SH}/splitx_vb.sv").read()
t = t.replace("ot_hbm_su_pg_lane_exp_core__splitx_vb", "ot_hbm_su_pg_lane_full_core__splitx_vb")
t = t.replace("ot_hbm_su_pg_lane_exp_x_core_vb__fs", "ot_hbm_su_pg_lane_full_x_core_vb__fs")
if "    output wire lane_coll\n" in t:
    t = sub1(t, "    output wire lane_coll\n", "    output wire lane_coll,\n    output wire lane_side_v,\n    output wire [31:0] lane_side_x\n")
else:
    t = sub1(t, "    output wire lane_coll,\n", "    output wire lane_coll,\n" + SIDE_DECL)
t = sub1(t, "        .lane_coll(lane_coll),\n", "        .lane_coll(lane_coll),\n        .lane_side_v(lane_side_v),\n        .lane_side_x(lane_side_x),\n")
open(f"{O}/splitf_vb.sv", "w").write(t)
t = open(TBIN).read()
t = sub1(t, "ot_hbm_su_pg_lane_exp_core__splitx #", "ot_hbm_su_pg_lane_full_core__splitx #")
t = sub1(t, "ot_hbm_su_pg_lane_exp_core__splitx_vb #", "ot_hbm_su_pg_lane_full_core__splitx_vb #")
t = sub1(t, "  logic [31:0] lane_side_y_r = '0;\n",
         f"  logic [31:0] lane_side_y_r = '0;\n  logic [31:0] side_y_h[0:{N-1}];\n"
         f"  wire [0:0] lane_side_v_ref, lane_side_v_dut;\n  logic [0:0] lane_side_v_h[0:{N-1}];\n"
         f"  wire [31:0] lane_side_x_ref, lane_side_x_dut;\n  logic [31:0] lane_side_x_h[0:{N-1}];\n  longint sv = 0;\n")
a = t.index("u_dut (")
head, tail = t[:a], t[a:]
# side pipe pair: the dut issues side_v/side_x 3 edges later, so the same return arrives 3 edges later
tail = sub1(tail, ".lane_side_y(lane_side_y_r)", ".lane_side_y(side_y_h[`OT_SIDE_D])")
t = head + tail
t = sub1(t, ".lane_coll(lane_coll_ref));", ".lane_coll(lane_coll_ref), .lane_side_v(lane_side_v_ref), .lane_side_x(lane_side_x_ref));")
t = sub1(t, ".lane_coll(lane_coll_dut));", ".lane_coll(lane_coll_dut), .lane_side_v(lane_side_v_dut), .lane_side_x(lane_side_x_dut));")
t = sub1(t, "    lane_side_y_r <= $urandom;\n",
         "    lane_side_y_r <= $urandom;\n    side_y_h[0] <= lane_side_y_r; " + f"for (int i = 1; i < {N}; i++) side_y_h[i] <= side_y_h[i-1];\n"
         f"    lane_side_v_h[0] <= lane_side_v_ref; for (int i = 1; i < {N}; i++) lane_side_v_h[i] <= lane_side_v_h[i-1];\n"
         f"    lane_side_x_h[0] <= lane_side_x_ref; for (int i = 1; i < {N}; i++) lane_side_x_h[i] <= lane_side_x_h[i-1];\n")
t = sub1(t, "      if (|lane_vm_we_ref) wr++;",
         f"      checks++; if (lane_side_v_dut !== lane_side_v_h[{N-1}]) bad(\"lane_side_v\");\n"
         f"      checks++; if (lane_side_v_h[{N-1}] && lane_side_x_dut !== lane_side_x_h[{N-1}]) bad(\"lane_side_x\");\n"
         "      if (|lane_side_v_ref) sv++;\n      if (|lane_vm_we_ref) wr++;")
t = sub1(t, "(errs == 0 && wr > 0 && sp > 0 && fp > 0) ? \"PASS\" : \"FAIL\"", "(errs == 0 && wr > 0 && sp > 0 && fp > 0 && sv > 0) ? \"PASS\" : \"FAIL\"")
t = sub1(t, "sfu_fault_dut=%0d\"", "sfu_fault_dut=%0d side_v=%0d\"")
t = sub1(t, ", sp, sd);", ", sp, sd, sv);")
t = sub1(t, "int kinds[0:7] = '{0,1,4,5,0,5,1,4};", "int kinds[0:7] = '{0,1,2,4,3,5,6,7};")
open(f"{O}/tbf.sv", "w").write(t)
print("ok")
