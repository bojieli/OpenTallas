#!/usr/bin/env python3
"""Wide-pitch dual-clock SRAM masters for the S81 CTRL rg2 SAFE successor (s81ctrl_rg2_s3, 10-19).

The stock pin-limited 1r1w2c masters put signal contacts on W/E at METAL['pin_pitch_um'] = 0.096 um
(10.4 contacts/um), which fails SAFE item 6 (<= 6 pins/um).  This builder runs the SAME compiler
(sram_gen.compile_macro) with the pin pitch set to 0.192 um (every fourth 48 nm M4 track, on-track
in every orientation), so a pin-limited master stretches its W/E faces to 5.2 contacts/um.
Nothing else changes (array, timing model, Liberty arcs, behavioural model).  Stock masters untouched.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/mem_compiler'))
import asap7  # noqa: E402
import sram_gen as S  # noqa: E402

PITCH = 0.192
MASTERS = [('ot_sram_1r1w2c_16x340_p192', 16, 340)]


def main():
    out = ROOT / 'physical/asap7_memory_macros'
    old = asap7.METAL['pin_pitch_um']
    asap7.METAL['pin_pitch_um'] = PITCH
    try:
        for name, words, bits in MASTERS:
            spec = S.SramSpec(name, words, bits, 1, 1, '1r1w2c')
            s = S.compile_macro(spec, out)
            a = s['area']
            per_edge = a['outline']['pins_per_edge']
            dens = per_edge / a['macro_height_um']
            assert dens <= 6, (name, dens)
            print(f"{name}: {a['macro_width_um']:.3f} x {a['macro_height_um']:.3f} um, "
                  f"{per_edge} contacts per W/E face = {dens:.3f}/um (pitch {PITCH})")
    finally:
        asap7.METAL['pin_pitch_um'] = old


if __name__ == '__main__':
    main()
