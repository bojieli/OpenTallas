#!/usr/bin/env python3
"""kv-die 2026-10-09: the two-die Qwen floorplan for the Chip Explorer (geo key `qwen_kvdie`): the r22k ROM die with
the KV die hanging off its S edge, the two UCIe macros facing each other (same x), drawn in one frame.

    python3 tools/qwen_kv_die/explorer_geo.py --rom results/arch/qwen_kv_die_20261009/rom_r22k_insts.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import kv_die as KV     # noqa: E402

GEO = ROOT / 'site/chip_explorer/inputs/geo.json'
GAP = 200.0             # die-to-die spacing drawn (um; UCIe-A reach <= 2 mm)
ROM_KIND = dict(tile='tile', station='station', head='col_head', io='io', xfifo='io', link_station='link_station',
                phy_d2d='link', d2d='link', clock_root='hub')
KV_KIND = dict(phy='phy', ctrl='hbm_ctrl', cdc='cdc', land='link_fifo', row_engine='row_engine', attn_stack='row_engine',
               attn_hub='row_engine', seq='spine', embgw='spine', pll='spine', host='io', phy_host='io', phy_d2d='link',
               d2d='link')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rom', type=Path, required=True)
    ap.add_argument('--geo', type=Path, default=GEO)
    a = ap.parse_args()
    rom = json.loads(a.rom.read_text())
    kv = KV.build()
    rw, rh = rom['die']
    kw, kh = kv['die']['w'], kv['die']['h']
    ru = next(r for r in rom['insts'] if r[0] == 'ucie_kv')
    ku = next(i for i in kv['insts'] if i.name == 'ucie_rom')
    kx = ru[3] + ru[5] / 2 - (ku.x + ku.w / 2)          # align the macro centres
    x0 = min(0.0, kx)
    W = max(rw, kx + kw) - x0
    H = kh + GAP + rh
    kinds, rects, meta, counts = [], [], {}, {}

    def kid(k):
        if k not in kinds:
            kinds.append(k)
        return kinds.index(k)
    for name, master, kind, x, y, w, h in rom['insts']:
        k = ROM_KIND.get(kind)
        if kind == 'spine_block':
            k = 'band_slab' if master.startswith('qfd_port_tiles') else 'spine'
        if k is None:
            continue
        rects.append([k, round(x - x0, 1), round(y + kh + GAP, 1), round(w, 1), round(h, 1), 'rom:' + name])
        meta['rom:' + name] = master
    for i in kv['insts']:
        k = KV_KIND.get(i.kind)
        if k is None:
            continue
        rects.append([k, round(i.x + kx - x0, 1), round(i.y, 1), round(i.w, 1), round(i.h, 1), 'kv:' + i.name])
        meta['kv:' + i.name] = i.master
    out = []
    for k, x, y, w, h, n in rects:
        out.append([kid(k), x, y, w, h, n])
        counts[k] = counts.get(k, 0) + 1
    g = json.loads(a.geo.read_text())
    g['qwen_kvdie'] = dict(w=round(W, 3), h=round(H, 3), kinds=kinds, rects=out, meta=dict(
        masters=meta, dies=dict(rom=dict(x=round(-x0, 1), y=round(kh + GAP, 1), w=rw, h=rh, label='r22k ROM die'),
                                kv=dict(x=round(kx - x0, 1), y=0.0, w=kw, h=kh, label='KV die')),
        note='ROM die (r22k) above, KV die below its S edge; the UCIe macros (link) face each other; relays omitted'),
        counts=counts)
    a.geo.write_text(json.dumps(g, separators=(',', ':')) + '\n')
    print(dict(w=round(W), h=round(H), rects=len(out), counts=counts))


if __name__ == '__main__':
    main()
