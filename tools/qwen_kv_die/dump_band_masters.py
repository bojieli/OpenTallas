#!/usr/bin/env python3
"""kv-die 2026-10-09: dump the r21c HBM-band abstracts (ot_hbm3e_phy, qfd_ctrl, qfd_cdc, qfd_kvc) and the band buses
of one stack per side so the KV-die generator (tools/qwen_kv_die/kv_die.py) re-places the SAME masters and pins.

    python3 tools/qwen_kv_die/dump_band_masters.py --out tools/qwen_kv_die/r21c_band.json
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_top_lint as L               # noqa: E402
import qwen_rom_fulldie_b3r2 as B      # noqa: E402

KEEP = ('ot_hbm3e_phy', 'qfd_ctrl', 'qfd_cdc', 'qfd_kvc', 'qfd_kvc_n')
CLS = ('phy_dfi', 'hbm_cdc', 'cdc_core', 'clock_trunk', 'reset')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    r = dict(L.QWEN_RECIPES['r21c'])
    cdc = r.pop('cdc')
    v, m = B.selected(True, cdc=B._cdc_arg(cdc), **r)
    M = v.masters(m, 1)
    by = {i.name: i for i in m['insts']}
    band = {i.name for i in m['insts'] if i.kind in ('phy', 'ctrl', 'cdc', 'link_fifo')}
    buses = [(bid, cl, bits, [list(e) for e in eps]) for bid, cl, bits, eps in m['buses']
             if cl in CLS and eps and all(e[0] in band for e in eps)]
    out = dict(schema='opentallas.qwen-kv-die.r21c-band.v1', recipe='r21c',
               generator_sha256=hashlib.sha256((ROOT / 'tools/qwen_rom_fulldie_b3r2.py').read_bytes()).hexdigest(),
               masters={n: dict(w=M[n].w, h=M[n].h, obs_top=M[n].obs_top, note=M[n].note, order=list(M[n].order),
                                ports={p: list(s) for p, s in M[n].ports.items()}) for n in KEEP if n in M},
               insts={n: by[n].d() for n in sorted(band)}, buses=buses, phy_pins=[list(p) for p in v.phy_pins()])
    a.out.write_text(json.dumps(out, indent=0) + '\n')
    print(len(out['masters']), len(out['insts']), len(out['buses']))


if __name__ == '__main__':
    main()
