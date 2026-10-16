#!/usr/bin/env python3
"""Contract pin plans of the sel / col engine endpoint tiles dsfd_dw_ep_s / dsfd_dw_ep_c (s81-ctl-1011, 2026-10-11; RTL
rtl/dsrom_sys/s81_ctrl/dsfd_dw_ep.sv).  64.8 x 64.8 um (x on the 10.8 lcm, y on the 2.16 lcm): N face = the vd snoop
(26 b from the slab's vd-driving tile: dsfd_selt_c / dsfd_colt_mrg), S face = the engine die nets c_cmd 85 in, c_done 9
out, c_st 2 out (toward the band block's die edge) + ck / rs.  ~2k flops (pulse CDC queues, job queue, pending maps).

    python3 tools/s81_ph/s81_ph_dw_ep_plan.py -> physical/s81_ph_views/ports/contract/dsfd_dw_ep_{s,c}/{ports.json,io_place.tcl}
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_ph'))
import s81_ph_tiles_plan as TP  # noqa: E402

W, H = 64.8, 64.8
for m in ('dsfd_dw_ep_s', 'dsfd_dw_ep_c'):
    spec = dict(master=m, w_um=W, h_um=H, domain='stream_1p2',
                note='N = vd snoop, S = engine die nets + clock / reset, M5, pitch 2 tracks',
                ports=[['vh', 26, 'input', 'N', 'M5', 2, 0.5],
                       ['c_cmd', 85, 'input', 'S', 'M5', 2, 0.30], ['c_done', 9, 'output', 'S', 'M5', 2, 0.66],
                       ['c_st', 2, 'output', 'S', 'M5', 2, 0.74], ['ck', 1, 'input', 'S', 'M5', 1, 0.82],
                       ['rst', 1, 'input', 'S', 'M5', 1, 0.86]])
    ports = TP.plan(spec)
    TP.write(m, W, H, 'stream_1p2', ports, spec)
    print(m, sum(len(p['pins']) for p in ports.values()))
