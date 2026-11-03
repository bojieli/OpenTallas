#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v part 4 (fix-only after freeze, KW-FIX-4 11:58 SWITCH holds): KNOWN right-width macro sites
(DIE-HBM-61/MEM 55c4a61894a, OT_HBM_RW_MACROS, recipe inst renames) for hfd_ep_static and ot_hbm_host_cp_rxs, the
keybuf part-2d form.  Outlines kept (ep 427.68x246.24, cp_rxs 400.248x151.68).  LEF: read port on the master W
edge, write port on the E edge, M4; W/E-pinned masters have no N/S pins (8.64 row gap).
  hfd_ep_static: 4x ot_sram_1r1w_64x306_m1_r0c0_g306 (106.056 x 31.896) in the old 2x2 r2c2 grid, same orients
    (W column MY, E column R0: read pins face the centre logic channel), each macro on the centre-facing edge of
    its old rect, rows on the old row centres; centre channel 50.5 um holds the clock entry (216.0, 120.96);
    82.5 um W/E logic fields for the 612+612 side pins, 70 um S field for the 1050 S pins.
  ot_hbm_host_cp_rxs: S-edge block (S face has no pins; N 1248, E 110, W 9), 2 columns (channel_fit 2x3):
    row 0 the 2 landing banks ot_sram_1r1w_256x256_m2_r0c0_g256 (169.368 x 28.392), rows 1-2 the 4 llr leaves
    ot_sram_1r1w_64x141_m1_r0c0_g141 (56.184 x 20.808) on the centre-facing side; W column MY, E column R0;
    edge 15.12 (4.32 + 10.8), centre channel 31.2 um holds the clock entry (198.72, 77.76); N std-cell band 49 um.
Writes core_macros.json cores[<module>] (old entry kept under previous).     python3 mk_rwmac.py PLAN_DIR"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); f = d / 'core_macros.json'; C = json.loads(f.read_text())
r3 = lambda v: round(v, 3)
G306, G141, G256 = ('ot_sram_1r1w_64x306_m1_r0c0_g306', 106.056, 31.896), ('ot_sram_1r1w_64x141_m1_r0c0_g141', 56.184, 20.808), \
    ('ot_sram_1r1w_256x256_m2_r0c0_g256', 169.368, 28.392)
def mac(name, m, orient, x0, y0):
    return dict(name=name, master=m[0], orient=orient, rect_um=[r3(x0), r3(y0), r3(x0 + m[1]), r3(y0 + m[2])])
ENT = {'hfd_ep_static': (216.0, 120.96), 'ot_hbm_host_cp_rxs': (198.72, 77.76)}
NEW = {}
# ep: left col x1 188.568 (MY), right col x0 239.112 (R0); rows y0 70.416 / 169.776
ep = 'u_fcore.u_rxb.g_block[%d].u_block.g_mem[%d].u_mem.g_rw.u_sram'
NEW['hfd_ep_static'] = [mac(ep % (b, m), G306, 'MY' if b == 0 else 'R0', 82.512 if b == 0 else 239.112, (70.416, 169.776)[m])
                        for m in (0, 1) for b in (0, 1)]
# cp_rxs: left col x0 15.12 (MY), right col x0 215.676 (R0, E edge gap 15.204)
lk = 'u_fcore.u_link.g_bank[%d].u_store.u_native.g_rw141.u_sram'
XL, XR, Y0, Y1, Y2 = 15.12, 215.676, 15.12, 52.164, 81.648
NEW['ot_hbm_host_cp_rxs'] = [
    mac('u_fcore.u_land.g_bank[0].u_mem', G256, 'MY', XL, Y0), mac('u_fcore.u_land.g_bank[1].u_mem', G256, 'R0', XR, Y0),
    mac(lk % 3, G141, 'MY', XL + G256[1] - G141[1], Y1), mac(lk % 2, G141, 'MY', XL + G256[1] - G141[1], Y2),
    mac(lk % 1, G141, 'R0', XR, Y1), mac(lk % 0, G141, 'R0', XR, Y2)]
for M, ms in NEW.items():
    old = C['cores'][M]; W, H = old['outline_um']; ex, ey = ENT[M]
    for a in ms:   # inside the outline with the 4.32 edge, 8.64 apart, clear of the clock entry by the 4.32 halo
        x0, y0, x1, y1 = a['rect_um']
        assert x0 >= 4.32 and y0 >= 4.32 and x1 <= W - 4.32 and y1 <= H - 4.32, (M, a)
        assert not (x0 - 4.32 < ex < x1 + 4.32 and y0 - 4.32 < ey < y1 + 4.32), (M, a)
        for b in ms:
            if b is a: continue
            u0, v0, u1, v1 = b['rect_um']
            assert min(x1, u1) - max(x0, u0) < -8.63 or min(y1, v1) - max(y0, v0) < -8.63, (M, a, b)
    C['cores'][M] = dict(status='KNOWN', outline_um=old['outline_um'], basis=(
        'DIE-HBM-61/PLAN d44v p4: MEM 55c4a61894a right-width SRAMs (OT_HBM_RW_MACROS, recipe inst renames), keybuf '
        'p2d form: W column MY / E column R0, read pins (master W edge) face the centre logic channel, write pins '
        'outward; >=10.8 pin channels, 8.64 row gaps, clock entry in the centre channel; outline kept'), macros=ms,
        channel_rule_um=old.get('channel_rule_um', 10.8), previous={k: v for k, v in old.items() if k != 'previous'})
    print(M, old['status'], '->', 'KNOWN', len(ms), 'macros')
f.unlink(); f.write_text(json.dumps(C, indent=1) + '\n')
