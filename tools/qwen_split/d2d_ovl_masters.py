#!/usr/bin/env python3
"""MU-D2D-OVL 10-19: emit the OVERLAP die masters qfd_d2d_static_ovl / qkd_d2d_static_ovl
(rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_ovl.sv) from the as-built pin-registered masters in
ot_qwen_d2d_dies.sv: same ports + cal_start_rx, cal_seg_rx, cal_user_tx[1:0], cal_user_rx[1:0] (inputs) and tx_user[1:0],
rx_user[1:0] (outputs), each with one pin flop when PR = 1 (the same +1 as cal_start / tx_slot / rx_slot, so the user
tags stay aligned with the slots they tag), and the core built with OVL = 1.  The as-built qfd_d2d_static /
qkd_d2d_static keep their ports and logic (their cores have OVL = 0 and the new inputs tied 0): every closed view
still binds.  Re-run after any edit of the as-built masters:  python3 tools/qwen_split/d2d_ovl_masters.py
"""
import re
from pathlib import Path

D = Path(__file__).resolve().parents[2] / 'rtl/qwen_sys/d2d_static_20261015'
SRC, OUT = D / 'ot_qwen_d2d_dies.sv', D / 'ot_qwen_d2d_dies_ovl.sv'
NEW = [('input', '', 'cal_start_rx'), ('input', '', 'cal_seg_rx'), ('input', '[1:0] ', 'cal_user_tx'),
       ('input', '[1:0] ', 'cal_user_rx'), ('output', '[1:0] ', 'tx_user'), ('output', '[1:0] ', 'rx_user')]
TIE = ".cal_start_rx(1'b0), .cal_seg_rx(1'b0), .cal_user_tx(2'd0), .cal_user_rx(2'd0), .tx_user(), .rx_user()"


def master(t, mod):
    m = re.search(r'\nmodule ' + mod + r' #\(.*?\nendmodule', t, re.S)
    body = m.group(0).strip('\n')
    body = body.replace(f'module {mod} #(', f'module {mod}_ovl #(', 1)
    body = body.replace('    input  wire cal_seg,\n', '    input  wire cal_seg,\n' + ''.join(
        f'    {d}{" " if d == "input" else ""} wire {w}{n},\n' for d, w, n in NEW), 1)
    regs = []
    for d, w, n in NEW:
        regs += [f'    wire {w}c_{n};', f'    reg {w}q_{n};']
        if d == 'input':
            regs += [f'    always @(posedge ck) q_{n} <= {n};', f'    assign c_{n} = PR ? q_{n} : {n};']
        else:
            regs += [f'    always @(posedge ck) q_{n} <= c_{n};', f'    assign {n} = PR ? q_{n} : c_{n};']
    assert body.count(TIE) == 1, mod
    body = body.replace(TIE, ', '.join(f'.{n}(c_{n})' for _, _, n in NEW))
    body = body.replace('_core #(.MUT(MUT)', '_core #(.OVL(1), .MUT(MUT)', 1)
    i = body.index('    wire c_cal_start;')
    return body[:i] + '\n'.join(regs) + '\n' + body[i:]


# QW-D2D SAFE5 10-19: the structurally safe compute master qfd_d2d_static_ovl_sf (same ports as qfd_d2d_static_ovl) =
# the OVL master with KEPT pin-flop copies for the high-fanout inputs and the SAFE5 core qfd_d2d_static_core_s
# (rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_safe5.sv).  Emitted to its own file so no existing source list changes.
OUT_SF = D / 'ot_qwen_d2d_dies_ovl_sf.sv'
# input -> {copy bus name: (width of the bus, source bit expression for copy i)}
SF_REP = {
    'cfg_data': {'cfg_data_t': (32, 'cfg_data[{i}]'), 'cfg_data_r': (32, 'cfg_data[{i}]'),
                 'cfg_seg_t': (5, 'cfg_data[{i}]'), 'cfg_seg_r': (5, 'cfg_data[{i}]')},
    'cal_start': {'cal_start_k': (5, 'cal_start')}, 'cal_seg': {'cal_seg_k': (3, 'cal_seg')},
    'cal_start_rx': {'cal_start_rx_k': (5, 'cal_start_rx')}, 'cal_seg_rx': {'cal_seg_rx_k': (3, 'cal_seg_rx')},
    'result_v': {'result_v_k': (10, 'result_v')},
}


def master_sf(ovl):
    body = ovl.replace('module qfd_d2d_static_ovl #(parameter integer MUT = 0, parameter integer PR = 1, parameter [31:0] TXDP = 32\'d0) (',
                       'module qfd_d2d_static_ovl_sf #(parameter integer MUT = 0, parameter integer PR = 1, parameter [31:0] TXDP = 32\'d0,\n'
                       '    parameter integer SFMUT = 0) (', 1)
    assert 'qfd_d2d_static_ovl_sf' in body
    for n, buses in SF_REP.items():
        w = re.search(r'    wire (\[\d+:0\] )?c_' + n + r';\n    reg (\[\d+:0\] )?q_' + n + r';\n    always @\(posedge ck\) q_' + n
                      + r' <= ' + n + r';\n    assign c_' + n + r' = PR \? q_' + n + r' : ' + n + r';\n', body)
        assert w, n
        rep = []
        for bus, (bw, src) in buses.items():
            rep.append(f'    wire [{bw - 1}:0] k_{bus};')
            rep.append(f'    for (gi = 0; gi < {bw}; gi = gi + 1) begin : g_{bus}')
            rep.append(f'        ot_d2d_kff u_k (.ck(ck), .d({src.format(i="gi")}), .q(k_{bus}[gi]));')
            rep.append('    end')
        body = body.replace(w.group(0), '\n'.join(rep) + '\n', 1)
    i = body.index('    wire c_cfg_tx_we;')
    body = body[:i] + '    genvar gi;   // SAFE5: KEPT pin-flop copies (ot_d2d_kff, route.synth_keep_modules), one per <= ~32 loads\n' + body[i:]
    core = re.search(r'    qfd_d2d_static_core #\(\.OVL\(1\), \.MUT\(MUT\), \.TXDP\((.*?)\)\) u_core \(', body)
    assert core
    body = body.replace(core.group(0), '    qfd_d2d_static_core_s #(.TXDP(%s), .SFMUT(SFMUT)) u_core (' % core.group(1), 1)
    for a, b in (('.cfg_data(c_cfg_data)', '.cfg_data_t(k_cfg_data_t), .cfg_data_r(k_cfg_data_r), .cfg_seg_t(k_cfg_seg_t), .cfg_seg_r(k_cfg_seg_r)'),
                 ('.cal_start(c_cal_start)', '.cal_start_k(k_cal_start_k)'), ('.cal_seg(c_cal_seg)', '.cal_seg_k(k_cal_seg_k)'),
                 ('.cal_start_rx(c_cal_start_rx)', '.cal_start_rx_k(k_cal_start_rx_k)'),
                 ('.cal_seg_rx(c_cal_seg_rx)', '.cal_seg_rx_k(k_cal_seg_rx_k)'), ('.result_v(c_result_v)', '.result_v_k(k_result_v_k)')):
        assert body.count(a) == 1, a
        body = body.replace(a, b)
    # SF requires the pin-registered master (the copies ARE the pin flops)
    body = body.replace('    genvar gi;', '    generate if (PR == 0) begin : g_sf_needs_pr\n        D2D_SF_REQUIRES_PR_1 u_sf_needs_pr ();\n'
                        '    end endgenerate\n    genvar gi;', 1)
    return body


def main():
    t = SRC.read_text()
    hdr = ('`timescale 1ns/1ps\n// GENERATED by tools/qwen_split/d2d_ovl_masters.py from ot_qwen_d2d_dies.sv (do not edit): MU-D2D-OVL '
           '10-19 overlap die masters\n// (cores with OVL = 1: request and response segments start separately, per-user tags).  '
           'Source list: ot_qwen_d2d_dies.sv first.\n')
    OUT.write_text(hdr + '\n\n'.join(master(t, m) for m in ('qfd_d2d_static', 'qkd_d2d_static')) + '\n')
    print('wrote', OUT)
    q = master(t, 'qfd_d2d_static')
    hdr_sf = ('`timescale 1ns/1ps\n// GENERATED by tools/qwen_split/d2d_ovl_masters.py (do not edit): QW-D2D SAFE5 10-19 structurally safe compute\n'
              '// D2D master qfd_d2d_static_ovl_sf = qfd_d2d_static_ovl ports + KEPT pin-flop copies + qfd_d2d_static_core_s.\n'
              '// Source list: ot_qwen_d2d_dies.sv, ot_qwen_d2d_safe5.sv, this file.\n')
    OUT_SF.write_text(hdr_sf + master_sf(q) + '\n')
    print('wrote', OUT_SF)


if __name__ == '__main__':
    main()
