#!/usr/bin/env python3
"""KV-SRAM-D2D 2026-10-19 (claude/kv-sram-d2d-1019): emit the RIGHT-SIZED-STORAGE KV link-end masters
qkd_d2d_static_sfm / qkd_d2d_static_ovl_sfm (core qkd_d2d_static_core_sfm) into
rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv, derived by exact text substitution from the safe fan-out sources
(ot_qwen_d2d_safe_fo.sv + the generated ot_qwen_d2d_dies_sfo.sv; both untouched, every closed / gated view still binds).

Differences from qkd_d2d_static[_ovl]_sf (SAFE-DESIGN checklist):
  * item 6 storage: the four slot-store banks use the truthful right-sized macro d2d_sram_1r1w_64x137_m1_r2c2_p192
    (SRAMV 1) or _p288 (SRAMV 2) from tools/mem_compiler/build_d2d_sram_1019.py: 64 slots x 137 b, the exact width the
    bank stores (FW 548 = 4 x 137), so the 375 tied-zero columns / 3,008 tied endpoints of the 64x512 disappear;
    write / read ports, write-age bypass and slot lifetime are unchanged (same generator, same behavioural model).
  * item 4 depth: the slot-link receive CRC is computed on the arriving pin-flop word and registered beside the
    received word (rx_crc <= crc(p_rx_flit) on the edge that captures rf <= p_rx_flit), so the fault cone
    rf -> CRC tree -> compare -> epoch_abort copies (gate worst -95.5 / -100.7 ps on ovl_sf / ovl_sfb) loses the
    CRC tree; same edge, same value (rx_crc == crc(rf) from the first edge).  The recovery's drain / reset counter n
    is 5 b (it never exceeds max(DRAIN, RSTC) - 1 = 31; the 16-b incrementer was the r7w_sf worst path -16.1 ps).
  * first-epoch guard (FEG 1, both calendars): each calendar records the receipt of every actually accepted image
    write (32 entries + segment-1 base) since its local reset; a start strobe is authorised only with the complete
    receipt, no write on the start edge or the edge before (earliest start W+2 after the last accepted write W) and no
    earlier rejection.  An unauthorised start never starts the calendar: it raises the calendar fault (-> end_fault ->
    epoch abort) and poisons the calendar (halted until local reset): fail-stop, never queued.  No port, no cycle on
    the healthy path (the production cold sequence writes all 66 words before the first start).
  * Z17 sideband: rx_zero17[16:0], 17 registered NONZERO predicates of the received payload captured on the exact
    q_rx_payload pin-flop edge (Z0 = |[31:19], Z1 = |[31:5], Z[z+1] = |[32z +: 32], z = 1..15; Codex fe8eac3f2 /
    8ec58f314 model), unreset like q_rx_payload.
MUTFO (bench only, in addition to the sf mutants 1..4): 5 = TX calendar guard disabled, 6 = receive CRC registered one
edge late (crc of the previous word), 7 = Z17 flag 0 omits payload bit 19.  MUTW = 1 (leaf): bank column 136 not
written (useful-width mutant).
Re-run after any edit of the safe fan-out sources:  python3 tools/qwen_split/d2d_sram_masters.py
"""
import re
from pathlib import Path

D = Path(__file__).resolve().parents[2] / 'rtl/qwen_sys/d2d_static_20261015'
SFO, SAFE, OUT = D / 'ot_qwen_d2d_dies_sfo.sv', D / 'ot_qwen_d2d_safe_fo.sv', D / 'ot_qwen_d2d_sfm.sv'


def module(t, name):
    m = re.search(r'\nmodule ' + re.escape(name) + r' #\(.*?\nendmodule', t, re.S)
    assert m, name
    return m.group(0).strip('\n')


def sub(t, a, b, n=1):
    assert t.count(a) == n, (t.count(a), a[:120])
    return t.replace(a, b)


def leaf(s):
    c = module(s, 'ot_qkvd_llr_replay_sram_leaf_sf')
    c = sub(c, 'module ot_qkvd_llr_replay_sram_leaf_sf #(', 'module ot_qkvd_llr_replay_sram_leaf_sfm #(')
    c = sub(c, 'MUT = 0, GB = 16, MUTFO = 0\n', 'MUT = 0, GB = 16, MUTFO = 0, SRAMV = 1, MUTW = 0\n')
    c = sub(c, '    wire [511:0] mr;\n', '    wire [W-1:0] mr;\n')
    c = sub(c, """    ot_sram_1r1w_64x512_m1_r2c2 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(512-W){1'b0}},dq}),
        .w_mask_in({{(512-W){1'b0}},{W{1'b1}}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
""", """    // right-sized bank (KV-SRAM-D2D): every one of the W = 137 columns stores a payload bit; spare rows / columns unused
    generate if (W != 137 || QD != 64) begin : g_shape
        OT_D2D_SRAM_BANK_IS_64X137 u_shape ();
    end endgenerate
    wire [W-1:0] wd = (MUTW != 0) ? {1'b0, dq[W-2:0]} : dq;
    generate if (SRAMV == 2) begin : g_p288
        d2d_sram_1r1w_64x137_m1_r2c2_p288 u_sram (
            .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr), .w_ce_in(wq), .w_addr_in(aq), .wd_in(wd),
            .w_mask_in({W{1'b1}}), .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(16'd0));
    end else if (SRAMV == 1) begin : g_p192
        d2d_sram_1r1w_64x137_m1_r2c2_p192 u_sram (
            .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr), .w_ce_in(wq), .w_addr_in(aq), .wd_in(wd),
            .w_mask_in({W{1'b1}}), .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(16'd0));
    end else begin : g_bad
        OT_D2D_SRAMV_1_OR_2 u_bad ();
    end endgenerate
""")
    return c


def ctl(s):
    c = module(s, 'ot_qwen_static_slot_ctl_sf')
    c = sub(c, 'module ot_qwen_static_slot_ctl_sf #(', 'module ot_qwen_static_slot_ctl_sfm #(')
    c = sub(c, '    wire [CW-1:0] tx_crc, rx_crc;\n', '    wire [CW-1:0] tx_crc, rx_crc_d, rx_crc_late;\n'
               '    (* keep = "true", dont_touch = "true" *) reg [CW-1:0] rx_crc;   // = crc(rf): same D word, same edge\n')
    c = sub(c, 'ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_rx_crc(.d(rf[FW+18:0]),.q(rx_crc));',
            'ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_rx_crc(.d(p_rx_flit[FW+18:0]),.q(rx_crc_d));\n'
            '    generate if (MUTFO == 6) begin : g_mut_crc_late   // bench mutant: CRC of the previous word\n'
            '        ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_rx_crc_late(.d(rf[FW+18:0]),.q(rx_crc_late));\n'
            '    end else begin : g_crc_now\n        assign rx_crc_late = rx_crc_d;\n    end endgenerate\n'
            '    (* keep = "true", dont_touch = "true" *) always @(posedge clk) rx_crc <= rx_crc_late;')
    return c


def link(s):
    c = module(s, 'ot_qwen_static_slot_link_sf')
    c = sub(c, 'module ot_qwen_static_slot_link_sf #(', 'module ot_qwen_static_slot_link_sfm #(')
    c = sub(c, 'parameter integer FW=548, CW=16, PW=FW+19+CW, MUT=0, MUTFO=0\n',
            'parameter integer FW=548, CW=16, PW=FW+19+CW, MUT=0, MUTFO=0, SRAMV=1\n')
    c = sub(c, 'ot_qkvd_llr_replay_sram_leaf_sf #(.W(BW),.MUT(MUT==3 && b==0),.MUTFO(b==0 ? MUTFO : 0)) u_store(',
            'ot_qkvd_llr_replay_sram_leaf_sfm #(.W(BW),.MUT(MUT==3 && b==0),.MUTFO(b==0 ? MUTFO : 0),.SRAMV(SRAMV)) u_store(')
    c = sub(c, 'ot_qwen_static_slot_ctl_sf #(.FW(FW),.CW(CW),.PW(PW),.MUTFO(MUTFO)) u_ctl (',
            'ot_qwen_static_slot_ctl_sfm #(.FW(FW),.CW(CW),.PW(PW),.MUTFO(MUTFO)) u_ctl (')
    return c


GUARD = """    // ---- FIRST-EPOCH GUARD (FEG; KV-SRAM-D2D 10-19).  Receipt of every ACCEPTED image write since local POR (the same
    // predicates as the image / base register writes).  A start is authorised only with the complete receipt (32 entries
    // + segment-1 base), no write on the start edge or the edge before (earliest start = W+2 after the last accepted
    // write W) and no earlier rejection.  An unauthorised start does not start: it faults and poisons the calendar
    // (halted until local reset).  ok_c: 4 KEPT copies of the registered authorisation, one D net. ----
    localparam integer FEGON = (FEG != 0) && (MUTFO != 5);
    wire wr_entry = cfg_we && !running && !cfg_addr[AW];
    reg [NE-1:0] seen;
    reg base_seen, poison;
    (* keep = "true", dont_touch = "true" *) reg [3:0] ok_c;
    wire auth = ok_c[0] && !cfg_we;
    wire reject = start_c[0] && !auth;
    wire poison_d = poison | reject;
    wire ok_d = (&seen) && base_seen && !cfg_we && !poison_d;
    // The receipt follows the IMAGE's lifetime: the image registers are unreset and accept a write whenever cfg_we &&
    // !running, including inside the 4-edge local rst_n release window (the cold boot writes there), so the receipt
    // clears only on the local cold POR (por_n: image content undefined) and counts every write the image accepts
    // after it.  The rejection state (poison) and the authorisation copies clear on the calendar's local rst_n.
    always @(posedge ck or negedge por_n)
        if (!por_n) begin seen <= {NE{1'b0}}; base_seen <= 1'b0; end
        else begin
            if (wr_entry) seen[cfg_addr[AW-1:0]] <= 1'b1;
            if (seg_we) base_seen <= 1'b1;
        end
    (* keep = "true", dont_touch = "true" *) always @(posedge ck or negedge rst_n)
        if (!rst_n) begin poison <= 1'b0; ok_c <= 4'd0; end
        else begin poison <= poison_d; ok_c <= {4{ok_d}}; end
    wire [3:0] st_a = FEGON ? (start_c & ok_c & {4{!cfg_we}}) : start_c;
    wire [3:0] ht_a = FEGON ? (halt_c | {4{poison}}) : halt_c;
"""


def cal(s):
    c = module(s, 'ot_qwen_d2d_cal_sf')
    c = sub(c, 'module ot_qwen_d2d_cal_sf #(parameter integer NE = 32, parameter integer AW = $clog2(NE), parameter integer MUTFO = 0) (',
            'module ot_qwen_d2d_cal_sfg #(parameter integer NE = 32, parameter integer AW = $clog2(NE), parameter integer MUTFO = 0,\n'
            '    parameter integer FEG = 1) (\n    input  wire          por_n,          // local cold POR copy (first-epoch guard receipt)')
    a = '    wire [NE-1:0] sel1_dec = {{(NE-1){1\'b0}}, 1\'b1} << cfg_base_c;\n'
    c = sub(c, a, a + GUARD)
    head, body = c.split(GUARD)
    i = body.index('    // first word fields')
    pre, post = body[:i], body[i:]
    j = post.index('`ifdef OT_FO_CHECK')
    logic, chk = post[:j], post[j:]
    logic = logic.replace('halt_c[', 'ht_a[').replace('start_c[', 'st_a[')
    logic = sub(logic, "            if (cfg_we && running) fault <= 1'b1;\n",
                "            if (cfg_we && running) fault <= 1'b1;\n"
                "            if (FEGON && (reject || poison)) fault <= 1'b1;               // first-epoch guard: fail-stop\n")
    chk = sub(chk, '(sel1_c1 !== sel1_c0 || pc1 !== pc0 || run_c !== running)',
              '(sel1_c1 !== sel1_c0 || pc1 !== pc0 || run_c !== running || ok_c !== {4{ok_c[0]}})')
    return head + GUARD + pre + logic + chk


def end(s):
    c = module(s, 'ot_qwen_d2d_static_end_sf')
    c = sub(c, 'module ot_qwen_d2d_static_end_sf #(', 'module ot_qwen_d2d_static_end_sfm #(')
    c = sub(c, '    parameter integer MUTFO = 0\n) (', '    parameter integer MUTFO = 0,\n    parameter integer SRAMV = 1,\n'
               '    parameter integer FEG = 1\n) (')
    c = sub(c, 'ot_qwen_d2d_cal_sf #(.NE(NE), .MUTFO(MUTFO)) u_txcal (', 'ot_qwen_d2d_cal_sfg #(.NE(NE), .MUTFO(MUTFO), .FEG(FEG)) u_txcal (.por_n(por_c[0]), ')
    c = sub(c, 'ot_qwen_d2d_cal_sf #(.NE(NE)) u_rxcal (', 'ot_qwen_d2d_cal_sfg #(.NE(NE), .FEG(FEG)) u_rxcal (.por_n(por_c[1]), ')
    c = sub(c, '    input  wire [NRC-1:0]   rst_n,\n', '    input  wire [NRC-1:0]   rst_n,\n    input  wire [1:0]       por_c,        // local POR copies: [0] TX, [1] RX calendar receipt\n')
    c = sub(c, 'ot_qwen_static_slot_link_sf #(.FW(FW), .CW(CW), .PW(PW), .MUTFO(MUTFO)) u_link (',
            'ot_qwen_static_slot_link_sfm #(.FW(FW), .CW(CW), .PW(PW), .MUTFO(MUTFO), .SRAMV(SRAMV)) u_link (')
    return c


def rec(s):
    c = module(s, 'ot_qwen_d2d_recovery_sf')
    c = sub(c, 'module ot_qwen_d2d_recovery_sf #(', 'module ot_qwen_d2d_recovery_sfm #(')
    c = sub(c, '    reg [2:0] st; reg [15:0] n; reg seen, lrst, fep, bq;',
            '    // n counts the drain / reset intervals only: 0 .. max(DRAIN, RSTC) - 1 (cleared on every entry), so NW bits\n'
            '    localparam integer NW = $clog2((DRAIN > RSTC) ? DRAIN : RSTC);\n'
            '    reg [2:0] st; reg [NW-1:0] n; reg seen, lrst, fep, bq;')
    return c


def core(t):
    c = module(t, 'qkd_d2d_static_core_sf')
    c = sub(c, 'module qkd_d2d_static_core_sf #(', 'module qkd_d2d_static_core_sfm #(')
    c = sub(c, 'parameter integer OVL = 0, parameter integer SAFE_RC = 1, parameter integer MUTFO = 0) (',
            'parameter integer OVL = 0, parameter integer SAFE_RC = 1, parameter integer MUTFO = 0,\n'
            '    parameter integer SRAMV = 1, parameter integer FEG = 1) (')
    c = sub(c, 'ot_qwen_d2d_recovery_sf #(.MASTER(1), .NEB(NEB)) u_rec (', 'ot_qwen_d2d_recovery_sfm #(.MASTER(1), .NEB(NEB)) u_rec (')
    c = sub(c, 'ot_qwen_d2d_static_end_sf #(.NT(NTX), .NR(4), .TXD(TXDP), .MUT(MUT), .OVL(OVL), .NRC(4), .NG2(NG2), .MUTFO(MUTFO)) u_end (',
            'ot_qwen_d2d_static_end_sfm #(.NT(NTX), .NR(4), .TXD(TXDP), .MUT(MUT), .OVL(OVL), .NRC(4), .NG2(NG2), .MUTFO(MUTFO), '
            '.SRAMV(SRAMV), .FEG(FEG)) u_end (.por_c({2{local_por_n[0]}}),')
    return c


Z17 = """    // Z17 sideband (KV-SRAM-D2D): 17 NONZERO predicates of the received payload, captured on the q_rx_payload edge
    // (Z0 = |[31:19], Z1 = |[31:5], Z[z+1] = |[32z +: 32] for z = 1..15); unreset, like q_rx_payload
    reg [16:0] q_rx_zero17;
    wire [16:0] c_rx_zero17;
    assign c_rx_zero17[0] = (MUTFO == 7) ? (|c_rx_payload[31:20]) : (|c_rx_payload[31:19]);
    assign c_rx_zero17[1] = |c_rx_payload[31:5];
    genvar zz;
    for (zz = 1; zz <= 15; zz = zz + 1) begin : g_z17
        assign c_rx_zero17[zz + 1] = |c_rx_payload[32*zz +: 32];
    end
    always @(posedge ck) q_rx_zero17 <= c_rx_zero17;
    assign rx_zero17 = PR ? q_rx_zero17 : c_rx_zero17;
"""


def wrapper(t, name, new):
    w = module(t, name)
    w = sub(w, f'module {name} #(parameter integer MUT = 0, parameter integer NL = 2, parameter integer NTX = 4, '
               'parameter integer SAFE_RC = 1, parameter integer MUTFO = 0,',
            f'module {new} #(parameter integer MUT = 0, parameter integer NL = 2, parameter integer NTX = 4, '
            'parameter integer SAFE_RC = 1, parameter integer MUTFO = 0, parameter integer SRAMV = 1, parameter integer FEG = 1,')
    w = sub(w, '    output wire [547:0] rx_payload,\n', '    output wire [547:0] rx_payload,\n    output wire [16:0] rx_zero17,\n')
    a = '    assign rx_payload = PR ? q_rx_payload : c_rx_payload;\n'
    w = sub(w, a, a + Z17)
    w = sub(w, 'qkd_d2d_static_core_sf #(', 'qkd_d2d_static_core_sfm #(.SRAMV(SRAMV), .FEG(FEG), ')
    return w


def main():
    s, t = SAFE.read_text(), SFO.read_text()
    hdr = ('`timescale 1ns/1ps\n// GENERATED by tools/qwen_split/d2d_sram_masters.py from ot_qwen_d2d_safe_fo.sv + ot_qwen_d2d_dies_sfo.sv '
           '(do not edit): KV-SRAM-D2D 10-19\n// right-sized-storage KV link-end masters qkd_d2d_static_sfm / qkd_d2d_static_ovl_sfm. '
           'Source list: the qkd_d2d_static_sf list +\n// ot_qwen_d2d_sfm.sv + the d2d_sram_1r1w_64x137_m1_r2c2_p192 / _p288 views.\n')
    parts = [leaf(s), ctl(s), link(s), cal(s), end(s), rec(s), core(t),
             wrapper(t, 'qkd_d2d_static_sf', 'qkd_d2d_static_sfm'), wrapper(t, 'qkd_d2d_static_ovl_sf', 'qkd_d2d_static_ovl_sfm')]
    OUT.write_text(hdr + '\n\n'.join(parts) + '\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
