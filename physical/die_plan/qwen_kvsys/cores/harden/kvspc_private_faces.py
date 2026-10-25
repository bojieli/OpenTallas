#!/usr/bin/env python3
"""Selected KV PC faces: private forward launch (+1 outgoing hop), shared pi capture, ID-only straps.

Apply AFTER kvspc_face_ports.py. Unparameterized single-bit kept FF modules
retain each outgoing boundary register through synthesis. Internal taps still
consume the original first-stage capture, so local decode cycles are unchanged.
"""
import json
import re
from pathlib import Path

FFS = '''
(* keep_hierarchy *) module ot_kvpc_pin_dff(input wire ck, input wire d, output reg q);
 always @(posedge ck) q <= d;
endmodule
(* keep_hierarchy *) module ot_kvpc_pin_ar0(input wire ck, input wire rn, input wire d, output reg q);
 always @(posedge ck or negedge rn) if (!rn) q <= 1'b0; else q <= d;
endmodule
'''


def forward_launch(text):
    old = '    assign dout = {bt, c[F_BT-1:F_CV+1], cv, c[F_CV-1:F_SS+1], ss, c[F_SS-1:F_EV+2], ev1, ev0, c[F_EV-1:0]};'
    if text.count(old) != 1:
        raise ValueError('expected one complete 780-bit forward word')
    new = '''    // Private outgoing launch: input capture c remains local; only dout gains one edge.
    wire [779:0] port_fwd_d = {bt, c[F_BT-1:F_CV+1], cv, c[F_CV-1:F_SS+1], ss, c[F_SS-1:F_EV+2], ev1, ev0, c[F_EV-1:0]};
    for (genvar fp = 0; fp < 780; fp = fp + 1) begin : g_port_forward
        if (fp == 0 || fp == 1 || fp == 615 || fp == 616 || fp == 719 || fp == 754 || fp == 779) begin : g_control
            (* keep *) ot_kvpc_pin_ar0 u_q (.ck(ck), .rn(rs_q), .d(port_fwd_d[fp]), .q(dout[fp]));
        end else begin : g_data
            (* keep *) ot_kvpc_pin_dff u_q (.ck(ck), .d(port_fwd_d[fp]), .q(dout[fp]));
        end
    end'''
    return text.replace(old, new)


def pi_capture_merge(text):
    a = '    (* keep *) reg         rv_q,rawslot_q;'
    b = '    (* keep *) reg rv_q, col_v_q, col_we_q, col_sr_q;'
    if text.count(a) != 1 or text.count(b) != 1:
        raise ValueError('expected scheduler and port rv_q declarations')
    # Both rv_q have identical hclk/h_rn/pi[0] next state. Let opt_merge share
    # their input capture; the shared Q feeds internal consumers only.
    return text.replace(a, '    reg rv_q; (* keep *) reg rawslot_q;').replace(
        b, '    reg rv_q; (* keep *) reg col_v_q, col_we_q, col_sr_q;')


def id_straps(text):
    for old, new, width in [('pc__pc', 'strap_pc', 5), ('pc__cfg_stack', 'strap_stack', 2)]:
        decl = f'input wire [{width-1}:0] {old},'
        bind = f'.{old}({old}[{width-1}:0])'
        if text.count(decl) != 1 or text.count(bind) != 1:
            raise ValueError(f'ID declaration/binding changed: {old}')
        text = text.replace(decl, f'input wire [{width-1}:0] {new},').replace(bind, f'.{old}({new}[{width-1}:0])')
    return text


def apply_kit(rtl_dir, mod):
    d = Path(rtl_dir)
    p = d/'qkd_ctrl_pc_nc.sv'; p.write_text(pi_capture_merge(p.read_text()))
    if not mod.endswith('_h_head_p'):
        p = d/'qkd_kv_pc_chain_station_b.sv'; p.write_text(forward_launch(p.read_text()))
        (d/'ot_kvpc_pin_ff.sv').write_text('`timescale 1ns/1ps\n'+FFS)
    p = d/(mod+'.sv'); p.write_text(id_straps(p.read_text()))


def core_json_update(cj):
    for old, new, width in [('pc__pc', 'strap_pc', 5), ('pc__cfg_stack', 'strap_stack', 2)]:
        cj['port_decl'][new] = cj['port_decl'].pop(old)
        for b in range(width):
            cj['pin_class'].pop(f'{old}[{b}]')
            cj['pin_class'][f'{new}[{b}]'] = 'strap'
    cj['straps'] = [{'port':'strap_pc','width':5,'meaning':'physical pseudo-channel identity'},
                    {'port':'strap_stack','width':2,'meaning':'physical HBM stack identity'}]
    return cj


def plan_pins_update(pins):
    return [dict(p, name=re.sub(r'^pc__pc(?=\[)', 'strap_pc', re.sub(r'^pc__cfg_stack(?=\[)', 'strap_stack', p['name']))) for p in pins]


def pins_update(pins):
    return [dict(p,bus={'pc__pc':'strap_pc','pc__cfg_stack':'strap_stack'}.get(p['bus'],p['bus'])) for p in pins]


if __name__ == '__main__':
    import sys
    apply_kit(sys.argv[1],sys.argv[2])
