#!/usr/bin/env python3
"""S81 scan and head die recipes on the 1,792-pair mapping (stream s81-dies, 2026-10-08).

The layer1 die (m221pq, results/rtl/dsrom_s81_fulldie_20261004/m221pq/options.txt) is the only S81 die built on the
1,792 mapping.  This file holds SEPARATE recipe entries for the other two die kinds the generator draws
(tools/dsrom_s81_fulldie.py is owned by the s81-die-2 stream: this file only passes generator options, it does not
change the generator), on the same m221pq frames, the same element views and the same --nxt-reach relay rule as the
r4b layer1 chain:

  scan      the 4-stack index-scanning stage die (32 of the rack: 8 scan stages x TP4), q-only flavour: the 1,792
            mapping puts every scan service home on a q stage (scanbf: the BF-flavour sensitivity).  m221pq options at --die layer
            (the generator's 4-stack kind: 4 PHY + 4 ctrl + 4 svc quarters, the layer-die VM 2.66 mm2 and the WFC soft
            reservation).  The 4-stack spine (VM 2.66 + WFC 0.456 on top of the layer1 spine) overflows the 1,728 um
            hub columns by ~200 um, and the die has only 90 um of horizontal slack (the W link stations need it), so the
            hub columns widen to 1,771.2 um and the VCH narrows 1,641.6 -> 1,555.2 um: the spine keeps its width.
  head12    the head die with its CURRENT content (embed + norm + lm-head bundles + the whole DSpark drafter:
            1,471 pairs + 85 head bundles a die over 12 dies), uniform 221.4 um frames (the qs5f q element; the
            generator's mixed q/BF frames are layer-die only).  Recorded to show whether it fits.
  head14    the same content over 14 head dies (structural option: add head dies).
  headp2    the mtp-die P2 proposal (claude/mtp-die-20261008, results/arch/mtp_die_20261008/plan.json, NOT on main):
            the drafter's experts move to 40 draft dies, the head die keeps 511 pairs (globals 2,526 / 12 + DP1
            primary 282 + Markov 18) + 85 bundles.  The MTP sequencer / accept slab and the 5 draft fan-out SerDes come
            from mtp-die's generator flags (--mtp-seq --mtp-links 5) once they land on main; until then they are
            PLACEHOLDER area in the array composition (tools/dsrom_array_v2.py), not in this floorplan.

Every recipe sets OT_S81_Q_LEF to the qs5f q abstract (as the m221pq / r4b chains do).

    python3 tools/s81/s81_dies_recipe.py plan  [--only scan,head12,...]   # floorplan record + DEF + SVG + margin lint
    python3 tools/s81/s81_dies_recipe.py opts  <name>                      # the generator option string
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q_LEF = 'physical/s81_die_views/q_elem_qs5f/q_elem.lef.gz'
os.environ.setdefault('OT_S81_Q_LEF', Q_LEF)
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as F  # noqa: E402

OUT = ROOT / 'results/rtl/dsrom_s81_fulldie_20261004/s81dies'
LAYER1 = 'results/rtl/dsrom_s81_fulldie_20261004/m221pq/options.txt'


def _layer1_opts():
    o = (ROOT / LAYER1).read_text().split()
    i = o.index('--die')
    return o[:i] + o[i + 2:] + ['--nxt-reach']          # r4b: r3 options + --nxt-reach


def _sub(o, k, v=None):
    o = list(o)
    if k in o:
        i = o.index(k)
        del o[i:i + (2 if v is not False and i + 1 < len(o) and not o[i + 1].startswith('--') else 1)]
    if v is not None and v is not False:
        o += [k] if v is True else [k, str(v)]
    return o


def _head_base():
    o = _layer1_opts()
    for k in ('--bf-per-region', '--pairs', '--q-elem-h'):
        o = _sub(o, k)
    o = _sub(o, '--pq-place', False)
    return _sub(o, '--elem-h', 221.4) + ['--frame-out-relay']


def recipes():
    scan = _sub(_sub(_layer1_opts(), '--hub-column-width', 1771.2), '--vch-w', 1555.2)
    hb = _head_base()
    return {
        'scan': dict(opts=_sub(scan, '--bf-per-region', 0) + ['--die', 'layer'],
                     role='scan die (4 HBM3E stacks), 32 of the rack: q-only flavour',
                     note='the 1,792 mapping homes every scan service on a q stage (half_dedicated stage_map '
                          'scan_service_homes 7, 25, ..., 109; flavour b q q): --bf-per-region 0 on the m221pq frames; '
                          'hub columns 1,771.2 um / VCH 1,555.2 um (spine width unchanged)'),
        'scanbf': dict(opts=scan + ['--die', 'layer'], role='scan die, BF flavour (sensitivity: a scan home on a BF stage)',
                       note='m221pq BF-flavour frames (4 BF a region); hub columns 1,771.2 um / VCH 1,555.2 um'),
        'head12': dict(opts=hb + ['--die', 'head', '--head-dies', '12'], role='head die, current content, 12 dies',
                       note='uniform 221.4 um frames; content = embed + lm-head bundles + the whole drafter'),
        'head14': dict(opts=hb + ['--die', 'head', '--head-dies', '14'], role='head die, current content, 14 dies',
                       note='structural option: the 12-die content over 14 dies'),
        'headp2': dict(opts=hb + ['--die', 'head', '--head-dies', '12', '--pairs', '511'],
                       role='head die, mtp-die P2 content (511 pairs + 85 bundles), 12 dies',
                       note='PLACEHOLDER content from the uncommitted mtp-die plan; MTP sequencer + 5 SerDes pending '
                            'its --mtp-seq / --mtp-links flags'),
    }


def build(opts):
    ap = argparse.ArgumentParser()
    F.die_options(ap)
    a = ap.parse_args(opts)
    F.apply_options(a)
    m = F.build()
    F.finalize_r8(m)
    return m


def plan(name, r):
    out = OUT / name
    out.mkdir(parents=True, exist_ok=True)
    try:
        m = build(r['opts'])
    except (AssertionError, RuntimeError) as e:            # a recipe that does not fit is a recorded result
        rec = dict(schema='opentallas.s81-dies.recipe.v1', name=name, role=r['role'], note=r['note'],
                   options=' '.join(r['opts']), q_lef=Q_LEF, fits=False, error=f'{type(e).__name__}: {e}')
        (out / 'floorplan.json').write_text(json.dumps(rec, indent=1) + '\n')
        (out / 'options.txt').write_text(' '.join(r['opts']) + '\n')
        return rec
    rec = F.plan_record_r8(m)
    rec['legality_python'] = F.legality(m)
    rec['generated_pin_clashes'] = len(F.pin_clashes(m))
    rec['windows_um'] = F.windows(m)
    rec['child_reservations'] = m.get('child_reservations', {})
    rec['margin_lint'] = F.margin_lint(m)
    rec['recipe'] = dict(name=name, role=r['role'], note=r['note'], options=' '.join(r['opts']), q_lef=Q_LEF,
                         tool='tools/s81/s81_dies_recipe.py', fits=True)
    (out / 'floorplan.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
    (out / 'options.txt').write_text(' '.join(r['opts']) + '\n')
    F.svg(m, out / 'floorplan.svg')
    F.write_def_floorplan(m, out / 'floorplan.def')
    for f in ('floorplan.svg', 'floorplan.def'):
        with open(out / f, 'rb') as s, gzip.open(out / (f + '.gz'), 'wb', compresslevel=9) as d:
            shutil.copyfileobj(s, d)
        (out / f).unlink()
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'opts'])
    ap.add_argument('name', nargs='?')
    ap.add_argument('--only', default='')
    a = ap.parse_args(argv)
    R = recipes()
    if a.mode == 'opts':
        print(' '.join(R[a.name]['opts']))
        return 0
    names = [n for n in R if not a.only or n in a.only.split(',')]
    res = {}
    for n in names:
        rec = plan(n, R[n])
        ml = rec.get('margin_lint', {})
        res[n] = dict(fits=rec.get('recipe', rec).get('fits'), error=rec.get('error'),
                      placed_mm2=rec.get('placed_footprint_mm2'), util=rec.get('utilisation'),
                      legality=rec.get('legality_python'), pin_clashes=rec.get('generated_pin_clashes'),
                      margin_lint=ml.get('verdict'))
        print(n, json.dumps(res[n]), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
