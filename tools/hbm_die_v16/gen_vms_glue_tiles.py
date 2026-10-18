#!/usr/bin/env python3
"""OWNERS-HBM/VM-GLUE 2026-10-18 (HBM d4g plan (b)): hardened-tile tops of the VM hub glue.  Writes
  rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles.sv      the three tile masters
  rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles_flat.sv bench-only adapters (<tile>_flat: the glue's flat
                                                                 bk_* buses -> the tile's per-bank ports; wires only)
The glue logic is UNCHANGED (hfd_hgi_vms_static_glue.sv from gen_vms_hoist.py, hfd_hgi_vms_static_qb.sv from
HBM-B-RTL1); the tops only
  (1) merge clk_hub / clk_ring[1:0] / clk_replay into ONE tile clock clk (all four are the same stream clock on the
      same edge; in the slice they were separate ports because hub, ring stops and replay were separate hard tiles);
  (2) split the bank-side buses per bank (b<k>_xq/_xq2/_xq_done/_xq2_done/_eg/_pq/_pr/_status[/_flt]) so each bank's
      link sits on ONE face next to that bank (a port is placed on one face);
  (3) E quadrants: the slice id is a strap pin (sid lands only on flops), so ONE master serves SE (1) and NE (3).
Masters:  hfd_hgi_vms_glue_sw_t  hfd_hgi_vms_static_SW_glue  (NC 2, sid 0)          -> hb_vms_SW
          hfd_hgi_vms_glue_e_t   ot_vms_slice_static_glue NC 1 RG 5 WG 2 = {SE,NE}b_glue with the sid strap -> hb_vms_SE / hb_vms_NE
          hfd_hgi_vms_glue_nw_t  hfd_hgi_vms_static_NW_glue  (NC 0, sid 2, bk_flt)  -> hb_vms_NW
    gen_vms_glue_tiles.py [--check]
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'rtl/hbm_accel/generic/vm/static'
OUT, FLAT = D / 'hfd_hgi_vms_glue_tiles.sv', D / 'hfd_hgi_vms_glue_tiles_flat.sv'
# per-bank slices of the glue's flat bank buses (gen_vms_hoist.py: bank b at [b*W+:W])
BANK = [('xq', 'output', 276, 'bk_xq'), ('xq2', 'output', 276, 'bk_xq2'), ('xq_done', 'input', 1, 'bk_xq_done'),
        ('xq2_done', 'input', 1, 'bk_xq2_done'), ('eg', 'input', 276, 'bk_eg'), ('pq', 'output', 285, 'bk_pq'),
        ('pr', 'input', 266, 'bk_pr'), ('status', 'input', 18, 'bank_status')]
FLT = ('flt', 'input', 1, 'bk_flt')
M = dict(sw=dict(nc=2, glue='hfd_hgi_vms_static_SW_glue', sid=None, flt=False, q='SW'),
         e=dict(nc=1, glue=None, sid='strap', flt=False, q='SE/NE'),
         nw=dict(nc=0, glue='hfd_hgi_vms_static_NW_glue', sid=None, flt=True, q='NW'))
RING = [('cw_in', 'input', 2224), ('ccw_in', 'input', 2224), ('cw_out', 'output', 2224), ('ccw_out', 'output', 2224),
        ('ring_tx_enable', 'input', 2), ('ring_tx_source', 'input', 6), ('replay_enable', 'input', 1), ('replay_source', 'input', 1)]
OUTS = [('hub_status', 3), ('mirror_busy', 2), ('vmstat', 19), ('ring_fault', 3)]


def w(n):
    return f'[{n - 1}:0] ' if n > 1 else ''


def ports(k, c):
    nc = c['nc']; cw = max(1, (nc).bit_length()) if nc else 1   # CW = clog2(NC+1)
    p = [('clk', 'input', 1), ('rst_n', 'input', 1)]
    if c['sid']:
        p.append(('sid', 'input', 2))
    if nc:
        p += [('cq', 'input', nc * 338), ('cr', 'output', nc * 274)]
    p += [('client_seq', 'input', (nc + 1) * 2), ('response_enable', 'input', nc + 1), ('response_seq', 'input', (nc + 1) * 2),
          ('bank_enable', 'input', 8), ('bank_client', 'input', 8 * cw), ('hub_ring_enable', 'input', 2),
          ('hub_ring_client', 'input', 2 * cw)]
    p += RING
    for b in range(8):
        p += [(f'b{b}_{n}', d, wd) for n, d, wd, _ in BANK + ([FLT] if c['flt'] else [])]
    p += [(n, 'output', wd) for n, wd in OUTS]
    return p


def flat_ports(k, c):
    p = [x for x in ports(k, c) if not x[0].startswith('b') or x[0] in ('bank_enable', 'bank_client')]
    p = [x for x in p if x[0] != 'clk']
    p = [('clk_hub', 'input', 1), ('clk_ring', 'input', 2), ('clk_replay', 'input', 1)] + p
    for n, d, wd, f in BANK + ([FLT] if c['flt'] else []):
        p.append((f, d, 8 * wd))
    return p


def decl(p):
    return ',\n'.join(f'    {d} wire {w(n)}{nm}' for nm, d, n in p)


def tile(k, c):
    p = ports(k, c)
    L = [f'module hfd_hgi_vms_glue_{k}_t (', decl(p), ');']
    for n, d, wd, f in BANK + ([FLT] if c['flt'] else []):
        L.append(f'    wire [{8 * wd - 1}:0] {f};')
        if d == 'input':
            L.append(f'    assign {f} = {{' + ', '.join(f'b{b}_{n}' for b in reversed(range(8))) + '};')
        else:
            L += [f'    assign b{b}_{n} = {f}[{b * wd + wd - 1}:{b * wd}];' if wd > 1 else f'    assign b{b}_{n} = {f}[{b}];' for b in range(8)]
    conn = ['.clk_hub(clk)', '.clk_ring({clk, clk})', '.clk_replay(clk)', '.rst_n(rst_n)']
    conn += [f'.{nm}({nm})' for nm, d, n in p if nm not in ('clk', 'rst_n', 'sid') and not (nm[0] == 'b' and nm[1].isdigit())]
    conn += [f'.{f}({f})' for _, _, _, f in BANK + ([FLT] if c['flt'] else [])]
    if c['glue']:
        L.append(f'    {c["glue"]} u_glue (\n        ' + ',\n        '.join(conn) + ');')
    else:
        L.append('    // = hfd_hgi_vms_static_SEb_glue / _NEb_glue (hfd_hgi_vms_static_qb.sv) with sid from the strap pin')
        L.append('    ot_vms_slice_static_glue #(.NC(1),.RG(5),.WG(2),.NATIVE_SHAPE(1),.BANK_PIN_IN(1)) u_slice (\n        .sid(sid),\n        '
                 + ',\n        '.join(conn) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


def flat(k, c):
    p = flat_ports(k, c)
    L = [f'module hfd_hgi_vms_glue_{k}_t_flat (', decl(p), ');']
    conn = ['.clk(clk_hub)']
    for nm, d, n in ports(k, c):
        if nm == 'clk':
            continue
        if nm[0] == 'b' and nm[1].isdigit():
            b = int(nm[1]); base = nm[3:]
            f, wd = next((f, wd) for n_, _, wd, f in BANK + [FLT] if n_ == base)
            conn.append(f'.{nm}({f}[{b * wd + wd - 1}:{b * wd}])' if wd > 1 else f'.{nm}({f}[{b}])')
        else:
            conn.append(f'.{nm}({nm})')
    L.append(f'    hfd_hgi_vms_glue_{k}_t u_tile (\n        ' + ',\n        '.join(conn) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


HDR = ('`timescale 1ns/1ps\n`default_nettype none\n// GENERATED by tools/hbm_die_v16/gen_vms_glue_tiles.py (do not edit): ')


def main():
    doc = '\n'.join('// ' + x for x in __doc__.strip().split('\n')[:-1])
    rtl = HDR + 'VM hub-glue tile masters.\n' + doc + '\n' + ''.join(tile(k, c) for k, c in M.items()) + '`default_nettype wire\n'
    fl = (HDR + 'BENCH-ONLY adapters <tile>_flat (wires): the glue port list (4 clocks, flat bk_* buses) around each tile '
          'master, so the hoist / qb compositions instantiate the tile in place of the glue.\n'
          + ''.join(flat(k, c) for k, c in M.items()) + '`default_nettype wire\n')
    if '--check' in sys.argv:
        ok = OUT.read_text() == rtl and FLAT.read_text() == fl
        print('VMS_GLUE_TILES_GEN', 'CHECK_PASS' if ok else 'CHECK_FAIL'); sys.exit(0 if ok else 1)
    OUT.write_text(rtl); FLAT.write_text(fl); print('VMS_GLUE_TILES_GEN WROTE', OUT.relative_to(ROOT), FLAT.relative_to(ROOT))


if __name__ == '__main__':
    main()
