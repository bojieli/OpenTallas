#!/usr/bin/env python3
"""Move t53 FT1's H jog out of the left macro-stack mouth, with unchanged registered depths.

The intended base is S81 FT-A8 (d3e52900e6). This is a geometry candidate, not a sign-off view.
Usage: python3 physical/die_plan/s81/delta_ft_t53_top_2144.py INPUT_PLAN OUTPUT_PLAN
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/die_plan'), str(Path(__file__).parent)]
import compact_plan
import ft_corridor


def apply(raw):
    tn = 'ot_s81sl_leaf__t53'
    ty = raw['partition_types'][tn]
    depth = {s['name']: s['stations'] for s in ty['ft_slots']}
    if depth != {'ft0': 6, 'ft1': 7}:
        raise ValueError(f'{tn}: expected FT-A8 depths6/7, got {depth}; reprice before changing the vehicle')
    before_cores = json.dumps(ty['hard_cores'], sort_keys=True)
    split = {f'{tn}/{s["name"]}': 128 for s in ty['ft_slots']}
    ledger = ft_corridor.place(raw, [tn], split_bits=split,
                              jogs={f'{tn}/ft0': 19.5, f'{tn}/ft1': 1150.2})
    assert before_cores == json.dumps(ty['hard_cores'], sort_keys=True)
    assert depth == {s['name']: s['stations'] for s in ty['ft_slots']}
    return ledger


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan')
    ap.add_argument('out')
    ap.add_argument('--ledger')
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    ledger = apply(raw)
    Path(a.out).write_text(compact_plan.dumps(raw))
    if a.ledger:
        Path(a.ledger).write_text(json.dumps(ledger, indent=2) + '\n')
    print('FT t53 top-jog candidate: same cores, ports, outline and depths; added cycles0')


if __name__ == '__main__':
    main()
