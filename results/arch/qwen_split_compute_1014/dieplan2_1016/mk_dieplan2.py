#!/usr/bin/env python3
"""Q-DIEPLAN2 (Q-COMPUTE-DIE helper, 2026-10-16): owner 5-column compute-die homes, second revision.

usage: mk_dieplan2.py BASE_HOMES OUT_HOMES [--dxw 410.4] [--dxe 0]

BASE = dieplan_0700/qcd_owner_a_t950-homes.json (W array | port_k strip | core | _f1 strip | E array, tile 457.92 x 950.4,
interim port option (a)). Only positions move; masters, instances and orientations are kept. Moves (each one removes a
fine-cut line > 0.60 of the base relay-skip GEN, cuts.py v3 / CLUSTER_PLAN M6):
  1. seq_su into the SU-W / VM-N corner (abuts both): seq->SU 5,862 b and seq->VM 3,115 b become face-to-face
     (base 1.155 / 0.938); control-geometry C (7ae6d63f3) faces E=SU, S=VM, W=control.
  2. xs_tap on the SU W face above seq_su (SU 2,137 b face-to-face), tt_ctlm on the SU W face above xs_tap,
     res_train_issue on the tt_ctlm W face.
  3. native59 into the SU-E / VM-N corner (abuts both): SU->native59 3,711 b and VM<->native59 2,023 b no longer cross
     the 3.24-mm VM (base 1.10 .. 0.99); same contact idea as 35b64a77a, abutted instead of 86 um off.
  4. clk_rx (no data nets) moves out of the native59 corner to the free band under the VM centre.
  5. the W port strip (port_k / lanes / res_ser stacks, up4 leaves, rstseq) moves --dxw um east, off the array edge: the
     band words converging on each port corner then meet in a free channel (M4-M9) instead of over the last tile column
     (M9 only for vertical wires; base 0.848).
  7. --cbuf-pack: cbuf_g|crom_g pairs abutted side by side (4 rows x 2) on the SU E face above native59.
  6. the KV stack (d2d_rom / ucie_kv / KV bumps, top edge) moves --kvdx west so native59 -> d2d leaves the cbuf/crom column.
The three option-(a) port<->_f1 pair lines (6,704 b each, one centroid line, floor 0.82 in a free channel) are an
interim-port EXCEPTION (Q-COMPUTE-DIE call 10-16, not a waiver); port remap b2 removes them. Room is kept for b2:
the pair windows stay block-free and both strips keep their outline.
"""
import argparse, json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('base'); ap.add_argument('out')
ap.add_argument('--dxw', type=float, default=410.4)
ap.add_argument('--dxe', type=float, default=0.0)
ap.add_argument('--clk', default='16302.24,3661.84')
ap.add_argument('--cbuf-pack', action='store_true', help='cbuf|crom pairs abutted side by side on the SU E face')
ap.add_argument('--dy1', type=float, default=0.0, help='band-1 stack (port/lanes/res_ser/_f1) y shift')
ap.add_argument('--kvdx', type=float, default=-360.0, help='KV stack (d2d_rom, ucie_kv, KV bumps) x shift')
a = ap.parse_args()
B = json.load(open(a.base)); H = {k: dict(v) for k, v in B['homes'].items()}
g = lambda v, q=0.216: round(round(v / q) * q, 3)
def mv(n, x, y):
    H[n]['x'] = g(x); H[n]['y'] = g(y)
su, vm = H['sp_vector_memory'] and H['sp_su64_sfu'], H['sp_vector_memory']
vm_top = vm['y'] + vm['h']
assert abs(su['y'] - vm_top) < 0.1, 'SU must sit on the VM N face'
# 1-2. W face of the SU
mv('seq_su', su['x'] - H['seq_su']['w'], vm_top)
s = H['seq_su']
mv('xs_tap', su['x'] - H['xs_tap']['w'], s['y'] + s['h'])
x = H['xs_tap']
mv('tt_ctlm', su['x'] - H['tt_ctlm']['w'], x['y'] + x['h'])
t = H['tt_ctlm']
mv('res_train_issue', t['x'] - H['res_train_issue']['w'], t['y'])
mv('up4_sel_station', t['x'] - H['up4_sel_station']['w'] - 21.6, t['y'] + 216.0)   # 26-b select relay home beside tt_ctlm
# 3. E face of the SU
mv('native59', su['x'] + su['w'], vm_top)
# 4. clock receiver
cx, cy = (float(v) for v in a.clk.split(','))
mv('clk_rx', cx, cy)
# 5. strips
WSTRIP = [n for n in H if n.startswith(('sp_port_tiles_', 'sp_band_lanes_', 'sp_res_ser_', 'tt_up4_leaf', 'up4_sel_branch'))
          and not n.endswith('_f1')] + ['rstseq_rom']
for n in WSTRIP:
    H[n]['x'] = g(H[n]['x'] + a.dxw)
for n in [n for n in H if n.endswith('_f1')]:
    H[n]['x'] = g(H[n]['x'] - a.dxe)
for n in ('sp_port_tiles_1', 'sp_band_lanes_1', 'sp_res_ser_1', 'sp_port_tiles_1_f1'):
    H[n]['y'] = g(H[n]['y'] + a.dy1)
# 6. KV stack west of the native59 line: native59->d2d 1,704 b then runs over the SU E edge (M7+M9 over the M5-capped SU)
#    instead of through the cbuf/crom column window (base 0.741)
for n in ('d2d_rom', 'ucie_kv', 'bump_fwd_lrst', 'bump_fwd_epoch', 'ckb_rom', 'rs_bump'):
    H[n]['x'] = g(H[n]['x'] + a.kvdx)
# 7. cbuf|crom pairs abutted (crom_g -> cbuf_g 719 b face to face, no vertical run through the native59 line window):
#    4 rows x 2 pairs on the SU E face above native59; the inner pair's cbuf touches the SU E face (cbuf -> SU 718 b)
if a.cbuf_pack:
    n0 = H['native59']; x0 = su['x'] + su['w']; y0 = n0['y'] + n0['h'] + 21.6
    cw, rw, ch = H['cbuf_g_0']['w'], H['crom_g_0']['w'], H['crom_g_0']['h']
    for k in range(8):
        r, c = k // 2, k % 2
        y = y0 + r * (ch + 4.32)
        if c == 0:
            H[f'cbuf_g_{k}']['x'] = g(x0 + 0.216); H[f'crom_g_{k}']['x'] = g(x0 + 0.216 + cw + 0.432)
        else:
            xr = x0 + 0.216 + cw + 0.432 + rw + 4.32
            H[f'crom_g_{k}']['x'] = g(xr); H[f'cbuf_g_{k}']['x'] = g(xr + rw + 0.432)
        H[f'cbuf_g_{k}']['y'] = g(y); H[f'crom_g_{k}']['y'] = g(y)
    assert max(H[f'cbuf_g_{k}']['x'] + cw for k in range(8)) < min(H[n]['x'] for n in H if n.endswith('_f1')), 'cbuf pack hits the E strip'
# legality: no overlaps among non-field blocks, all inside the die
D = B['die']
blk = [(n, h) for n, h in H.items()]
for n, h in blk:
    assert h['x'] >= -1e-3 and h['y'] >= -1e-3 and h['x'] + h['w'] <= D['w'] + 1e-3 and h['y'] + h['h'] <= D['h'] + 1e-3, n
import itertools
core = [(n, h) for n, h in blk if not n.startswith(('t_', 's_', 'h_', 'x'))] + [(n, h) for n, h in blk if n.startswith('xs_tap')]
ov = []
for (n1, a1), (n2, a2) in itertools.combinations(blk, 2):
    if min(a1['x'] + a1['w'], a2['x'] + a2['w']) - max(a1['x'], a2['x']) > 0.01 and \
       min(a1['y'] + a1['h'], a2['y'] + a2['h']) - max(a1['y'], a2['y']) > 0.01:
        ov.append((n1, n2))
assert not ov, ov[:10]
res = dict(B); res['homes'] = H; res['candidate'] = Path(a.out).stem.replace('-homes', '')
res['params'] = dict(B['params'], source='mk_dieplan2.py', base=Path(a.base).name, dxw=a.dxw, dxe=a.dxe, dy1=a.dy1, kvdx=a.kvdx, cbuf_pack=a.cbuf_pack, clk_rx=[cx, cy],
                     interim_exception='option (a) port<->_f1 pair lines (3 x 6,704 b) at the 0.82 centroid-line floor; b2 removes them')
Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
print(json.dumps({n: [H[n]['x'], H[n]['y']] for n in ('seq_su', 'xs_tap', 'tt_ctlm', 'res_train_issue', 'native59', 'clk_rx', 'sp_port_tiles_0')}))
