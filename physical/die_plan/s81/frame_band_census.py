#!/usr/bin/env python3
"""S81-P6 10-23: frame-band census from the BAND RTL (COORD: the census missed band-internal logic).

Reads the banded seam kits (frame_seam_pipe.py output: one band module per lp region r0/r1/r2 + the wiring top) and
writes inputs/frame_band_census.json = band-to-band bits per master (driver band -> reader band, every band port net of
the wiring top; the lpr_root reset feedthrough through b1 included).  gen_plan_v4.py takes the frame-internal lane
widths from it, census_cov.py checks every frame's fi_* lanes against it.

  frame_band_census.py [--out physical/die_plan/s81/inputs/frame_band_census.json]
"""
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
import frame_seam_pipe as S  # noqa: E402

KITS = {"h9": "rtl/dsrom_sys/s81_dv/frame_lp/kit/col_h9_l4_lp_kit_vgcs.sv",
        "h10": "rtl/dsrom_sys/s81_dv/frame_lp/kit/col_h10_l4_lp_kit_vgcs.sv"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'physical/die_plan/s81/inputs/frame_band_census.json'))
    a = ap.parse_args()
    res = dict(note="band-to-band bits of the banded seam frame kits (frame_seam_pipe.py); keys rA->rB = band A drives "
                    "band B; source = the band RTL, not a constant", masters={}, sources={})
    for m, f in KITS.items():
        t = (ROOT / f).read_text()
        top = 'col_%s_l4_lp' % m
        x = S.crossings(t, top)
        res["masters"][m] = {k.replace('b', 'r'): v for k, v in x.items()}
        res["sources"][m] = dict(rtl=f, sha256=hashlib.sha256(t.encode()).hexdigest())
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(res["masters"]))


if __name__ == '__main__':
    main()
