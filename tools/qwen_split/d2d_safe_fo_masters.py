#!/usr/bin/env python3
"""KV-D2D 2026-10-19 (claude/kv-d2d-1019): emit the SAFE FAN-OUT KV link-end masters
qkd_d2d_static_sf / qkd_d2d_static_ovl_sf and their core qkd_d2d_static_core_sf
(rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_sfo.sv) from the as-built pin-registered master qkd_d2d_static and
core qkd_d2d_static_core in ot_qwen_d2d_dies.sv.

Same ports, same pin registers, same hierarchy names (u_core.u_end, u_core.u_st, u_core.u_reset_regions ...), same
cycle-level behaviour.  Differences (SAFE-DESIGN checklist item 3; see ot_qwen_d2d_safe_fo.sv):
  * the core builds ot_qwen_d2d_static_end_sf / ot_qwen_d2d_status_rx_sf, 12 epoch_begin copies (ot_qwen_d2d_recovery_sf
    NEB) and 12-copy reset families per region (ot_rst_pipe COPIES; the kit sets OT_RST_COPIES_MAX);
  * the wrapper adds identical KEPT pin-flop copies of cal_start / cal_seg (4 per calendar; the OVL master's RX calendar
    copies sample cal_start_rx / cal_seg_rx) and of cfg_addr (1 per calendar) / cfg_data (2 per calendar): every copy
    samples the same pin, so it equals the original pin flop from the first edge.
The as-built modules are untouched, so every closed view still binds.  MUTFO is a bench-only mutant selector.
Re-run after any edit of the as-built masters:  python3 tools/qwen_split/d2d_safe_fo_masters.py
"""
import importlib.util
import re
from pathlib import Path

D = Path(__file__).resolve().parents[2] / 'rtl/qwen_sys/d2d_static_20261015'
SRC, OUT = D / 'ot_qwen_d2d_dies.sv', D / 'ot_qwen_d2d_dies_sfo.sv'
_spec = importlib.util.spec_from_file_location('ovl', Path(__file__).resolve().parent / 'd2d_ovl_masters.py')
OVL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(OVL)


def module(t, name):
    m = re.search(r'\nmodule ' + name + r' #\(.*?\nendmodule', t, re.S)
    assert m, name
    return m.group(0).strip('\n')


def sub(t, a, b, n=1):
    assert t.count(a) == n, (t.count(a), a[:100])
    return t.replace(a, b)


def core(t):
    c = module(t, 'qkd_d2d_static_core')
    c = sub(c, 'module qkd_d2d_static_core #(', 'module qkd_d2d_static_core_sf #(')
    c = sub(c, 'parameter integer OVL = 0, parameter integer SAFE_RC = 0) (',
            'parameter integer OVL = 0, parameter integer SAFE_RC = 1, parameter integer MUTFO = 0) (')
    c = sub(c, """    output wire         epoch_abort, output wire [31:0] recovery_cycles, output wire fault
);""", """    output wire         epoch_abort, output wire [31:0] recovery_cycles, output wire fault,
    // identical pin-flop copies (wrapper): cal_start / cal_seg [3:0] TX calendar, [7:4] RX calendar; cfg_addr [5:0] TX,
    // [11:6] RX; cfg_data [63:0] TX table halves, [127:64] RX table halves
    input  wire [7:0]   sf_start, sf_seg, input wire [11:0] sf_cfg_addr, input wire [127:0] sf_cfg_data,
    input  wire [9:0]   sf_cfg_base
);
    generate if (SAFE_RC != 1) begin : g_sfo_needs_rc
        QKD_D2D_SAFE_FO_NEEDS_SAFE_RC1 u_sfo_rc ();
    end endgenerate
    localparam integer NEB = 12;   // epoch_begin copies: [7:0] slot link, [9:8] end, [10] STATUS / KVN, [11] spare
    localparam integer RCP = 12;   // reset copies per region (ot_rst_pipe COPIES; OT_RST_COPIES_MAX spreads the loads)
    localparam integer NG2 = 10;   // STATUS capture groups
    wire [NEB-1:0] ebc;
    wire [NG2-1:0] st_ev_c, st_rs_c;""")
    c = sub(c, 'ot_rst_pipe #(.REGIONS(NREG), .STAGES(2)) u_reset_regions',
            'ot_rst_pipe #(.REGIONS(NREG), .STAGES(2), .COPIES(RCP)) u_reset_regions')
    c = sub(c, 'ot_rst_pipe #(.REGIONS(1), .STAGES(2)) u_por_region',
            'ot_rst_pipe #(.REGIONS(1), .STAGES(2), .COPIES(RCP)) u_por_region')
    c = sub(c, 'ot_qwen_d2d_recovery #(.MASTER(1)) u_rec (', 'ot_qwen_d2d_recovery_sf #(.MASTER(1), .NEB(NEB)) u_rec (')
    c = sub(c, '.recovery_cycles(recovery_cycles));', '.recovery_cycles(recovery_cycles), .epoch_begin_c(ebc));')
    c = sub(c, 'ot_qwen_d2d_static_end #(.NT(NTX), .NR(4), .TXD(TXDP), .MUT(MUT), .OVL(OVL), .NRC(SAFE_RC ? 4 : 1)) u_end (',
            'ot_qwen_d2d_static_end_sf #(.NT(NTX), .NR(4), .TXD(TXDP), .MUT(MUT), .OVL(OVL), .NRC(4), .NG2(NG2), '
            '.MUTFO(MUTFO)) u_end (')
    c = sub(c, '.cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),',
            '.cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr_c(sf_cfg_addr), .cfg_data_c(sf_cfg_data), '
            '.cfg_base_c(sf_cfg_base), .eb_c(ebc[9:0]),')
    c = sub(c, '.epoch_begin(eb), .epoch(ep), .cal_start(cal_start), .cal_seg(cal_seg),',
            '.epoch_begin(eb), .epoch(ep), .cal_start(cal_start), .start_c(sf_start), .seg_c(sf_seg),')
    c = sub(c, '.cal_start_rx(cal_start_rx), .cal_seg_rx(cal_seg_rx), .cal_user_tx(cal_user_tx)',
            '.cal_start_rx(cal_start_rx), .cal_user_tx(cal_user_tx)')
    c = sub(c, '.rx_beat(rb), .rx_payload(rxp),\n', '.rx_beat(rb), .rx_payload(rxp), .st_ev_c(st_ev_c), .st_rs_c(st_rs_c),\n')
    c = sub(c, 'ot_qwen_d2d_status_rx u_st (.ck(ck), .rst_n(local_rst_n[2]), .epoch16(status_epoch16), .rx_event(rxe[2]), .rx_slot(rxs[2]),',
            'ot_qwen_d2d_status_rx_sf #(.NG(NG2)) u_st (.ck(ck), .rst_n(local_rst_n[2]), .epoch16(status_epoch16), '
            '.rx_event(rxe[2]), .rx_slot(rxs[2]),\n        .ev_c(st_ev_c), .rs_c(st_rs_c),')
    c = sub(c, '.result_value(engine_result_value), .result_cycles(engine_result_cycles), .epoch_begin(eb), .fault(s_f));',
            '.result_value(engine_result_value), .result_cycles(engine_result_cycles), .epoch_begin(ebc[10]), .fault(s_f));')
    c = sub(c, 'ot_qwen_d2d_kvn_rx u_kvn (.ck(ck), .rst_n(local_rst_n[3] & ~eb),',
            'ot_qwen_d2d_kvn_rx u_kvn (.ck(ck), .rst_n(local_rst_n[3] & ~ebc[10]),')
    return c


COPIES = """    // KV-D2D SAFE FAN-OUT (d2d_safe_fo_masters.py): identical KEPT pin-flop copies.  Each samples the same pin as the
    // original pin flop, so it equals that flop from the first edge; the calendars load one field group per copy.
    generate if (PR != 1) begin : g_sfo_needs_pr
        QKD_D2D_SAFE_FO_NEEDS_PR1 u_sfo_pr ();
    end endgenerate
    wire sf_rx_start_pin = cal_start, sf_rx_seg_pin = cal_seg;   // RX calendar start / segment pins (OVL: the RX pins)
    (* keep = "true", dont_touch = "true" *) reg [7:0] q_sf_start;
    (* keep = "true", dont_touch = "true" *) reg [7:0] q_sf_seg;
    (* keep = "true", dont_touch = "true" *) reg [11:0] q_sf_cfg_addr;
    (* keep = "true", dont_touch = "true" *) reg [127:0] q_sf_cfg_data;
    (* keep = "true", dont_touch = "true" *) reg [9:0] q_sf_cfg_base;
    (* keep = "true", dont_touch = "true" *) always @(posedge ck) begin
        q_sf_start <= {{4{sf_rx_start_pin}}, {4{cal_start}}};
        q_sf_seg <= {{4{sf_rx_seg_pin}}, {4{cal_seg}}};
        q_sf_cfg_addr <= {2{cfg_addr}};
        q_sf_cfg_data <= {4{cfg_data}};
        q_sf_cfg_base <= {2{cfg_data[4:0]}};
    end
"""


def wrapper(t):
    w = module(t, 'qkd_d2d_static')
    w = sub(w, 'module qkd_d2d_static #(parameter integer MUT = 0, parameter integer NL = 2, parameter integer NTX = 4, '
               'parameter integer SAFE_RC = 0,',
            'module qkd_d2d_static_sf #(parameter integer MUT = 0, parameter integer NL = 2, parameter integer NTX = 4, '
            'parameter integer SAFE_RC = 1, parameter integer MUTFO = 0,')
    i = w.index('    wire c_cal_start;')
    w = w[:i] + COPIES + w[i:]
    w = sub(w, 'qkd_d2d_static_core #(.MUT(MUT), .SAFE_RC(SAFE_RC),',
            'qkd_d2d_static_core_sf #(.MUT(MUT), .MUTFO(MUTFO), .SAFE_RC(SAFE_RC),')
    w = sub(w, '.fault(c_fault));', '.fault(c_fault), .sf_start(q_sf_start), .sf_seg(q_sf_seg), '
                                    '.sf_cfg_addr(q_sf_cfg_addr), .sf_cfg_data(q_sf_cfg_data), .sf_cfg_base(q_sf_cfg_base));')
    return w


def ovl(w):
    o = OVL.master('\n' + w + '\n', 'qkd_d2d_static_sf')
    o = sub(o, 'module qkd_d2d_static_sf_ovl #(', 'module qkd_d2d_static_ovl_sf #(')
    o = sub(o, 'qkd_d2d_static_core_sf #(.MUT(MUT),', 'qkd_d2d_static_core_sf #(.OVL(1), .MUT(MUT),')
    o = sub(o, 'wire sf_rx_start_pin = cal_start, sf_rx_seg_pin = cal_seg;',
            'wire sf_rx_start_pin = cal_start_rx, sf_rx_seg_pin = cal_seg_rx;')
    return o


def main():
    t = SRC.read_text()
    w = wrapper(t)
    hdr = ('`timescale 1ns/1ps\n// GENERATED by tools/qwen_split/d2d_safe_fo_masters.py from ot_qwen_d2d_dies.sv (do not edit): KV-D2D '
           '10-19 SAFE FAN-OUT KV link-end masters\n// qkd_d2d_static_sf / qkd_d2d_static_ovl_sf (core qkd_d2d_static_core_sf, '
           'end / STATUS in ot_qwen_d2d_safe_fo.sv).  Source list: ot_qwen_d2d_dies.sv,\n// ot_qwen_d2d_dies_ovl.sv, '
           'ot_qwen_d2d_safe_fo.sv, ot_qwen_d2d_dies_sfo.sv.\n')
    OUT.write_text(hdr + '\n\n'.join([core(t), w, ovl(w)]) + '\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
