#!/usr/bin/env python3
"""kv-die 2026-10-09: the r22k ROM die record -- build the recipe once (tools/die_top_lint.py QWEN_R22K) and write
die size / reticle margin, the area by master family, the UCIe placement, the relay stages of every crossing bus (the
re-price reads them), the die relay margin lint (fp_margin_lint.die_margin) and the r21c -> r22k area delta.

    python3 tools/qwen_kv_die/rom_record.py --out results/arch/qwen_kv_die_20261009/rom_r22k.json
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_top_lint as L               # noqa: E402
import fp_margin_lint as FPL           # noqa: E402
import qwen_rom_fulldie_b3r2 as B      # noqa: E402

CROSS = ('x3', 'attn_ret', 'emb', 'emb_a', 'emb_cr', 'seq_d2d', 'd2d_seq', 'd2d_fdi', 'pll_fwd', 'rst_fwd')
RETICLE = 858.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    r = dict(L.QWEN_RECIPES['r22k'])
    cdc = r.pop('cdc')
    v, m = B.selected(True, cdc=B._cdc_arg(cdc), **r)
    ins = m['insts']
    W, H = m['die']['w'], m['die']['h']
    stages = Counter()
    for bid, cl, bits, eps in m['buses']:
        base = re.sub(r'__r\d+$', '', bid)
        if base in CROSS:
            stages[base] += 1
    fam = Counter()
    for i in ins:
        k = 'relay' if (i.kind or '').startswith('relay') or i.name.startswith('rly_') else i.kind or i.master
        fam[k] += i.w * i.h / 1e6
    by = {i.name: i for i in ins}
    rec = dict(
        schema='opentallas.qwen-kv-die.rom-r22k.v1', recipe='r22k = r21c + tools/qwen_kv_die/rom_r22k.py surgery',
        generator_sha256=hashlib.sha256((ROOT / 'tools/qwen_rom_fulldie_b3r2.py').read_bytes()).hexdigest(),
        surgery_sha256=hashlib.sha256((ROOT / 'tools/qwen_kv_die/rom_r22k.py').read_bytes()).hexdigest(),
        die_um=[round(W, 3), round(H, 3)], die_mm2=round(W * H / 1e6, 3), reticle_mm2=RETICLE,
        margin_mm2=round(RETICLE - W * H / 1e6, 3), r21c_die_mm2=846.792,
        instances=len(ins), buses=len(m['buses']), instance_mm2=round(sum(i.w * i.h for i in ins) / 1e6, 3),
        area_by_kind_mm2={k: round(x, 3) for k, x in sorted(fam.items(), key=lambda t: -t[1])},
        ucie=dict(by['ucie_kv'].d(), mm2=round(by['ucie_kv'].w * by['ucie_kv'].h / 1e6, 4), edge='S',
                  edge_um=round(by['ucie_kv'].w, 3)),
        d2d_rom=by['d2d_rom'].d(), clk_rx=by['clk_rx'].d(),
        crossing_bus_stages={k: max(0, stages[k] - 1) for k in CROSS},
        stage_note='relay stages = registered hops between the endpoint pins (segments - 1); every endpoint port is '
                   'registered as well (the stage the r21 token-cost counts as one per die hop)',
        r22k=m.get('r22k'),
        margin_lint=FPL.die_margin(ins, m['buses'], {i.kind for i in ins if i.name.startswith('rly_')}, reach_um=504.0),
        relay_kinds=sorted({i.kind for i in ins if i.name.startswith('rly_')}))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=str) + '\n')
    # block rectangles (relays omitted) for the two-die explorer view
    (a.out.parent / 'rom_r22k_insts.json').write_text(json.dumps(
        dict(die=[round(W, 3), round(H, 3)], insts=[[i.name, i.master, i.kind, round(i.x, 2), round(i.y, 2), round(i.w, 2),
                                                     round(i.h, 2)] for i in ins if not i.name.startswith('rly_')]),
        separators=(',', ':')) + '\n')
    print(json.dumps({k: rec[k] for k in ('die_um', 'die_mm2', 'margin_mm2', 'crossing_bus_stages')}))
    print(json.dumps({k: rec['margin_lint'][k] for k in rec['margin_lint'] if 'examples' not in k}))


if __name__ == '__main__':
    main()
