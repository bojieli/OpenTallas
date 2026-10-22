#!/usr/bin/env python3
"""Die RC model when M8 carries die signals (ROOT14 10-20; owner 21:27: M8 open for die SIGNAL routing, M9 stays
PG/clock, regular PG straps kept on M8; COORD 21:24: the M8 RC/repeater model is owed in die STA).

S81 repair 66736dcff made it opt-in (--signal-top-layer M8).  This is the one rule every die flow uses, default ON:
a die whose signal routing reaches M8 (or M9) gets
  * repeater step  rc_layer M8  (tools/die_repeaters: repair_design spaces repeaters on the M8 wire RC; the post-GRT
                                 audit then re-judges slew / cap on the real per-layer GRT parasitics),
  * die STA        set_wire_rc -signal -layer M8 for every placement-estimate fallback, and GRT parasitics
                   (estimate_parasitics -global_routing) with the per-layer M8 RC of setRC.tcl -- the STA must read
                   GRT parasitics; a placement-only estimate on an M8 die is labelled NOT a die timing result.
Dies whose signals stop at M7 keep the old model (repeaters M4, STA wire RC M6).

    m8.model('M8') -> {'m8_signals': True, 'repeater_rc_layer': 'M8', 'sta_wire_rc_layer': 'M8', ...}
    m8.top_from_range('M4-M9') -> 'M9'
    python3 tools/die_safety/m8.py M2-M8 [--field repeater_rc_layer]
"""
import argparse
import json
import re
import sys

M8_TOPS = ('M8', 'M9')


def top_from_range(rng):
    """'M2-M8' / 'M4-M9' / 'M8' -> top layer name"""
    layers = re.findall(r'M(\d+)', str(rng or ''))
    if not layers:
        raise ValueError(f'no metal layer in {rng!r}')
    return f'M{max(int(x) for x in layers)}'


def model(signal_top='M7'):
    top = top_from_range(signal_top)
    m8 = top in M8_TOPS
    return dict(signal_top_layer=top, m8_signals=m8,
                repeater_rc_layer='M8' if m8 else 'M4',
                sta_wire_rc_layer='M8' if m8 else 'M6',
                sta_parasitics='global_routing (per-layer setRC.tcl incl. M8); placement fallback = NOT a die result' if m8
                else 'global_routing',
                ir_drop_required=m8)


def sta_rc_tcl(signal_top='M7', plat='/OpenROAD-flow-scripts/flow/platforms/asap7'):
    m = model(signal_top)
    return f"source {plat}/setRC.tcl\nset_wire_rc -signal -layer {m['sta_wire_rc_layer']}\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('signal_layers', help='signal routing range or top layer, e.g. M2-M8')
    ap.add_argument('--field')
    a = ap.parse_args(argv)
    m = model(a.signal_layers)
    print(m[a.field] if a.field else json.dumps(m))
    return 0


if __name__ == '__main__':
    sys.exit(main())
