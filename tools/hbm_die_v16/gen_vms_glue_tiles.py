#!/usr/bin/env python3
"""OWNERS-HBM/VM-GLUE 2026-10-18, rev 2 (VM-GLUE2): hardened-tile tops of the HBM d4g VM hub glue.  Writes
  rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles.sv      the three tile masters + ot_vms_slice_static_glue_vr
  rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles_flat.sv bench-only: <tile>_flat adapters (the glue's flat port
                                                                 list -> the tile) and <tile>_ref / <tile>_ref_flat (the
                                                                 same tile body around the ORIGINAL slice glue)
Masters (GEN2 binding, d4g l4/l5: every hub has NC 0 except SW):
  hfd_hgi_vms_glue_sw_t  = hfd_hgi_vms_static_SW_glue  (NC 2, sid 0)                 -> hb_vms_SW
  hfd_hgi_vms_glue_e_t   = hfd_hgi_vms_static_SE_glue / _NE_glue (NC 0, RG 4, WG 2) with the sid STRAP pin -> hb_vms_SE (1), hb_vms_NE (3)
  hfd_hgi_vms_glue_nw_t  = hfd_hgi_vms_static_NW_glue  (NC 0, sid 2, + bk_flt into bank status bit 17) -> hb_vms_NW
  NW cannot share the E master: its bk_flt inputs (the wq2-merge sticky flt) do not exist on SE / NE (a shared master
  would tie them = stub).  RG / WG are dead parameters of the slice (RB / WB unused), so SE / NE / NW differ only in sid + flt.
Rev 2 (measured: rev-1 NW --cts gate, one clk root 26k sinks, TT insertion 1503 / spread 421 ps, setup WNS -1744 ps:
hub status / response gather and ring-stop xq / reset recovery crossing 1-2.4 ns of wire in ONE cycle over the
777.6 x 1555.2 pin-bound outline -- the glue is single-cycle logic sitting between 20k pins on four faces):
  (1) REGISTERED FACES: every port except clk / rst_n goes through PIPE = 1 + RELAYS flops between the pin and the
      slice (input: pin flop at the pin, then RELAYS relay flops; output: RELAYS relay flops, then the pin flop).  With
      RELAYS 2 every stage spans <= ~1/3 of the worst pin-to-core distance (~1,230 um) = <= ~410 um (the 405 um plan).
      LATENCY (record for the compiler / calendar owner): every hub input +PIPE cycles, every hub output +PIPE cycles;
      the ring-stop commit check moves with the bank round trip: COMMIT_DELAY = 5 + BANK_PIN_IN, BANK_PIN_IN 1 -> 1 + 2*PIPE.
  (2) RESET: rst_n -> ot_rst_relay (sync 2 + tree 1 = release +3 edges, transaction-level: no client counts cycles from
      reset); the ring stops are ot_vms_rstop_static_vr (valid-only reset, logic otherwise verbatim), so the reset net
      drops from 19k loads to ~2.3k (hub / rcl / status valids + the replay client's registers).
  (3) one clock (clk_hub / clk_ring / clk_replay are one stream clock); the kit uses the OT_SPINE clock spine.
    gen_vms_glue_tiles.py [--check]
"""
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'rtl/hbm_accel/generic/vm/static'
OUT, FLAT = D / 'hfd_hgi_vms_glue_tiles.sv', D / 'hfd_hgi_vms_glue_tiles_flat.sv'
GLUE = D / 'hfd_hgi_vms_static_glue.sv'
RELAYS = 2
PIPE = 1 + RELAYS
BPI = 1 + 2 * PIPE            # slice BANK_PIN_IN: COMMIT_DELAY = 5 + BPI
# per-bank slices of the glue's flat bank buses (gen_vms_hoist.py: bank b at [b*W+:W])
BANK = [('xq', 'output', 276, 'bk_xq'), ('xq2', 'output', 276, 'bk_xq2'), ('xq_done', 'input', 1, 'bk_xq_done'),
        ('xq2_done', 'input', 1, 'bk_xq2_done'), ('eg', 'input', 276, 'bk_eg'), ('pq', 'output', 285, 'bk_pq'),
        ('pr', 'input', 266, 'bk_pr'), ('status', 'input', 18, 'bank_status')]
FLT = ('flt', 'input', 1, 'bk_flt')
RING = [('cw_in', 'input', 2224), ('ccw_in', 'input', 2224), ('cw_out', 'output', 2224), ('ccw_out', 'output', 2224),
        ('ring_tx_enable', 'input', 2), ('ring_tx_source', 'input', 6), ('replay_enable', 'input', 1), ('replay_source', 'input', 1)]
OUTS = [('hub_status', 3), ('mirror_busy', 2), ('vmstat', 19), ('ring_fault', 3)]


def glue_params(q):
    """(NC, RG, WG, sid) of hfd_hgi_vms_static_<q>_glue, read from the glue source (so the tile cannot drift from it)."""
    t = GLUE.read_text()
    body = re.search(rf'module hfd_hgi_vms_static_{q}_glue\s*\((.*?)endmodule', t, re.S).group(1)
    m = re.search(r'ot_vms_slice_static_glue #\(\.NC\((\d+)\),\.RG\((\d+)\),\.WG\((\d+)\),\.NATIVE_SHAPE\(1\),\.BANK_PIN_IN\(1\)\)', body)
    s = re.search(r"\.sid\(2'd(\d)\)", body)
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(s.group(1)), 'bk_flt' in body


def masters():
    sw, se, ne, nw = (glue_params(q) for q in ('SW', 'SE', 'NE', 'NW'))
    assert se[:3] == ne[:3] and not se[4] and not ne[4] and (se[3], ne[3]) == (1, 3), (se, ne)
    assert sw[0] == 2 and nw[0] == 0 and nw[4] and not sw[4], (sw, nw)
    return dict(sw=dict(nc=sw[0], rg=sw[1], wg=sw[2], sid=sw[3], flt=False),
                e=dict(nc=se[0], rg=se[1], wg=se[2], sid='strap', flt=False),
                nw=dict(nc=nw[0], rg=nw[1], wg=nw[2], sid=nw[3], flt=True))


def w(n):
    return f'[{n - 1}:0] ' if n > 1 else ''


def ports(c):
    nc = c['nc']; cw = max(1, nc.bit_length()) if nc else 1   # CW = clog2(NC+1)
    p = [('clk', 'input', 1), ('rst_n', 'input', 1)]
    if c['sid'] == 'strap':
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


def flat_ports(c):
    p = [x for x in ports(c) if not (x[0][0] == 'b' and x[0][1].isdigit())]
    p = [x for x in p if x[0] != 'clk']
    p = [('clk_hub', 'input', 1), ('clk_ring', 'input', 2), ('clk_replay', 'input', 1)] + p
    for n, d, wd, f in BANK + ([FLT] if c['flt'] else []):
        p.append((f, d, 8 * wd))
    return p


def decl(p):
    return ',\n'.join(f'    {d} wire {w(n)}{nm}' for nm, d, n in p)


def slice_vr():
    """ot_vms_slice_static_glue verbatim, ring stops -> ot_vms_rstop_static_vr (valid-only reset)."""
    t = GLUE.read_text()
    m = re.search(r'module ot_vms_slice_static_glue #\(.*?endmodule\n', t, re.S).group(0)
    m2 = m.replace('module ot_vms_slice_static_glue #(', 'module ot_vms_slice_static_glue_vr #(', 1)
    assert m2.count('ot_vms_rstop_static #(') == 2
    return ('// = ot_vms_slice_static_glue (hfd_hgi_vms_static_glue.sv, gen_vms_hoist.py) verbatim except the two ring stops\n'
            '//   -> ot_vms_rstop_static_vr (valid-only reset).\n' + m2.replace('ot_vms_rstop_static #(', 'ot_vms_rstop_static_vr #('))


def tile(k, c, core, name):
    """Tile top: PIPE flops on every face port, reset relay, the slice core."""
    p = ports(c)
    L = [f'module {name} (', decl(p), ');']
    L.append(f'    // REGISTERED FACES (rev 2): {PIPE} flops between every pin and the slice (pin flop + {RELAYS} relays);'
             f' hub latency +{PIPE} in / +{PIPE} out, slice BANK_PIN_IN {BPI}.')
    L.append('    wire [0:0] rst_c;')
    L.append('    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst (.clk(clk),.rst_n_in(rst_n),.rst_n(rst_c));')
    inner = {}
    for nm, d, n in p:
        if nm in ('clk', 'rst_n'):
            continue
        st = [f'pp_{nm}_{i}' for i in range(PIPE)]   # input: st[0] at the pin ... output: st[-1] at the pin
        L.append(f'    reg {w(n)}' + ', '.join(st) + ';')
        if d == 'input':
            src = [nm] + st[:-1]
            inner[nm] = st[-1]
        else:
            L.append(f'    wire {w(n)}{nm}_c;')
            src = [f'{nm}_c'] + st[:-1]
            L.append(f'    assign {nm} = {st[-1]};')
            inner[nm] = f'{nm}_c'
        L.append('    always @(posedge clk) begin ' + ' '.join(f'{s} <= {x};' for s, x in zip(st, src)) + ' end')
    # flat bank buses between the face pipes and the slice
    for n, d, wd, f in BANK + ([FLT] if c['flt'] else []):
        L.append(f'    wire [{8 * wd - 1}:0] {f};')
        if d == 'input':
            L.append(f'    assign {f} = {{' + ', '.join(inner[f'b{b}_{n}'] for b in reversed(range(8))) + '};')
        else:
            L += [f'    assign {inner[f"b{b}_{n}"]} = {f}[{b * wd + wd - 1}:{b * wd}];' if wd > 1
                  else f'    assign {inner[f"b{b}_{n}"]} = {f}[{b}];' for b in range(8)]
    if c['flt']:   # = hfd_hgi_vms_static_NW_glue: the wq2-merge sticky flt joins bank status bit 17
        L.append('    wire [143:0] bank_status_m;')
        L += [f'    assign bank_status_m[{b * 18 + 17}:{b * 18}] = {{bank_status[{b * 18 + 17}] | bk_flt[{b}], bank_status[{b * 18 + 16}:{b * 18}]}};'
              for b in range(8)]
    sid = inner['sid'] if c['sid'] == 'strap' else f"2'd{c['sid']}"
    conn = ['.clk_hub(clk)', '.clk_ring({clk, clk})', '.clk_replay(clk)', '.rst_n(rst_c[0])', f'.sid({sid})']
    if c['nc']:
        conn += [f'.cq({inner["cq"]})', f'.cr({inner["cr"]})']
    else:
        L.append('    wire [273:0] vacant_cr; // NC=0: no local clients exist (as the glue).')
        conn += [".cq(338'd0)", '.cr(vacant_cr)']
    for nm, d, n in p:
        if nm in ('clk', 'rst_n', 'sid', 'cq', 'cr') or (nm[0] == 'b' and nm[1].isdigit()):
            continue
        conn.append(f'.{nm}({inner[nm]})')
    for _, _, _, f in BANK:
        conn.append(f'.{f}({f}_m)' if (f == 'bank_status' and c['flt']) else f'.{f}({f})')
    L.append(f'    {core} #(.NC({c["nc"]}),.RG({c["rg"]}),.WG({c["wg"]}),.NATIVE_SHAPE(1),.BANK_PIN_IN({BPI})) u_slice (\n        '
             + ',\n        '.join(conn) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


def flat(k, c, name):
    p = flat_ports(c)
    L = [f'module {name}_flat (', decl(p), ');']
    conn = ['.clk(clk_hub)']
    for nm, d, n in ports(c):
        if nm == 'clk':
            continue
        if nm[0] == 'b' and nm[1].isdigit():
            b = int(nm[1]); base = nm[3:]
            f, wd = next((f, wd) for n_, _, wd, f in BANK + [FLT] if n_ == base)
            conn.append(f'.{nm}({f}[{b * wd + wd - 1}:{b * wd}])' if wd > 1 else f'.{nm}({f}[{b}])')
        else:
            conn.append(f'.{nm}({nm})')
    L.append(f'    {name} u_tile (\n        ' + ',\n        '.join(conn) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


HDR = ('`timescale 1ns/1ps\n`default_nettype none\n// GENERATED by tools/hbm_die_v16/gen_vms_glue_tiles.py (do not edit): ')


def main():
    M = masters()
    doc = '\n'.join('// ' + x for x in __doc__.strip().split('\n')[:-1])
    rtl = (HDR + 'VM hub-glue tile masters.\n' + doc + '\n' + slice_vr()
           + ''.join(tile(k, c, 'ot_vms_slice_static_glue_vr', f'hfd_hgi_vms_glue_{k}_t') for k, c in M.items()) + '`default_nettype wire\n')
    fl = (HDR + 'BENCH-ONLY.  <tile>_flat: the glue port list (4 clocks, flat bk_* buses) around each tile master, so the '
          'hoist compositions instantiate the tile in place of the glue.  <tile>_ref: the SAME generated tile body around the '
          'ORIGINAL ot_vms_slice_static_glue (full-reset ring stops); <tile>_ref_flat its adapter: the bench reference.\n'
          + ''.join(flat(k, c, f'hfd_hgi_vms_glue_{k}_t') for k, c in M.items())
          + ''.join(tile(k, c, 'ot_vms_slice_static_glue', f'hfd_hgi_vms_glue_{k}_t_ref') + flat(k, c, f'hfd_hgi_vms_glue_{k}_t_ref')
                    for k, c in M.items()) + '`default_nettype wire\n')
    if '--check' in sys.argv:
        ok = OUT.read_text() == rtl and FLAT.read_text() == fl
        print('VMS_GLUE_TILES_GEN', 'CHECK_PASS' if ok else 'CHECK_FAIL'); sys.exit(0 if ok else 1)
    OUT.write_text(rtl); FLAT.write_text(fl); print('VMS_GLUE_TILES_GEN WROTE', OUT.relative_to(ROOT), FLAT.relative_to(ROOT), M)


if __name__ == '__main__':
    main()
