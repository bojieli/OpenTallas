#!/usr/bin/env python3
"""Per-die measured relay reach: the one source of truth for die-level repair_design -max_wire_length.

COORDINATOR STANDARD 1 (owner 10-16, safe margins): the measured reach of a die (relay launch + capture + neighbour skew,
TT) is its planning constant, and a die generator's repair max wire length = that reach, never above it -- a long
unrelayed die wire must be a hard error, never silently buffered.

    reach_um('hbm')                       -> 450.0 (raises DieReachError when the design is missing: fails closed)
    add_args(ap, 'hbm'); v = from_args(a, 'hbm')
        --max-wire-um UM                  default = reach_um(design); a value above the reach is REFUSED ...
        --allow-over-reach REASON         ... unless a non-empty reason is given (recorded in the manifest)
    repair_tcl(v, '-buffer_gain 4.0')     -> 'repair_design -max_wire_length 450 -buffer_gain 4.0'

Values and evidence: results/arch/die_reach_1016.json (OT_DIE_REACH overrides the path).
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REACH_FILE = ROOT / 'results/arch/die_reach_1016.json'


class DieReachError(ValueError):
    pass


def _file():
    return Path(os.environ.get('OT_DIE_REACH') or REACH_FILE)


def record(design):
    p = _file()
    if not p.exists():
        raise DieReachError(f'die reach table missing: {p}')
    d = json.loads(p.read_text()).get('designs', {})
    r = d.get(design)
    if not r or not isinstance(r.get('reach_um'), (int, float)) or r['reach_um'] <= 0:
        raise DieReachError(f'no measured reach for die design {design!r} in {p} (known: {sorted(d)}); '
                            'measure it and add it there -- no default')
    return r


def reach_um(design):
    return float(record(design)['reach_um'])


def resolve(design, max_wire_um=None, allow_over_reach=None):
    """-> dict(value_um, reach_um, design, source, over_reach_reason); refuses value > reach without a reason."""
    reach = reach_um(design)
    v = reach if max_wire_um is None else float(max_wire_um)
    if v <= 0:
        raise DieReachError(f'--max-wire-um must be > 0 (got {v:g})')
    reason = (allow_over_reach or '').strip() or None
    if v > reach and not reason:
        raise DieReachError(f'--max-wire-um {v:g} exceeds the measured {design} die reach {reach:g} um '
                            f'({_file().name}); pass --allow-over-reach REASON to override')
    try:
        src = str(_file().resolve().relative_to(ROOT))
    except ValueError:
        src = str(_file())
    return dict(value_um=v, reach_um=reach, design=design, source=src,
                evidence=record(design).get('evidence', []), over_reach_reason=reason if v > reach else None)


def add_args(ap, design):
    ap.add_argument('--max-wire-um', type=float, default=None,
                    help=f'die repair_design -max_wire_length (um); default = measured {design} die reach '
                         f'(results/arch/die_reach_1016.json); never above it without --allow-over-reach')
    ap.add_argument('--allow-over-reach', metavar='REASON', default=None,
                    help='allow --max-wire-um above the measured reach; the reason is recorded in the manifest')


def from_args(a, design):
    try:
        return resolve(design, a.max_wire_um, a.allow_over_reach)
    except DieReachError as e:
        raise SystemExit(f'die_reach: {e}')


def repair_tcl(mw, extra=''):
    """mw = resolve() dict or a number -> the repair_design command line"""
    v = mw['value_um'] if isinstance(mw, dict) else float(mw)
    return f'repair_design -max_wire_length {v:g}' + (f' {extra}' if extra else '')


if __name__ == '__main__':
    import sys
    for d in sys.argv[1:] or json.loads(_file().read_text())['designs']:
        print(d, reach_um(d))
