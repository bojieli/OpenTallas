#!/usr/bin/env python3
"""Die GEN/plan hard checks (ROOT14 10-20, owner: reduce die closure risk).  A die GEN/plan FAILS when

  C1 no_landing   a region crossing (data path between two regional clocks) has no landing ring
                  (owner CLOCK RULE 10-20 08:55: every region crossing lands in a fixed-latency mesochronous ring);
  C2 no_root      a region crossing has no clock root on one of its sides (undriven trunk / unknown region);
  W1 hop_over     a die-level wire hop (pin -> relay station -> ... -> pin) is longer than the planning reach
                  (405 um, owner DIE FLOORPLAN RULE 10-20 21:40) = no relay site within reach;
  W2 no_site      (when the plan declares relay channels / cell-row sites) a stretch of a die wire longer than the
                  reach runs with no relay/repeater site under it (e.g. across a macro wall with no channel, or a
                  relay station homed on a macro instead of a channel).

The counts go into the GEN packet (key "gen_safety") so every die review sees them.

FACTS (JSON, schema opentallas.die_gen_safety_facts.v1) -- every die GEN writes this, or an adapter builds it:
  design            s81 | qwen_compute | qwen_kv | hbm (free text accepted)
  reach_um          planning reach (default 405)
  regions           {name: {"root": <clock root name or null>}}
  crossings[]       {id, src_region, dst_region, landing: <landing inst or null>, bits?}
  wires[]           {id, pts: [[x, y], ...] (source pin, relay stations in order, destination pin), kind?: sync|fwd|reset}
  channels[]        optional relay-channel / cell-row site rectangles [x0, y0, x1, y1] (um)
  summaries[]       optional pre-counted results of an existing per-die check (adapters below):
                    {source, crossings?, no_landing?, no_root?, wires?, hops_over?, wires_over?, max_hop_um?}

ADAPTERS (combine freely with --facts; all add to one report):
  --landed-pairs F  Qwen/KV tools/die_clock/qwen_landed_pairs.py output: NEIGHBOUR + GAP + BUMP = no landing,
                    NO_ROOT = no root
  --hbm-reach F     HBM tools/hbm_die_v16/d4g_reach_check.py output: sync + fwd buses over reach
  --relay-stages F  any die_relay_stages.v1 export with span_um: span / (stages + 1) > reach (even-spacing bound)

  gen_check.py --design s81 --facts gen_safety_facts.json [--packet GEN_PACKET.json] [--out report.json]
               [--diagnostic REASON]          -> exit 1 on FAIL (0 with --diagnostic: verdict stays FAIL, labelled)
"""
import argparse
import json
import math
import sys
from pathlib import Path

SCHEMA_FACTS = 'opentallas.die_gen_safety_facts.v1'
SCHEMA = 'opentallas.die_gen_safety.v1'
REACH_UM = 405.0
SAMPLE_UM = 5.0
COUNT_KEYS = ('crossings', 'no_landing', 'no_root', 'wires', 'hops', 'hops_over', 'wires_over', 'wires_no_site')


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class _RectIndex:
    def __init__(self, rects, cell=200.0):
        self.cell, self.bins = cell, {}
        for r in rects:
            x0, y0, x1, y1 = map(float, r)
            for i in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
                for j in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                    self.bins.setdefault((i, j), []).append((x0, y0, x1, y1))

    def inside(self, x, y):
        for (x0, y0, x1, y1) in self.bins.get((int(math.floor(x / self.cell)), int(math.floor(y / self.cell))), ()):
            if x0 <= x <= x1 and y0 <= y <= y1:
                return True
        return False


def _route(a, b):
    """L-shaped Manhattan route a -> b (x first): sample points every SAMPLE_UM"""
    pts = []
    (x0, y0), (x1, y1) = a, b
    for (sx, sy), (ex, ey) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1))):
        L = abs(ex - sx) + abs(ey - sy)
        n = max(1, int(math.ceil(L / SAMPLE_UM)))
        for k in range(n + 1):
            t = k / n
            pts.append((sx + (ex - sx) * t, sy + (ey - sy) * t))
    return pts


def unsited_run(pts, idx):
    """longest stretch (um) of the wire polyline with no relay/repeater site under it.  Sites = the declared relay
    channels / cell-row rectangles and the two end pins; a relay station counts only when it sits in a channel (a
    station dropped on a macro is no site: its cells cannot be placed there)"""
    worst = run = 0.0
    last = tuple(pts[-1])
    for a, b in zip(pts, pts[1:]):
        samples = _route(a, b)
        for p, q in zip(samples, samples[1:]):
            if idx.inside(*q) or q == last:
                run = 0.0
            else:
                run += manhattan(p, q)
                worst = max(worst, run)
    return worst


def check_facts(f, reach=None, max_list=40):
    reach = float(reach or f.get('reach_um') or REACH_UM)
    regions = f.get('regions') or {}
    cnt = dict.fromkeys(COUNT_KEYS, 0)
    ex = dict(no_landing=[], no_root=[], hops_over=[], wires_no_site=[])
    max_hop = 0.0
    for c in f.get('crossings') or []:
        cnt['crossings'] += 1
        if not c.get('landing'):
            cnt['no_landing'] += 1
            if len(ex['no_landing']) < max_list:
                ex['no_landing'].append(dict(id=c.get('id'), src=c.get('src_region'), dst=c.get('dst_region'), bits=c.get('bits')))
        miss = [s for s in (c.get('src_region'), c.get('dst_region')) if not (regions.get(s) or {}).get('root')]
        if miss:
            cnt['no_root'] += 1
            if len(ex['no_root']) < max_list:
                ex['no_root'].append(dict(id=c.get('id'), regions_without_root=miss))
    idx = _RectIndex(f['channels']) if f.get('channels') else None
    for w in f.get('wires') or []:
        pts = [tuple(map(float, p)) for p in w.get('pts') or []]
        if len(pts) < 2:
            continue
        cnt['wires'] += 1
        over = []
        for k, (a, b) in enumerate(zip(pts, pts[1:])):
            cnt['hops'] += 1
            d = manhattan(a, b)
            max_hop = max(max_hop, d)
            if d > reach + 1e-6:
                over.append((k, round(d, 1)))
        if over:
            cnt['hops_over'] += len(over)
            cnt['wires_over'] += 1
            if len(ex['hops_over']) < max_list:
                ex['hops_over'].append(dict(id=w.get('id'), kind=w.get('kind'), hops=over[:6]))
        if idx is not None:
            r = unsited_run(pts, idx)
            if r > reach + 1e-6:
                cnt['wires_no_site'] += 1
                if len(ex['wires_no_site']) < max_list:
                    ex['wires_no_site'].append(dict(id=w.get('id'), unsited_um=round(r, 1)))
    srcs = []
    for s in f.get('summaries') or []:
        for k in COUNT_KEYS:
            cnt[k] += int(s.get(k) or 0)
        max_hop = max(max_hop, float(s.get('max_hop_um') or 0.0))
        srcs.append(s.get('source'))
    fails = []
    if cnt['no_landing']:
        fails.append(f"C1 {cnt['no_landing']}/{cnt['crossings']} region crossings without a landing ring")
    if cnt['no_root']:
        fails.append(f"C2 {cnt['no_root']}/{cnt['crossings']} region crossings without a clock root on a side")
    if cnt['hops_over']:
        fails.append(f"W1 {cnt['hops_over']} wire hops on {cnt['wires_over']} die wires longer than {reach:g} um "
                     f"(max {max_hop:.0f} um): no relay site within reach")
    if cnt['wires_no_site']:
        fails.append(f"W2 {cnt['wires_no_site']} die wires with a >{reach:g} um stretch over no relay/repeater site")
    if not (cnt['crossings'] or cnt['wires']):
        fails.append('EMPTY: no crossing and no wire in the facts (the GEN export is missing; never a pass)')
    landed_census = any(s.get('source') == 'qwen_landed_pairs' and 'crossings' in s
                        for s in f.get('summaries') or [])
    coverage = dict(C1='CHECKED' if 'crossings' in f or landed_census else 'NOT_EXPORTED',
                    C2='CHECKED' if ('crossings' in f and 'regions' in f) or landed_census else 'NOT_EXPORTED',
                    W1='CHECKED' if cnt['wires'] else 'NOT_EXPORTED',
                    W2='CHECKED' if idx is not None and f.get('wires') else 'NOT_EXPORTED')
    complete = all(v == 'CHECKED' for v in coverage.values())
    return dict(schema=SCHEMA, design=f.get('design'), reach_um=reach, verdict='FAIL' if fails else 'PASS',
                check_coverage=coverage, coverage_complete=complete,
                verdict_scope='FULL_GEN_SAFETY' if complete else 'SCOPED_CHECK_ONLY',
                physical_qualification_eligible=complete and not fails,
                qualification='GEN safety preconditions only; source-bound facts and native/clock/route/IR signoff remain required',
                counts=cnt, max_hop_um=round(max_hop, 1), channels_declared=bool(idx), fails=fails, examples=ex,
                regions=len(regions), regions_without_root=sorted(k for k, v in regions.items() if not (v or {}).get('root')),
                summaries=srcs)


# ---------------------------------------------------------------- adapters
def from_landed_pairs(doc):
    pc = (doc.get('summary') or {}).get('pairs') or {}
    cross = sum(int(pc.get(k, 0)) for k in ('LANDED', 'NEIGHBOUR', 'GAP', 'BUMP', 'NO_ROOT', 'RESET_ROOT'))
    return dict(source='qwen_landed_pairs', crossings=cross,
                no_landing=sum(int(pc.get(k, 0)) for k in ('NEIGHBOUR', 'GAP', 'BUMP')), no_root=int(pc.get('NO_ROOT', 0)))


def from_hbm_reach(doc):
    ob = doc.get('over_buses_by_class') or {}
    over = int(ob.get('sync', 0)) + int(ob.get('fwd', 0))
    hist = [float(r.get('span_um') or 0) for r in doc.get('worst') or doc.get('first') or [] if isinstance(r, dict)]
    return dict(source='hbm_d4g_reach_check', wires=int(doc.get('buses_checked') or 0), hops=int(doc.get('buses_checked') or 0),
                hops_over=over, wires_over=over, max_hop_um=max(hist, default=0.0))


def from_relay_stages(doc, reach):
    s = dict(source='die_relay_stages_span', wires=0, hops=0, hops_over=0, wires_over=0, max_hop_um=0.0)
    for b in doc.get('buses') or []:
        if b.get('span_um') is None:
            continue
        n = int(b.get('stages') or 0) + 1
        hop = float(b['span_um']) / n
        s['wires'] += 1; s['hops'] += n
        s['max_hop_um'] = max(s['max_hop_um'], hop)
        if hop > reach + 1e-6:
            s['wires_over'] += 1; s['hops_over'] += n
    return s


def _load(p):
    p = Path(p)
    b = p.read_bytes()
    if p.suffix == '.gz':
        import gzip
        b = gzip.decompress(b)
    return json.loads(b)


def merge_packet(packet, rep):
    p = Path(packet)
    d = json.loads(p.read_text()) if p.exists() and p.stat().st_size else {}
    d['gen_safety'] = {k: rep[k] for k in ('schema', 'verdict', 'reach_um', 'counts', 'max_hop_um', 'fails', 'channels_declared',
                                          'regions_without_root', 'summaries', 'diagnostic', 'check_coverage',
                                          'coverage_complete', 'verdict_scope', 'physical_qualification_eligible',
                                          'qualification') if k in rep}
    p.write_text(json.dumps(d, indent=1) + '\n')


def status_line(rep):
    c = rep['counts']
    return (f"DIE_GEN_SAFETY {rep['verdict']}{' (DIAGNOSTIC: ' + rep['diagnostic'] + ')' if rep.get('diagnostic') else ''} "
            f"design={rep.get('design')} reach={rep['reach_um']:g} crossings={c['crossings']} no_landing={c['no_landing']} "
            f"no_root={c['no_root']} wires={c['wires']} hops_over={c['hops_over']} wires_over={c['wires_over']} "
            f"max_hop={rep['max_hop_um']:g} no_site={c['wires_no_site']} "
            f"scope={rep['verdict_scope']} physical_qualification_eligible={int(rep['physical_qualification_eligible'])}" +
            ('' if rep['verdict'] == 'PASS' else ' | ' + ' | '.join(rep['fails'])))


def run(design=None, facts=None, landed_pairs=None, hbm_reach=None, relay_stages=None, reach=None, diagnostic=None):
    f = _load(facts) if facts else dict(schema=SCHEMA_FACTS)
    if design:
        f['design'] = design
    r = float(reach or f.get('reach_um') or REACH_UM)
    f.setdefault('summaries', [])
    if landed_pairs:
        f['summaries'].append(from_landed_pairs(_load(landed_pairs)))
    if hbm_reach:
        f['summaries'].append(from_hbm_reach(_load(hbm_reach)))
    if relay_stages:
        f['summaries'].append(from_relay_stages(_load(relay_stages), r))
    rep = check_facts(f, r)
    if diagnostic:
        rep['diagnostic'] = diagnostic
        rep['physical_qualification_eligible'] = False
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--design')
    ap.add_argument('--facts')
    ap.add_argument('--landed-pairs'); ap.add_argument('--hbm-reach'); ap.add_argument('--relay-stages')
    ap.add_argument('--reach', type=float, help=f'planning reach um (default facts reach_um, else {REACH_UM:g})')
    ap.add_argument('--out'); ap.add_argument('--packet', help='GEN packet JSON: the report goes in its "gen_safety" key')
    ap.add_argument('--diagnostic', metavar='REASON', help='diagnostic build: exit 0, verdict stays FAIL and is labelled')
    a = ap.parse_args(argv)
    if not (a.facts or a.landed_pairs or a.hbm_reach or a.relay_stages):
        ap.error('give --facts and/or an adapter input')
    rep = run(a.design, a.facts, a.landed_pairs, a.hbm_reach, a.relay_stages, a.reach, a.diagnostic)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    if a.packet:
        merge_packet(a.packet, rep)
    print(status_line(rep))
    return 0 if rep['verdict'] == 'PASS' or a.diagnostic else 1


if __name__ == '__main__':
    sys.exit(main())
