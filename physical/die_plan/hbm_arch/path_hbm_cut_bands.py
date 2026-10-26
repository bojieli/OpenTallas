#!/usr/bin/env python3
"""HBM B1-M5 cut delta (COORD PLAN-DELTA 2026-10-26 01:21: "spu1 band widening and the b002/b011 FT bands
(cuts 0.597-0.62 -> <=0.60)"): add NS die_ft_bands (M5+M7, die_share 1.0) under the heavy vertical FT bundles
that the cut lower bound (batch_2330/cutbound/cutbound.py) and G0 found above 0.55-0.60 on horizontal cuts.

- q_spu1 (no cores; H@5.9 mm 8,359 b / 13,387 tracks = 0.62): band under the L2 N window (2,999 b), x 276.48-786.24.
- q_b002 / q_b011 (380-um bank columns; one 2,068-b lane L17 / L15 jogs N-S at the column centre x 190.08: 0.597):
  band x 129.60-250.56.
- q_b010 (G0 H@8250 0.67: L14 2,068 b + L36 1,329 b + L107 cross at x 414.72, outside its existing NS band
  552.96-829.44 that carries L28): band x 328.32-501.12.
Spans are type frame (NE instances are MY mirrors), on the 8.64-um grid, sized at <= 0.55 of the band tracks for
the bundles they carry. No window, outline, core or station changes; the kit keeps its own routing off M5/M7 there.
"""
import argparse, json, shutil
from pathlib import Path

BANDS = {
    'q_spu1': [(276.48, 786.24, 'L2 N->W 2999 b bundle (N window 278.59-778.75); H-cut 0.62 -> band')],
    'q_b002': [(129.60, 250.56, 'L17 2068 b W->E N-S jog at the column centre; H-cut 0.597 -> band')],
    'q_b011': [(129.60, 250.56, 'L15 2068 b E->W N-S jog at the column centre; H-cut 0.597 -> band')],
    'q_b010': [(328.32, 501.12, 'L14 2068 b + L36 1329 b + L107 N-S jogs at x 414.72; H-cut 0.67 -> band')],
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--src', type=Path, required=True); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists(): raise SystemExit('output must be new')
    p = json.loads((a.src / 'die_plan.json').read_text()); rep = []
    for tn, spans in BANDS.items():
        t = p['partition_types'][tn]; w = t['outline_um'][0]; bands = t.setdefault('die_ft_bands', [])
        for lo, hi, why in spans:
            assert 0 <= lo < hi <= w, (tn, lo, hi, w)
            for b in bands:
                if b['dir'] == 'NS' and b['span_um'][0] < hi and lo < b['span_um'][1]:
                    raise SystemExit(f'{tn}: new NS band {lo}-{hi} overlaps {b["span_um"]}')
            bands.append({'dir': 'NS', 'span_um': [lo, hi], 'layers': ['M5', 'M7'], 'die_share': 1.0,
                          'note': 'PATH-HBM B1-M5 cut delta (COORD 10-26 01:21): ' + why})
            rep.append(dict(type=tn, span_um=[lo, hi], why=why))
    shutil.copytree(a.src, a.out)
    (a.out / 'die_plan.json').write_text(json.dumps(p, indent=1) + '\n')
    (a.out / 'cut_bands_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep))


if __name__ == '__main__': main()
