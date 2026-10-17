#!/usr/bin/env python3
"""KVE-2-ASTK 2026-10-17: derive the credit-free, lane-free ASTK leaves from the selected static (calendar) masters.

Sources: rtl/qwen_sys/split_20261014/qkd_astk_cal_gen.sv (qkd_astk_ep_cal, qkd_astk_ctl_cal) and
rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv (qkd_astk_ex).  Output: rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv
Usage: gen_astk_static.py CAL_GEN.sv LEAVES.sv OUT.sv
"""
import hashlib, re, sys
from pathlib import Path

def once(s, a, b):
    n = s.count(a)
    if n != 1:
        raise SystemExit(f'source binding mismatch ({n}x): {a[:80]!r}')
    return s.replace(a, b)

def mod(text, name):
    m = re.search(r'^module ' + name + r' #?\(.*?^endmodule\n', text, re.M | re.S)
    if not m:
        raise SystemExit('module not found: ' + name)
    return m.group()

cal_p, lv_p, out_p = map(Path, sys.argv[1:4])
cal, lv = cal_p.read_text(), lv_p.read_text()

# ---- EP: static calendar slice, no tree lanes, no node credit ----------------------------------------------------------
ep = mod(cal, 'qkd_astk_ep_cal')
ep = once(ep, '''module qkd_astk_ep_cal #(
    parameter integer STATIC_SCHEDULE=0,
    parameter integer EXP_START_AGE=0,
    parameter integer HEADS=`KVD_HEADS
) (''', 'module qkd_astk_ep_s (')
ep = once(ep, '    input  wire [424:0]  so,\n    output wire [633:0]  si,\n',
          '    input  wire [411:0]  so,        // engine so[411:0] (er / sc / lmax); the engine fault so[424] is sf\n'
          '    input  wire          sf,\n'
          '    output wire [632:0]  si,        // engine si[632:0]: no node credit (si[633] of the credit design is gone)\n')
ep = once(ep, '    input  wire          cr,\n', '')
ep = once(ep, '    input  wire [15:0]   cal_exp,   // this EP\'s EXP start age (compiler calendar)\n',
          '    input  wire [15:0]   cal_exp,   // the command\'s EXP base age (compiler calendar, held through the start edge)\n'
          '    input  wire [7:0]    eo,        // strap: this slice\'s EXP offset (9 e + RL (e + e / 2) in the strip)\n')
ep = once(ep, '    always @(posedge ck) cal_exp_q <= cal_exp;\n',
          '    (* keep *) reg [7:0] eo_q;\n    always @(posedge ck) begin cal_exp_q <= cal_exp; eo_q <= eo; end\n')
ep = once(ep, '    always @(posedge ck) if (start) exp_age <= cal_exp_q;\n',
          '    always @(posedge ck) if (start) exp_age <= cal_exp_q + {8\'d0, eo_q};\n')
ep = re.sub(r'    input  wire \[535:0\]  ui,.*?output wire         fo\n', '', ep, count=1, flags=re.S)
ep = once(ep, '    input  wire [135:0]  xe,\n);', '    input  wire [135:0]  xe\n);')
ep = once(ep, '''    (* keep_hierarchy *) qkd_astk_lanes u_l (.ck(ck), .rn(rn_q), .ui(ui), .uo(uo), .di(di), .do_(do_), .pi(pi), .po(po),
        .ci(ci), .co(co), .kui(kui), .kuo(kuo), .kdi(kdi), .kdo(kdo), .tui(tui), .tuo(tuo), .tdi(tdi), .tdo(tdo), .fi(fi), .fo(fo));
''', '''    localparam integer STATIC_SCHEDULE = 1, HEADS = 1;
    wire [424:0] so_x = {sf, 12'd0, so};               // so[423:412] (node beats, k / v done) are not read
''')
ep = once(ep, '    (* keep *) reg         cr_q;\n', '')
ep = once(ep, 'eqc <= 8\'d0; cr_q <= 1\'b0; end', 'eqc <= 8\'d0; end')
ep = once(ep, 'eqc <= {xe[103:102], xe[69:68], xe[35:34], xe[1:0]}; cr_q <= cr; end',
          'eqc <= {xe[103:102], xe[69:68], xe[35:34], xe[1:0]}; end')
ep = once(ep, 'so_q[424] <= so[424]; qq[0]', 'so_q[424] <= so_x[424]; qq[0]')
ep = once(ep, 'so_q[12:1] <= so[12:1]; so_q[423:14] <= so[423:14];', 'so_q[12:1] <= so[12:1]; so_q[411:14] <= so[411:14];')
ep = once(ep, 'so_q[0] <= so[0]; so_q[13] <= so[13];', 'so_q[0] <= so[0]; so_q[13] <= so[13];')
ep = once(ep, '(* keep *) reg [424:0] so_q;', '(* keep *) reg [424:0] so_q;            // [423:412] unused (no flops)')
ep = once(ep, '    initial if (STATIC_SCHEDULE && (HEADS != 1))\n        $fatal(1,"invalid static ASTK EXP profile");\n', '')
ep = once(ep, '(* keep *) reg [569:0] sio;', '(* keep *) reg [568:0] sio;')
ep = once(ep, 'sio[569:537] <= 33\'d0; end', 'sio[568:537] <= 32\'d0; end')
ep = once(ep, 'sio[568:537] <= xdq; sio[569] <= cr_q; end', 'sio[568:537] <= xdq; end')
ep = once(ep, 'assign si = {sio[569], e_rdq, sio[568:0]};', 'assign si = {e_rdq, sio[568:0]};')
ep = once(ep, "(`KVD_AKMUT == 2) ? 6'd1 : 6'd0", "(`KVD_STMUT == 1) ? 6'd1 : 6'd0")
assert 'cr' not in re.findall(r'\bcr\b', ep), 'cr left'
for w in ('ui', 'kui', 'fo', 'u_l'):
    assert not re.search(r'\b' + w + r'\b', ep), w + ' left'

# ---- EX: one head's exp pipe, no tree lanes ------------------------------------------------------------------------
ex = mod(lv, 'qkd_astk_ex')
ex = once(ex, 'module qkd_astk_ex (', 'module qkd_astk_ex_s (')
ex = re.sub(r'    output reg  \[33:0\]   xe,\n.*?output wire         fo\n', '    output reg  [33:0]   xe\n', ex, count=1, flags=re.S)
ex = re.sub(r'    \(\* keep_hierarchy \*\) qkd_astk_lanes u_l .*?\.fo\(fo\)\);\n', '', ex, count=1, flags=re.S)
ex = once(ex, "(`KVD_AKMUT == 5) ? 32'd1 : 32'd0", "(`KVD_STMUT == 2) ? 32'd1 : 32'd0")
for w in ('ui', 'kui', 'fo', 'u_l'):
    assert not re.search(r'\b' + w + r'\b', ex), w + ' left'

# ---- CTL: static calendar port without the legacy P.V lanes ---------------------------------------------------------
ct = mod(cal, 'qkd_astk_ctl_cal')
ct = once(ct, '''module qkd_astk_ctl_cal #(
    parameter integer HEADS = `KVD_HEADS,  // native TP8 = 1
    parameter integer STATIC_SCHEDULE=0,
    parameter integer LMAX_START_AGE=0,
    parameter integer Z_START_AGE=0,
    parameter integer Z_STRIDE=4
) (''', '''module qkd_astk_ctl_s #(
    parameter integer Z_STRIDE=4
) (''')
ct = once(ct, '    output reg  [564:0]  ap,\n', '    output reg  [42:0]   ap,         // the hub sideband {so_data 32, so_any, so_k 4, so_hh 2, so_g, so_type 2, so_valid}\n')
ct = once(ct, '    output reg  [5:0]    co,\n    input  wire [262:0]  px,\n    input  wire [262:0]  py,\n', '')
ct = once(ct, '    input  wire          fx,\n    input  wire          fy,\n', '')
ct = once(ct, '    (* keep *) reg rn_q;', '''    localparam integer HEADS = 1, STATIC_SCHEDULE = 1;   // the LMAX / Z start ages come from cal
    reg  [5:0]   co;                                   // the legacy tree cells' {gmax, start}: no load
    wire [262:0] px = 263'd0, py = 263'd0;             // P.V is the pvw's (no tree lanes reach the port)
    wire         fx = 1'b0, fy = 1'b0;
    (* keep *) reg rn_q;''')
ct = once(ct, "ap[0] <= 1'b0; ap[45:43] <= 3'b000; lt[0]", "ap[0] <= 1'b0; lt[0]")
ct = once(ct, "ap[0] <= 1'b0; ap[45] <= pv_v; ap[44:43] <= pvd;", "ap[0] <= 1'b0;")
ct = re.sub(r"        ap\[564:46\] <= \{pvw, 1'b0, pxq\[5:1\], pxq\[6\]\};\n", '', ct, count=1)
ct = once(ct, "(`KVD_AKMUT == 4) ? pyq[262:7] : pxq[262:7]", "pxq[262:7]")
ct = once(ct, "(`KVD_AKMUT == 4) ? pxq[262:7] : pyq[262:7]", "pyq[262:7]")
ct = once(ct, "if (z_emit) ap[42:1] <= {z_s,", "if (z_emit) ap[42:1] <= {z_s ^ ((`KVD_STMUT == 3) ? 32'd1 : 32'd0),")
assert 'ap[45' not in ct and 'ap[564' not in ct

hdr = f'''`timescale 1ns/1ps
`ifndef KVD_STMUT
`define KVD_STMUT 0
`endif
// ---------------------------------------------------------------------------------------------------------------------
// KVE-2-ASTK 2026-10-17: credit-free, lane-free successors of the ASTK strip leaves (owner static-cycle rule; HANDOFF 0db).
// GENERATED by tools/qwen_kv_die/gen_astk_static.py -- do not edit; regenerate.
//   {cal_p.name} sha256 {hashlib.sha256(cal.encode()).hexdigest()}
//   {lv_p.name} sha256 {hashlib.sha256(lv.encode()).hexdigest()}
// The selected static attention (ot_qwen_tp8_attention_native_service_w16) computes P.V in the pvw pairs from the ASTK e
// rows; its ASTK (qkd_astk_native_stack_*cal) has no P.V tree cells, ties every lane / credit input of qkd_astk_ep_cal and
// qkd_astk_ex to 0 and leaves the heads' node beats (nb_d) unconnected.  So the tree cells (qkd_astk_pv / _pv_tp8), the
// lanes that crossed ep / ex (ui / di / pi / ci / kui / kdi / tui / tdi / fi, 1,358 b a face), the node credits
// (cra / crb -> ep cr -> engine nb_cr) and the local credits (lci / lco) carry no work on the static timeline.
// These successors are the calendar masters with those ports removed; logic and edges are otherwise identical:
//   qkd_astk_ep_s   = qkd_astk_ep_cal  (STATIC 1, HEADS 1)  - lanes, cr, si[633] (nb_cr); so[423:412] not taken
//   qkd_astk_ex_s   = qkd_astk_ex                          - lanes
//   qkd_astk_ctl_s  = qkd_astk_ctl_cal (STATIC 1, HEADS 1) - px / py / fx / fy / co; ap = the 43-b sideband only
// Every remaining data input is captured in a pin register (unchanged from the masters).  Bench (lockstep against the
// selected composition qkd_astk_native_stack_cal): rtl/test/qwen_kv_die/tb_qkd_astk_strip_st.sv.
// Mutants (`KVD_STMUT): 1 ep_s e rows written one address off; 2 ex_s e one ulp off; 3 ctl_s Z word one ulp off.
// ---------------------------------------------------------------------------------------------------------------------
'''
out_p.write_text(hdr + '\n' + ep + '\n' + ex + '\n' + ct)
print('wrote', out_p)
