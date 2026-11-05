#!/usr/bin/env python3
"""DIE-QC-74 11-05: NKP bit3 (8), on top of nkp_patch.py: the g_terms7p shifter rows REGISTERED one edge before the
carry-save tree.  Cut for the p7t / v3 worst class spc copy -> (b - spc) -> barrel row -> CSA -> ts_sq / ts_cq: 4_cts TT
placement RC -283.77 ps NK, -472.45 ps NL, data 909 / 1203 ps.  Rows edge 1, ts_sq edge 2, tsh[0] edge 3, tsg_a edge 4,
tstep_r / ot_step edge 5 < first round boundary (edge >= IL = 8): 0 visible cycles, values unchanged.  Async reset as
ts_sq (no free start state on structurally-0 row bits: LEC).  NKP without bit3 elaborates as before.
usage: nkp15_patch.py RTLDIR  (patches ot_qwen_w12_matvec_land32.sv in place; exact anchors, fail-closed)"""
import sys
from pathlib import Path

def rep(t, a, b):
    assert t.count(a) == 1, (a[:90], t.count(a)); return t.replace(a, b)

p = Path(sys.argv[1]) / "ot_qwen_w12_matvec_land32.sv"
t = p.read_text()
t = rep(t, ".rows(trf), .s(ts_s), .c(ts_c));", ".rows(trc), .s(ts_s), .c(ts_c));")
t = rep(t, ".rows(orf), .s(os_s), .c(os_c));", ".rows(orc), .s(os_s), .c(os_c));")
t = rep(t, "            wire [AW+PRW-1:0] ts_s, ts_c, os_s, os_c, ts_a, os_a;\n",
        "            //: NKP bit3 (DIE-QC-74 11-05): rows registered before the CSA tree: rows edge 1 ... tstep_r / ot_step edge 5 < IL\n"
        "            wire [NB_GT*(AW+PRW)-1:0] trc, orc;\n"
        "            if ((NKP & 8) != 0) begin : g_rq\n"
        "                reg [NB_GT*(AW+PRW)-1:0] trf_q, orf_q;\n"
        "                always @(posedge clk or negedge rst_n)\n"
        "                    if (!rst_n) begin trf_q <= {(NB_GT*(AW+PRW)){1'b0}}; orf_q <= {(NB_GT*(AW+PRW)){1'b0}}; end\n"
        "                    else begin trf_q <= trf; orf_q <= orf; end\n"
        "                assign trc = trf_q;\n"
        "                assign orc = orf_q;\n"
        "            end else begin : g_rc\n"
        "                assign trc = trf;\n"
        "                assign orc = orf;\n"
        "            end\n"
        "            wire [AW+PRW-1:0] ts_s, ts_c, os_s, os_c, ts_a, os_a;\n")
t = rep(t, "KV_PREP < 3 || IL < 6 || NKP > 7 ||", "KV_PREP < 3 || IL < 6 || NKP > 15 ||")
p.write_text(t)
print("NKP15_PATCH OK", p)
