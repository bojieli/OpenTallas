#!/usr/bin/env python3
"""OWNERS-HBM/VM-GLUE 2026-10-18, physical rework HBM-KITS-C/VMGLUE 10-18 (g2): hardened-tile tops of the VM hub glue.
Writes
  rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles.sv      the three tile masters
  rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles_ref.sv  BENCH-ONLY contract references <tile>_ref (flat glue
                                                                 ports): the UNCHANGED historical glue
                                                                 ot_vms_slice_static_glue (BANK_PIN_IN 3) behind the
                                                                 tile's latency contract
Tile top = hfd_vms_glue_core_lt (hfd_hgi_vms_glue_lt.sv: the glue wiring with reset-light ring stops / replay and the
parallel hub response demultiplex) plus
  (1) ONE tile clock clk (clk_hub / clk_ring[1:0] / clk_replay are the same stream clock on the same edge);
  (2) ONE reset port rst_n -> ot_rst_relay, 4 regional copies (hub | CW stop | CCW stop | replay + status): release
      +3 edges after the port (SYNC 2 + TREE 1), assertion asynchronous;
  (3) per-bank ports b<k>_* (a port sits on ONE face, next to its bank) and per-LANE ring ports
      <cw_in|cw_out|ccw_in|ccw_out>_l<k> (flit bits [k*276 +: 276], the bank-k lane) + _h (header bits [2223:2208]), so
      the ring face is laid out in lane bands beside the bank faces (vms_glue_kit_specs.py);
  (4) ONE register stage at every bank-side port (inputs eg / pr / xq_done / xq2_done / status [/ flt] land on a
      plain flop at the pin; outputs xq / xq2 / pq leave from a relay flop at the pin): the tile spans 648 x 1555 um,
      so a bank face to the ring face or to the hub is two reach stages, never one.  The ring commit check moves with
      it: COMMIT_DELAY 5 + 1 (bank pin) + 2 (tile xq relay + xq_done landing) = 8 (the historical BANK_PIN_IN knob).
  (5) E quadrants: the slice id is a strap pin, ONE master serves SE (1, R0) and NE (3, MX); E = NC 0 glue
      (hfd_hgi_vms_static_{SE,NE}_glue, the d4g binding since l4_idx_quad).
COMPILER CONTRACT (vs the historical glue at the same ports): every bank-side input is consumed 1 edge later and every
bank-side output appears 1 edge later (bank round trip pq -> pr +2, eject xq -> xq_done check +2 = COMMIT_DELAY 8, the
WACK / commit fault edge +2 after the eject, mirror egress eg -> ring tx slot +1, bank_status -> vmstat +1); ring,
client, control ports unchanged; reset release +3 edges.  <tile>_ref states exactly that (tools/hbm_die_v16/
vms_glue_tile_equiv.py runs tile vs ref in lockstep).
Tile parameter MUT (bench only, default 0): 1 ring-stop flit mutant, 3 eg not landed (contract break).
    gen_vms_glue_tiles.py [--check]
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'rtl/hbm_accel/generic/vm/static'
OUT, REF = D / 'hfd_hgi_vms_glue_tiles.sv', D / 'hfd_hgi_vms_glue_tiles_ref.sv'
LANE = 276
# per-bank slices of the glue's flat bank buses (gen_vms_hoist.py: bank b at [b*W+:W]); name, dir, width, flat bus
BANK = [('xq', 'output', 276, 'bk_xq'), ('xq2', 'output', 276, 'bk_xq2'), ('xq_done', 'input', 1, 'bk_xq_done'),
        ('xq2_done', 'input', 1, 'bk_xq2_done'), ('eg', 'input', 276, 'bk_eg'), ('pq', 'output', 285, 'bk_pq'),
        ('pr', 'input', 266, 'bk_pr'), ('status', 'input', 18, 'bank_status')]
FLT = ('flt', 'input', 1, 'bk_flt')
M = dict(sw=dict(nc=2, rg=5, wg=2, sid="2'd0", flt=False, q='SW'),
         e=dict(nc=0, rg=4, wg=2, sid='strap', flt=False, q='SE/NE'),
         nw=dict(nc=0, rg=5, wg=3, sid="2'd2", flt=True, q='NW'))
RINGB = [('cw_in', 'input'), ('cw_out', 'output'), ('ccw_in', 'input'), ('ccw_out', 'output')]
RINGC = [('ring_tx_enable', 'input', 2), ('ring_tx_source', 'input', 6), ('replay_enable', 'input', 1),
         ('replay_source', 'input', 1)]
OUTS = [('hub_status', 3), ('mirror_busy', 2), ('vmstat', 19), ('ring_fault', 3)]
COMMIT_DELAY = 8


def w(n):
    return f'[{n - 1}:0] ' if n > 1 else ''


def cw_of(nc):
    return max(1, (nc).bit_length()) if nc else 1   # CW = clog2(NC+1)


def bankp(c):
    return BANK + ([FLT] if c['flt'] else [])


def common(c):
    nc = c['nc']; cw = cw_of(nc)
    p = []
    if nc:
        p += [('cq', 'input', nc * 338), ('cr', 'output', nc * 274)]
    p += [('client_seq', 'input', (nc + 1) * 2), ('response_enable', 'input', nc + 1), ('response_seq', 'input', (nc + 1) * 2),
          ('bank_enable', 'input', 8), ('bank_client', 'input', 8 * cw), ('hub_ring_enable', 'input', 2),
          ('hub_ring_client', 'input', 2 * cw)]
    return p


def ports(k, c):
    p = [('clk', 'input', 1), ('rst_n', 'input', 1)]
    if c['sid'] == 'strap':
        p.append(('sid', 'input', 2))
    p += common(c)
    for n, d in RINGB:
        p += [(f'{n}_l{b}', d, LANE) for b in range(8)] + [(f'{n}_h', d, 16)]
    p += RINGC
    for b in range(8):
        p += [(f'b{b}_{n}', d, wd) for n, d, wd, _ in bankp(c)]
    p += [(n, 'output', wd) for n, wd in OUTS]
    return p


def ref_ports(k, c):
    """the historical glue's flat port list (one clk)"""
    p = [('clk', 'input', 1), ('rst_n', 'input', 1)]
    if c['sid'] == 'strap':
        p.append(('sid', 'input', 2))
    p += common(c)
    p += [(n, d, 2224) for n, d in RINGB] + RINGC
    p += [(f, d, 8 * wd) for _, d, wd, f in bankp(c)]
    p += [(n, 'output', wd) for n, wd in OUTS]
    return p


def decl(p):
    return ',\n'.join(f'    {d} wire {w(n)}{nm}' for nm, d, n in p)


def cat(names):
    return '{' + ', '.join(names) + '}'


def tile(k, c):
    p = ports(k, c); nc = c['nc']
    L = [f'module hfd_hgi_vms_glue_{k}_t #(parameter integer MUT=0) (', decl(p), ');']
    L.append('    // regional reset: the port drives only the relay (2 sync + 4 region copies); release +3 edges')
    L.append('    wire [3:0] rr;')
    L.append('    ot_rst_relay #(.REGIONS(4),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));')
    L.append('    // ring buses: lane k = flit bits [k*276 +: 276], header = [2223:2208]')
    for n, d in RINGB:
        L.append(f'    wire [2223:0] {n};')
        if d == 'input':
            L.append(f'    assign {n} = ' + cat([f'{n}_h'] + [f'{n}_l{b}' for b in reversed(range(8))]) + ';')
        else:
            L += [f'    assign {n}_l{b} = {n}[{b * LANE + LANE - 1}:{b * LANE}];' for b in range(8)]
            L.append(f'    assign {n}_h = {n}[2223:2208];')
    L.append('    // bank-side ports: one plain register stage at the pin (inputs land, outputs relay)')
    for n, d, wd, f in bankp(c):
        L.append(f'    wire [{8 * wd - 1}:0] {f}_p, {f}_c;')
        L.append(f'    reg [{8 * wd - 1}:0] {f}_r;')
        L.append(f'    always @(posedge clk) {f}_r <= {f}_p;')
        if d == 'input':
            L.append(f'    assign {f}_p = ' + cat([f'b{b}_{n}' for b in reversed(range(8))]) + ';')
            byp = " (MUT == 3) ? bk_eg_p :" if f == 'bk_eg' else ''
            L.append(f'    assign {f}_c ={byp} {f}_r;')
        else:
            L.append(f'    assign {f}_p = {f}_c;')
            L += [f'    assign b{b}_{n} = {f}_r[{b * wd + wd - 1}:{b * wd}];' if wd > 1 else f'    assign b{b}_{n} = {f}_r[{b}];'
                  for b in range(8)]
    st = 'bank_status_c'
    if c['flt']:
        L.append('    // NW: the wq2-merge leaves (vmm_NWb) sticky flt -> bank status bit 17 (as hfd_hgi_vms_static_NW_glue)')
        L.append('    wire [143:0] bank_status_m;')
        L += [f'    assign bank_status_m[{b * 18 + 17}:{b * 18}] = {{bank_status_c[{b * 18 + 17}] | bk_flt_c[{b}], '
              f'bank_status_c[{b * 18 + 16}:{b * 18}]}};' for b in range(8)]
        st = 'bank_status_m'
    sid = 'sid' if c['sid'] == 'strap' else c['sid']
    conn = ['.clk(clk)', '.rst_n(rr)', f'.sid({sid})']
    conn += [f'.{nm}({nm})' for nm, _, _ in common(c)]
    if not nc:
        conn += ['.cq(338\'d0)', '.cr()']
    conn += [f'.{n}({n})' for n, _ in RINGB] + [f'.{n}({n})' for n, _, _ in RINGC]
    conn += [f'.bank_status({st})', '.bk_xq(bk_xq_c)', '.bk_xq2(bk_xq2_c)', '.bk_xq_done(bk_xq_done_c)',
             '.bk_xq2_done(bk_xq2_done_c)', '.bk_eg(bk_eg_c)', '.bk_pq(bk_pq_c)', '.bk_pr(bk_pr_c)']
    conn += [f'.{n}({n})' for n, _ in OUTS]
    L.append(f'    hfd_vms_glue_core_lt #(.NC({nc}),.COMMIT_DELAY({COMMIT_DELAY}),.RMUT((MUT == 1) ? 1 : 0)) u_core (\n        '
             + ',\n        '.join(conn) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


def ref(k, c):
    p = ref_ports(k, c); nc = c['nc']
    L = [f'module hfd_hgi_vms_glue_{k}_t_ref (', decl(p), ');']
    L.append('    wire rr;  // the same release: 2 sync + 1 relay stage after the port')
    L.append('    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));')
    L.append('    // contract: every bank-side input consumed 1 edge later, every bank-side output 1 edge later')
    for n, d, wd, f in bankp(c):
        L.append(f'    reg [{8 * wd - 1}:0] {f}_d; wire [{8 * wd - 1}:0] {f}_g;')
        if d == 'input':
            L.append(f'    always @(posedge clk) {f}_d <= {f}; assign {f}_g = {f}_d;')
        else:
            L.append(f'    always @(posedge clk) {f}_d <= {f}_g; assign {f} = {f}_d;')
    st = 'bank_status_g'
    if c['flt']:
        L.append('    wire [143:0] bank_status_m;')
        L.append('    genvar fb;')
        L.append('    generate for(fb=0;fb<8;fb=fb+1)begin:g_flt')
        L.append('        assign bank_status_m[fb*18+:18]={bank_status_g[fb*18+17]|bk_flt_g[fb],bank_status_g[fb*18+:17]};')
        L.append('    end endgenerate')
        st = 'bank_status_m'
    sid = 'sid' if c['sid'] == 'strap' else c['sid']
    conn = ['.clk_hub(clk)', '.clk_ring({clk, clk})', '.clk_replay(clk)', '.rst_n(rr)', f'.sid({sid})']
    conn += [f'.{nm}({nm})' for nm, _, _ in common(c)]
    if not nc:
        conn += [".cq(338'd0)", '.cr()']
    conn += [f'.{n}({n})' for n, _ in RINGB] + [f'.{n}({n})' for n, _, _ in RINGC]
    conn += [f'.bank_status({st})'] + [f'.{f}({f}_g)' for _, _, _, f in BANK if f != 'bank_status']
    conn += [f'.{n}({n})' for n, _ in OUTS]
    L.append(f'    ot_vms_slice_static_glue #(.NC({nc}),.RG({c["rg"]}),.WG({c["wg"]}),.NATIVE_SHAPE(1),.BANK_PIN_IN(3)) u_glue (\n        '
             + ',\n        '.join(conn) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


HDR = ('`timescale 1ns/1ps\n`default_nettype none\n// GENERATED by tools/hbm_die_v16/gen_vms_glue_tiles.py (do not edit): ')


def main():
    doc = '\n'.join('// ' + x for x in __doc__.strip().split('\n')[:-1])
    rtl = HDR + 'VM hub-glue tile masters.\n' + doc + '\n' + ''.join(tile(k, c) for k, c in M.items()) + '`default_nettype wire\n'
    rf = (HDR + 'BENCH-ONLY contract references <tile>_ref: the historical glue ot_vms_slice_static_glue (unchanged '
          'hub / ring stops / replay / status, BANK_PIN_IN 3 = COMMIT_DELAY 8) behind one delay stage on every bank-side '
          'port and the tile reset relay timing, at the historical flat ports.\n'
          + ''.join(ref(k, c) for k, c in M.items()) + '`default_nettype wire\n')
    if '--check' in sys.argv:
        ok = OUT.read_text() == rtl and REF.read_text() == rf
        print('VMS_GLUE_TILES_GEN', 'CHECK_PASS' if ok else 'CHECK_FAIL'); sys.exit(0 if ok else 1)
    OUT.write_text(rtl); REF.write_text(rf); print('VMS_GLUE_TILES_GEN WROTE', OUT.relative_to(ROOT), REF.relative_to(ROOT))


if __name__ == '__main__':
    main()
