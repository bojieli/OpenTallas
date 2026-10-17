#!/usr/bin/env python3
"""Q-DIEPLAN3 (2026-10-16): q2o4 homes from q2o2d -- VM/SU seam routing channel.

q2o3 census: ~1,300 VM N-face clock pins (native_ck, relay_ck, write_ck, ck_r0..7, M5) and rst_n lie UNDER the abutted SU
(x 15.26-17.18 mm): a sealed seam. The core north stack (every centre block whose origin is at or above the VM top: SU,
seq_su, xs_tap, embed_prov, native59, cbuf/crom, tt_ctlm, res_train_issue, up4_sel_station) moves up by --channel um,
so the VM N face gets an open M4/M5 channel; seam data (sa / sq) stays straight face to face across it. Kit grants are
master-local and unchanged; sys_face moves with the stack (print the new OT_SPLIT_SYSFACE_XY).

usage: mk_q2o4.py BASE OUT [--channel 43.2]
"""
import argparse, json
ap = argparse.ArgumentParser(); ap.add_argument('base'); ap.add_argument('out'); ap.add_argument('--channel', type=float, default=43.2)
a = ap.parse_args()
B = json.load(open(a.base)); H = B['homes']
vm = H['sp_vector_memory']; top = vm['y'] + vm['h']
STACK = ('sp_su64_sfu', 'seq_su', 'xs_tap', 'embed_prov', 'native59', 'tt_ctlm', 'res_train_issue', 'up4_sel_station')
moved = []
for n, h in H.items():
    if n in STACK or n.startswith(('cbuf_g_', 'crom_g_')):
        assert h['y'] >= top - 0.1, n
        h['y'] = round(h['y'] + a.channel, 3); moved.append(n)
P = B['params']
P['sysface_xy'] = [P['sysface_xy'][0], round(P['sysface_xy'][1] + a.channel, 3)]
P['vm_su_channel_um'] = a.channel; P['source'] = 'mk_q2o4.py'; P['base_q2o4'] = a.base
B['candidate'] = 'q2o4'
json.dump(B, open(a.out, 'w'), indent=1)
print(f'moved {len(moved)}: {moved}; sysface_xy {P["sysface_xy"]}')
