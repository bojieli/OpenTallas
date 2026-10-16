#!/usr/bin/env python3
"""Derive the command-calendar ASTK masters (qkd_astk_ep_cal, qkd_astk_ctl_cal, qkd_astk_ctl_tp8_cal) from the sealed
qkd_astk_ep / qkd_astk_ctl / qkd_astk_ctl_tp8 source by exact textual edits, so arithmetic/datapath stay byte-identical.

Only change: the static start ages (EXP / LMAX / Z) become command-carried calendar inputs captured on the local start
edge (compiler-scheduled per context length), plus a fault when the carried calendar violates the leaf's own sealed
constraints. The sealed masters are untouched. --check fails if the committed output differs from a fresh derivation.
"""
import argparse, hashlib, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv'
STACK_S = 'rtl/qwen_sys/split_20261014/qkd_astk_native_stack_s.sv'
NSTACK = 'rtl/hdc/nearhbm/ot_qwen_tp8_attention_native_stack.sv'
OUT = ROOT / 'rtl/qwen_sys/split_20261014/qkd_astk_cal_gen.sv'

def module(text, name):
    m = re.search(r'^module %s #\(.*?^endmodule\n' % re.escape(name), text, re.S | re.M)
    assert m, name
    return m.group(0)

def edit(s, a, b):
    assert s.count(a) == 1, (a[:80], s.count(a))
    return s.replace(a, b)

def derive():
    src = SRC.read_text()
    ep = module(src, 'qkd_astk_ep')
    ep = edit(ep, 'module qkd_astk_ep #(', 'module qkd_astk_ep_cal #(')
    ep = edit(ep, "    parameter integer HEADS=`KVD_HEADS\n) (\n    input  wire          ck,",
              "    parameter integer HEADS=`KVD_HEADS\n) (\n    input  wire [15:0]   cal_exp,   // this EP's EXP start age (compiler calendar)\n    input  wire          ck,")
    ep = edit(ep, "    wire static_trigger = schedule_active && schedule_age == EXP_START_AGE-1;",
              "    reg  [15:0] cal_exp_q, exp_age;\n    always @(posedge ck) cal_exp_q <= cal_exp;\n"
              "    always @(posedge ck) if (start) exp_age <= cal_exp_q;\n"
              "    wire cal_bad = STATIC_SCHEDULE && schedule_active && exp_age <= 16'(DT+16);\n"
              "    wire static_trigger = schedule_active && schedule_age == exp_age-16'd1;")
    ep = edit(ep, "(HEADS != 1 || EXP_START_AGE <= DT+16)", "(HEADS != 1)")
    ep = edit(ep, "            if (j_bad || (|se) || (trig && a_busy) ||", "            if (j_bad || (|se) || (trig && a_busy) || cal_bad ||")
    ctl = module(src, 'qkd_astk_ctl')
    ctl = edit(ctl, 'module qkd_astk_ctl #(', 'module qkd_astk_ctl_cal #(')
    ctl = edit(ctl, ") (\n    input  wire          ck,", ") (\n    input  wire [31:0]   cal,       // {Z start age, LMAX start age} (compiler calendar)\n    input  wire          ck,")
    ctl = edit(ctl, "    wire l_slot = schedule_active && schedule_age >= LMAX_START_AGE-1 && schedule_age < LMAX_START_AGE+3;\n"
                    "    wire [15:0] z_age = schedule_age - (Z_START_AGE-1);\n"
                    "    wire z_window = schedule_active && schedule_age >= Z_START_AGE-1;",
               "    reg  [31:0] cal_q, cal_r;\n    always @(posedge ck) cal_q <= cal;\n    always @(posedge ck) if (start) cal_r <= cal_q;\n"
               "    wire [15:0] lmax_age = cal_r[15:0], zst_age = cal_r[31:16];\n"
               "    wire cal_bad = STATIC_SCHEDULE && schedule_active && (lmax_age < 16'd1 || zst_age < lmax_age+16'd4);\n"
               "    wire l_slot = schedule_active && schedule_age >= lmax_age-16'd1 && schedule_age < lmax_age+16'd3;\n"
               "    wire [15:0] z_age = schedule_age - (zst_age-16'd1);\n"
               "    wire z_window = schedule_active && schedule_age >= zst_age-16'd1;")
    ctl = edit(ctl, "(HEADS != 1 || LMAX_START_AGE < 1 ||\n        Z_START_AGE < LMAX_START_AGE+4 || Z_STRIDE < 4)", "(HEADS != 1 || Z_STRIDE < 4)")
    # Z block sums by block index (static only, Q-VMWB 2026-10-15): the EP chain finishes a stack's PARTIAL last block
    # (fewer gam groups) before the full ones, so arrival order != block order when nblk >= 2 and T is not a multiple of
    # 128 in that stack (T = 1000/3000/5000/7000 faulted at the first Z slot). The static calendar reads block k at slot
    # k: write zf_m at the block tag, read at z_age / Z_STRIDE, presence per block (duplicate = fault). Legacy unchanged.
    ctl = edit(ctl, "    wire [132:0] z_hd = zf_m[zfr[3:0]];\n", "    wire [132:0] z_hd;\n    reg  [15:0]  zp;\n")
    ctl = edit(ctl, "    always @(posedge ck) if (zq[0] && stl == 7'd0) zf_m[zfw[3:0]] <= {zq[137:10], zq[5:2], zq[1]};",
               "    wire [3:0]   zf_wa = STATIC_SCHEDULE ? zq[5:2] : zfw[3:0];\n"
               "    always @(posedge ck) if (zq[0] && stl == 7'd0) zf_m[zf_wa] <= {zq[137:10], zq[5:2], zq[1]};")
    ctl = edit(ctl, "    wire z_done_slot = z_window && z_age == nblk * Z_STRIDE;\n",
               "    wire z_done_slot = z_window && z_age == nblk * Z_STRIDE;\n"
               "    wire [3:0] z_k = 4'(z_age / Z_STRIDE);\n"
               "    assign z_hd = zf_m[STATIC_SCHEDULE ? z_k : zfr[3:0]];\n"
               "    wire z_have = STATIC_SCHEDULE ? zp[z_k] : z_ne;\n")
    ctl = edit(ctl, "((l_slot && !kdone[0]) || (z_slot && !z_ne) ||", "((l_slot && !kdone[0]) || (z_slot && !z_have) || (z_in && zp[zq[5:2]]) ||")
    ctl = edit(ctl, "            if (z_in) begin zfw <= zfw + 5'd1;", "            if (z_in) begin zp[zq[5:2]] <= 1'b1; zfw <= zfw + 5'd1;")
    ctl = edit(ctl, "zfw <= 5'd0; zfr <= 5'd0; zh <= 2'd0; zovf <= 1'b0; f <= 1'b0; af <= 1'b0;",
               "zfw <= 5'd0; zfr <= 5'd0; zh <= 2'd0; zovf <= 1'b0; f <= 1'b0; af <= 1'b0; zp <= 16'd0;")
    ctl = edit(ctl, "zfw <= 5'd0; zfr <= 5'd0; zh <= 2'd0; f <= 1'b0; zovf <= 1'b0;\n",
               "zfw <= 5'd0; zfr <= 5'd0; zh <= 2'd0; f <= 1'b0; zovf <= 1'b0; zp <= 16'd0;\n")
    ctl = edit(ctl, "            if (pv_bad || (STATIC_SCHEDULE &&", "            if (pv_bad || cal_bad || (STATIC_SCHEDULE &&")
    tp8 = module(src, 'qkd_astk_ctl_tp8')
    tp8 = edit(tp8, 'module qkd_astk_ctl_tp8 #(', 'module qkd_astk_ctl_tp8_cal #(')
    tp8 = edit(tp8, ") (\n    input  wire          ck,", ") (\n    input  wire [31:0]   cal,\n    input  wire          ck,")
    tp8 = edit(tp8, "    qkd_astk_ctl #(", "    qkd_astk_ctl_cal #(")
    tp8 = edit(tp8, " u (.ck(ck),", " u (.cal(cal), .ck(ck),")
    stk = (ROOT / STACK_S).read_text()
    stk = stk[stk.index('module qkd_astk_native_stack_s'):]
    stk = edit(stk, 'module qkd_astk_native_stack_s #(', 'module qkd_astk_native_stack_cal #(')
    stk = edit(stk, '  input wire ck_c,', '  input wire [47:0] cal,   // {EXP base, Z start, LMAX start} compiler calendar of this command\n  input wire ck_c,')
    stk = edit(stk, ' qkd_astk_ctl_tp8 #(', ' qkd_astk_ctl_tp8_cal #(')
    stk = edit(stk, ' u_ctl(.ck(ck_c),', ' u_ctl(.cal(cal[31:0]),.ck(ck_c),')
    stk = edit(stk, '  qkd_astk_ep #(', '  qkd_astk_ep_cal #(')
    stk = edit(stk, ' u_ep(\n', ' u_ep(.cal_exp(16\'(cal[47:32]+9*e+RL*(e+e/2))),\n')
    top = (ROOT / NSTACK).read_text()
    top = top[top.index('module ot_qwen_tp8_attention_native_stack'):]
    top = edit(top, 'module ot_qwen_tp8_attention_native_stack #(', 'module ot_qwen_tp8_attention_native_stack_cal #(')
    top = edit(top, ' input wire rst_n,', ' input wire [47:0] cal,\n input wire rst_n,')
    # The stack index is a strap port (as qkd_ectl3 cfg / ASTK st already are): one master serves all four stacks.
    top = edit(top, ' parameter integer STACK=0,RL=1,', ' parameter integer RL=1,')
    top = edit(top, ' input wire [47:0] cal,', ' input wire [47:0] cal,\n input wire [1:0] stack_id,')
    top = edit(top, '.st(2\'(STACK))', '.st(stack_id)')
    top = edit(top, '.cfg({3\'(engine),2\'(STACK)})', '.cfg({3\'(engine),stack_id})')
    top = edit(top, ' qkd_astk_native_stack_s #(', ' qkd_astk_native_stack_cal #(')
    top = edit(top, ' u_astk(\n', ' u_astk(.cal(cal),\n')
    h = hashlib.sha256(SRC.read_bytes()).hexdigest()
    head = ('`timescale 1ns/1ps\n`ifndef KVD_HEADS\n`define KVD_HEADS 2\n`endif\n'
            f'// GENERATED by tools/qwen_attention_native/gen_astk_cal.py from {SRC.relative_to(ROOT)} sha256 {h}.\n'
            '// Do not edit; regenerate. Calendar-input variants of the sealed ASTK EP/CTL masters (Q-ATTN 2026-10-15).\n')
    hs = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (STACK_S, NSTACK)}
    head += ''.join(f'// derived also from {p} sha256 {v}\n' for p, v in hs.items())
    return head + ep + '\n' + ctl + '\n' + tp8 + '\n' + stk + '\n' + top

HUB = ROOT / 'rtl/hdc/nearhbm/ot_qkd_ahub_static.sv'
HUB_OUT = ROOT / 'rtl/hdc/nearhbm/ot_qkd_ahub_static_cal_gen.sv'

def derive_hub():
    src = HUB.read_text()
    core = module(src, 'qkd_ahub_static_core')
    core = edit(core, """module qkd_ahub_static_core #(
    parameter [63:0] LMAX_IN_AGE=0,
    parameter [63:0] Z_IN_AGE=0,
    parameter integer Z_IN_STRIDE=16,
    parameter integer LMAX_ISSUE_AGE=0,
    parameter integer Z_START_AGE=0,
    parameter integer Z_LEVEL_GAP=10,
    parameter integer RECIP_ISSUE_AGE=0,
    parameter integer RECIP_RETURN_AGE=0,
    parameter integer RZ_PUBLISH_AGE=0
)(
    input wire clk,rst_n,start,active_layer_parity,""", """module qkd_ahub_static_core_cal #(
    parameter integer Z_IN_STRIDE=16,
    parameter integer Z_LEVEL_GAP=10
)(
    // compiler calendar of this command: {RZ_PUBLISH, RECIP_RETURN, RECIP_ISSUE, Z_START, LMAX_ISSUE, Z_IN x4, LMAX_IN x4}
    input wire [207:0] cal,
    input wire clk,rst_n,start,active_layer_parity,""")
    core = edit(core, """    reg active,parity;reg [15:0] epoch;reg [5:0] layer;""",
"""    reg active,parity;reg [15:0] epoch;reg [5:0] layer;
    reg [63:0] LMAX_IN_AGE,Z_IN_AGE;reg [15:0] LMAX_ISSUE_AGE,Z_START_AGE,RECIP_ISSUE_AGE,RECIP_RETURN_AGE,RZ_PUBLISH_AGE;
    always @(posedge clk)if(start)
        {RZ_PUBLISH_AGE,RECIP_RETURN_AGE,RECIP_ISSUE_AGE,Z_START_AGE,LMAX_ISSUE_AGE,Z_IN_AGE,LMAX_IN_AGE}<=cal;
    // Z blocks per stack follow the context length exactly as the stack control emits them; absent blocks stay
    // unwritten and read as zero in ot_nhb_zh, the reference zero-leaf tree.
    reg [4:0] nblk[0:3];reg [63:0] zmask;
    always @*begin
        zmask=0;
        for(integer s=0;s<4;s=s+1)begin
            nblk[s]=(T>14'(128*s))?5'(((T-14'(128*s)-14'd1)>>9)+14'd1):5'd0;
            for(integer k=0;k<16;k=k+1)if(k<nblk[s])zmask[4*k+s]=1'b1;
        end
    end""")
    core = edit(core, "            if(active && edge_age>=Z_IN_AGE[16*s+:16] && edge_age<Z_IN_AGE[16*s+:16]+16*Z_IN_STRIDE)begin",
                      "            if(active && edge_age>=Z_IN_AGE[16*s+:16] && edge_age<Z_IN_AGE[16*s+:16]+nblk[s]*Z_IN_STRIDE)begin")
    core = edit(core, "            done_slot[s]=active && edge_age==Z_IN_AGE[16*s+:16]+16*Z_IN_STRIDE;",
                      "            done_slot[s]=active && edge_age==Z_IN_AGE[16*s+:16]+nblk[s]*Z_IN_STRIDE;")
    core = edit(core, "else if(start)fault<=(T!=8192)||(active_layer_parity!=active_layer[0]);",
                      "else if(start)fault<=(T==0)||(T>8192)||(active_layer_parity!=active_layer[0]);")
    core = edit(core, """zseen[0][63:0]!=64'hffffffffffffffff || zseen[1][63:0]!=64'hffffffffffffffff ||
                    zseen[2][63:0]!=64'hffffffffffffffff || zseen[3][63:0]!=64'hffffffffffffffff)) ||""",
"""zseen[0][63:0]!=zmask || zseen[1][63:0]!=zmask ||
                    zseen[2][63:0]!=zmask || zseen[3][63:0]!=zmask)) ||
                (active && edge_age==16'd1 && (LMAX_IN_AGE==0 || Z_IN_AGE==0 || LMAX_ISSUE_AGE<1 || Z_START_AGE<1 ||
                    RECIP_ISSUE_AGE<=Z_START_AGE+77 || RECIP_RETURN_AGE<=RECIP_ISSUE_AGE || RZ_PUBLISH_AGE<RECIP_RETURN_AGE+4)) ||""")
    core = edit(core, """    initial begin
        if(LMAX_IN_AGE==0 || Z_IN_AGE==0 || LMAX_ISSUE_AGE<1 || Z_START_AGE<1 || Z_LEVEL_GAP<10 ||
            RECIP_ISSUE_AGE<=Z_START_AGE+77 || RECIP_RETURN_AGE<=RECIP_ISSUE_AGE || RZ_PUBLISH_AGE<RECIP_RETURN_AGE+4 || Z_IN_STRIDE<4)
            $fatal(1,"unsealed/invalid static AHUB calendar");
    end""", """    initial if(Z_LEVEL_GAP<10 || Z_IN_STRIDE<4)$fatal(1,"invalid static AHUB geometry");""")
    die = module(src, 'ot_qkd_ahub_static_die')
    die = edit(die, """module ot_qkd_ahub_static_die #(
    parameter [63:0] LMAX_IN_AGE=0,Z_IN_AGE=0,
    parameter integer Z_IN_STRIDE=16,LMAX_ISSUE_AGE=0,Z_START_AGE=0,Z_LEVEL_GAP=10,
    parameter integer RECIP_ISSUE_AGE=0,RECIP_RETURN_AGE=0,RZ_PUBLISH_AGE=0,""", """module ot_qkd_ahub_static_die_cal #(
    parameter integer Z_IN_STRIDE=16,Z_LEVEL_GAP=10,""")
    die = edit(die, ")(\n    input wire ck_core,", ")(\n    // {RZ_PUBLISH, RECIP_ISSUE, Z_START, LMAX_ISSUE, Z_IN x4, LMAX_IN x4}; RECIP_RETURN is the fixed leaf+relay geometry\n    input wire [191:0] cal,\n    input wire ck_core,")
    die = edit(die, """    qkd_ahub_static_core #(.LMAX_IN_AGE(LMAX_IN_AGE),.Z_IN_AGE(Z_IN_AGE),.Z_IN_STRIDE(Z_IN_STRIDE),
        .LMAX_ISSUE_AGE(LMAX_ISSUE_AGE),.Z_START_AGE(Z_START_AGE),.Z_LEVEL_GAP(Z_LEVEL_GAP),
        .RECIP_ISSUE_AGE(RECIP_ISSUE_AGE),.RECIP_RETURN_AGE(RECIP_RETURN_AGE),.RZ_PUBLISH_AGE(RZ_PUBLISH_AGE)) u_core (""",
"""    wire [15:0] recip_return=cal[175:160]+16'(67+RX_RLY+RY_RLY);
    qkd_ahub_static_core_cal #(.Z_IN_STRIDE(Z_IN_STRIDE),.Z_LEVEL_GAP(Z_LEVEL_GAP)) u_core (
        .cal({cal[191:176],recip_return,cal[175:0]}),""")
    h = hashlib.sha256(HUB.read_bytes()).hexdigest()
    return ('`timescale 1ns/1ps\n'
            f'// GENERATED by tools/qwen_attention_native/gen_astk_cal.py from {HUB.relative_to(ROOT)} sha256 {h}.\n'
            '// Do not edit. Command-calendar variant of the six-root static AHUB: ages arrive with the command, Z block\n'
            '// presence follows T as the stack control emits it (zero leaves, as the reference tree). Q-ATTN 2026-10-15.\n'
            + core + '\n' + die)

FIN = ROOT / 'rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static.sv'
FIN_OUT = ROOT / 'rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static_cal_gen.sv'

def derive_final():
    src = FIN.read_text()
    j = module(src, 'ot_qwen_tp8_pv_join16_static')
    j = edit(j, """module ot_qwen_tp8_pv_join16_static #(
 parameter integer P0_AGE=8,P1_AGE=20,R_AGE=48,ADD_LAT=7,MUL_LAT=6
)(
 input wire clk,""", """module ot_qwen_tp8_pv_join16_static_cal #(
 parameter integer ADD_LAT=7,MUL_LAT=6
)(
 input wire [47:0] cal,   // {R_AGE, P1_AGE, P0_AGE} of this command (compiler calendar), captured at start
 input wire clk,""")
    j = edit(j, """ localparam integer LAST_CAPTURE=(P0_AGE>P1_AGE)?((P0_AGE>R_AGE)?P0_AGE:R_AGE):((P1_AGE>R_AGE)?P1_AGE:R_AGE);
 localparam integer ADD_AGE=LAST_CAPTURE+1,SUM_AGE=ADD_AGE+ADD_LAT;
 localparam integer MUL_AGE=SUM_AGE+1,PRODUCT_AGE=MUL_AGE+MUL_LAT,OUT_AGE=PRODUCT_AGE+1;
 reg active;reg[31:0] age;reg[15:0] ep;""", """ reg[31:0] P0_AGE,P1_AGE,R_AGE;
 always @(posedge clk)if(start)begin P0_AGE<=32'(cal[15:0]);P1_AGE<=32'(cal[31:16]);R_AGE<=32'(cal[47:32]);end
 wire[31:0] LAST_CAPTURE=(P0_AGE>P1_AGE)?((P0_AGE>R_AGE)?P0_AGE:R_AGE):((P1_AGE>R_AGE)?P1_AGE:R_AGE);
 wire[31:0] ADD_AGE=LAST_CAPTURE+1,SUM_AGE=ADD_AGE+ADD_LAT;
 wire[31:0] MUL_AGE=SUM_AGE+1,PRODUCT_AGE=MUL_AGE+MUL_LAT,OUT_AGE=PRODUCT_AGE+1;
 reg active;reg[31:0] age;reg[15:0] ep;""")
    j = edit(j, "   if(active||P0_AGE<1||P1_AGE<1||R_AGE<1)begin fault<=1;active<=0;end",
                "   if(active||cal[15:0]<1||cal[31:16]<1||cal[47:32]<1)begin fault<=1;active<=0;end")
    f = module(src, 'ot_qwen_tp8_pv256_finalize_static')
    f = edit(f, """module ot_qwen_tp8_pv256_finalize_static #(
 parameter integer P0_AGE=8,P1_AGE=20,R_AGE=48,ADD_LAT=7,MUL_LAT=6
)(
 input wire[31:0] clk_join,""", """module ot_qwen_tp8_pv256_finalize_static_cal #(
 parameter integer ADD_LAT=7,MUL_LAT=6
)(
 input wire[47:0] cal,
 input wire[31:0] clk_join,""")
    f = edit(f, """  ot_qwen_tp8_pv_join16_static #(.P0_AGE(P0_AGE),.P1_AGE(P1_AGE),.R_AGE(R_AGE),.ADD_LAT(ADD_LAT),.MUL_LAT(MUL_LAT)) u_join(""",
                """  ot_qwen_tp8_pv_join16_static_cal #(.ADD_LAT(ADD_LAT),.MUL_LAT(MUL_LAT)) u_join(.cal(cal),""")
    h = hashlib.sha256(FIN.read_bytes()).hexdigest()
    return ('`timescale 1ns/1ps\n'
            f'// GENERATED by tools/qwen_attention_native/gen_astk_cal.py from {FIN.relative_to(ROOT)} sha256 {h}.\n'
            '// Do not edit. Command-calendar capture ages for the static PV final join (Q-ATTN 2026-10-15).\n' + j + '\n' + f)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--check', action='store_true'); a = ap.parse_args()
    outs = {OUT: derive(), HUB_OUT: derive_hub(), FIN_OUT: derive_final()}
    for o, text in outs.items():
        if a.check:
            if o.read_text() != text: sys.exit(f'{o.name} is stale vs its sealed source')
            print(f'{o.name} current')
        else:
            o.write_text(text); print(o)

if __name__ == '__main__': main()
