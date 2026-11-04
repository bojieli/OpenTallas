#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v part 2: keybuf_slice macro sites for the DIE-HBM-61/MEM right-width SRAMs (55c4a61894a,
OT_HBM_RW_MACROS): 4x ot_sram_1r1w_256x256_m2_r0c0_g256 (169.368 x 28.392) + 1x ot_sram_1r1w_256x64_m2_r0c0_g64
(53.16 x 28.392); LEF: read port (clk, r_*, rd_out) on the macro W edge, write port (w_*, wd_in) on the E edge, M4.
RTL: wd = key_in[1098:11] (write), key_out = replay_v ? {rd, tag} : key_in (read + bypass mux).
Form: one stacked column, orient MY (write pins face W = key_in, read pins face E = key_out), with
  W logic channel 31.32 um   (key_in 1132 face pins x 0.048 / 2 vertical layers M5/M7 = 27.2 um of jog tracks),
  E logic channel 41.23 um   (key_out 1099 pins: 26.4 um + the read mux; holds the clock island [203.04,142.56,211.68,151.2]),
  5 row gaps 25.3 um         (key_in -> key_out bypass 1099 bits on M4/M6 between the rows: ~31 um needed of 151 um),
so no route has to cross a SRAM.  Writes core_macros.json cores[keybuf] (old entry kept under previous).
    python3 mk_kbmac.py PLAN_DIR"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); f = d / 'core_macros.json'; C = json.loads(f.read_text())
M = 'ot_hnx_idxn_keybuf_slice'; old = C['cores'][M]
X0, X1, Y0, PY, HM = 31.32, 200.688, 25.272, 53.784, 28.392
mac = []
for k in range(5):
    y = round(Y0 + k * PY, 3)
    if k < 4:
        mac.append(dict(name=f'u_fcore.gm[{k}].g_rw.mem', master='ot_sram_1r1w_256x256_m2_r0c0_g256', orient='MY',
                        rect_um=[X0, y, X1, round(y + HM, 3)]))
    else:
        mac.append(dict(name='u_fcore.gm[4].g_rw64.mem', master='ot_sram_1r1w_256x64_m2_r0c0_g64', orient='MY',
                        rect_um=[round(X1 - 53.16, 3), y, X1, round(y + HM, 3)]))
C['cores'][M] = dict(status='KNOWN', outline_um=old['outline_um'], basis=(
    'DIE-HBM-61/PLAN d44v p2: MEM 55c4a61894a right-width SRAMs (OT_HBM_RW_MACROS, recipe inst renames), one column '
    'orient MY: write pins W (key_in), read pins E (key_out); W channel 31.32, E channel 41.23 (clock island clear), '
    'row gaps 25.392 x 6 for the key_in->key_out bypass; no route over a SRAM'), macros=mac,
    channel_rule_um=old.get('channel_rule_um', 10.8), previous={k: v for k, v in old.items() if k != 'previous'})
f.unlink(); f.write_text(json.dumps(C, indent=1) + '\n')
print(M, [m['rect_um'] for m in mac])
