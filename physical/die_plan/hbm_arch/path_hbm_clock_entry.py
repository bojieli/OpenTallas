#!/usr/bin/env python3
"""D-HBM-B1 PLAN-DELTA (12.3 / 12.8a): plan-defined CENTRE clock entry for every HBM hard core, zero early offset.

What it changes (plan + core_conns sidecar only; no RTL, no cycles):
  1. every kind=core clock tap gets insertion_ps = the die common latency (TT) and insertion_ff_ps = the FF common
     latency: the 746 offset taps (12.8 ban: early-tap offsets) are dropped, none are re-introduced.
  2. every hard core gets exactly ONE plan clock tap at its master-plan entry (core-local centre snapped to the 4.32-um
     PG lattice = master_plan.core_entry; IP macros (ot_pdie_serdes, cannot be rebuilt) keep their native clock pin
     as entry, source IP_DECLARED).  Tap name = `<inst>.<port>` when the core has one clock port, else `<inst>`
     (one entry serving every clock pin of the rebuilt core, schema.core_taps wildcard form).  All other core taps of
     that instance are removed.  The tap xy is the entry in the type frame (orient + track_offset applied).
  3. clock_entries.json (sidecar; the plan schema stays unchanged) records the entry (core-local xy, 8.64 island rect, port, merged native clock ports,
     source) for the kit generator (12.7c / 12.8a: kits must place the clock pin exactly there).
  4. core_conns.json: every clock port of every hard core is fed from its own plan tap (`tap:<tap name>`): the
     peer-core clock relays (`core:...`, 307 port refs on 7aaba41c) are replaced (COORD 07:12 (a), 12.8a).
  5. clock.core_taps = 'early' on every type with hard cores so the die clock (S.core_taps) serves every entry; with
     all offsets 0 the keyword is legacy (no early delivery): CLOCK-128 must retarget the die tree/mesh to these
     taps (clock_taps_die.json lists them in the die frame).
Native views are NOT changed: their clock pins stay where they were built.  master_plan's native-pin check therefore
keeps FAILing every rebuilt core with "native clock pin differs from proposed entry" until the core is rebuilt on the
plan slice -- that FAIL is the rebuild list, not something to hide.
"""
import argparse, json, re, shutil
from pathlib import Path

LAT = 4.32
ISL = 8.64
RX = re.compile(r'(^|_)(clk|ck|clock)(_|$)')
IP_MODULES = {'ot_pdie_serdes'}


def snap(v, q=LAT):
    return round(round(v / q) * q, 4)


def base(n):
    return re.sub(r'\[\d+\]$', '', n)


def island(xy):
    import math
    x0 = math.floor(xy[0] / LAT) * LAT
    y0 = math.floor(xy[1] / LAT) * LAT
    if xy[0] - x0 < 1e-6:
        x0 -= LAT
    if xy[1] - y0 < 1e-6:
        y0 -= LAT
    return [round(x0, 3), round(y0, 3), round(x0 + ISL, 3), round(y0 + ISL, 3)]


def core_to_type(h, x, y):
    w, hh = h['outline_um']
    o = h.get('orient', 'R0')
    ox, oy = h['origin_um']
    dx, dy = h.get('track_offset_um', [0, 0])
    X, Y = {'R0': (x, y), 'MX': (x, hh - y), 'MY': (w - x, y), 'R180': (w - x, hh - y)}[o]
    return ox + dx + X, oy + dy + Y


def type_to_die(P, p, x, y):
    ox, oy = p['origin_um']
    w, h = P['partition_types'][p['type']]['outline_um']
    o = p.get('orient', 'R0')
    X, Y = {'R0': (x, y), 'MX': (x, h - y), 'MY': (w - x, y), 'R180': (w - x, h - y)}.get(o, (x, y))
    return ox + X, oy + Y


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--src', type=Path, required=True, help='plan bundle dir (cores/ pin tables, core_conns.json)')
    ap.add_argument('--plan', type=Path, help='die_plan.json to modify (default SRC/die_plan.json)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit('output must be new')
    P = json.loads((a.plan or a.src / 'die_plan.json').read_text())
    CC = json.loads((a.src / 'core_conns.json').read_text())
    tt = float(P['clock'].get('common_latency_ps', P['clock']['insertion_ps']))
    ff = float(P['clock'].get('insertion_ff_ps', round(0.81 * tt, 3)))
    rep = dict(common_tt_ps=tt, common_ff_ps=ff, offsets_dropped=0, taps_before=0, taps_after=0, cores=0,
               ip_cores=0, single_port=0, merged_entry=0, conns_rewired=0, conns_peer_relays_removed=0,
               mode_set_early=[], modules={}, entries={}, branch_legs=[])
    die_taps = []
    core_entries = {}
    for tn, t in P['partition_types'].items():
        ck = t.setdefault('clock', {})
        taps = ck.get('taps', []) or []
        rep['taps_before'] += sum(1 for tp in taps if tp.get('kind') == 'core')
        for tp in taps:
            if tp.get('kind') == 'core' and (abs(float(tp.get('insertion_ps', tt)) - tt) > 1e-6
                                             or abs(float(tp.get('insertion_ff_ps', ff)) - ff) > 1e-6):
                rep['offsets_dropped'] += 1
        if not t.get('hard_cores'):
            continue
        old = {tp['name']: tp for tp in taps}
        keep = [tp for tp in taps if tp.get('kind') != 'core']
        new = []
        for h in t['hard_cores']:
            rep['cores'] += 1
            inst, mod = h['inst'], h['module']
            pins = json.loads((a.src / h['pins_file']).read_text())
            pins = pins['pins'] if isinstance(pins, dict) else pins
            ports = sorted({base(p['name']) for p in pins if RX.search(base(p['name'])) and 'rst' not in p['name']})
            prev = [nm for nm in old if nm == inst or nm.startswith(inst + '.')]
            prev_ports = sorted({nm[len(inst) + 1:] for nm in prev if nm != inst})
            ports = sorted(set(ports) | {base(p) for p in prev_ports})
            if not ports:
                raise SystemExit(f'{tn}/{inst}: no clock port in {h["pins_file"]}')
            w, hh = h['outline_um']
            if mod in IP_MODULES:
                ck_pins = [p for p in pins if base(p['name']) in ports]
                if len(ck_pins) != 1:
                    raise SystemExit(f'{tn}/{inst}: IP core needs one native clock pin, has {len(ck_pins)}')
                xy = [round(ck_pins[0].get('x', (ck_pins[0].get('xy') or [0, 0])[0]), 4),
                      round(ck_pins[0].get('y', (ck_pins[0].get('xy') or [0, 0])[1]), 4)]
                src = 'IP_DECLARED native clock pin (IP cannot be rebuilt; 12.8a centre not applicable)'
                rep['ip_cores'] += 1
            else:
                xy = [snap(w / 2), snap(hh / 2)]
                src = 'master plan centre entry on the 4.32 PG lattice (12.8a, D-HBM-B1)'
            # an existing wildcard tap (`<inst>`, e.g. TKM tiles driven by plan branch buffers) keeps its name
            name = inst if (inst in old or len(ports) > 1) else f'{inst}.{ports[0]}'
            rep['single_port' if len(ports) == 1 else 'merged_entry'] += 1
            tx, ty = core_to_type(h, *xy)
            ent = dict(xy_um=xy, island_um=island(xy), port=ports[0] if len(ports) == 1 else None,
                       merged_clock_ports=ports if len(ports) > 1 else [], tap=name, source=src,
                       stack=['M9', 'M5'], latency_target_tt_ps=tt, latency_target_ff_ps=ff)
            core_entries.setdefault(tn, {})[inst] = dict(ent, module=mod)
            prevtp = old.get(name) or (old.get(prev[0]) if prev else None) or {}
            tap = dict(name=name, kind='core', xy=[round(tx, 4), round(ty, 4)], insertion_ps=tt,
                       insertion_ff_ps=ff, budget_owner=mod,
                       note=('D-HBM-B1 12.8a: plan centre clock entry (in-core pushdown island, clock_entries.json), '
                             'common latency, zero early offset; replaces '
                             f'{prev or "no plan tap"}; native view clock pin(s) {ports} NOT at the entry until the '
                             'core is rebuilt on its plan slice'))
            if prevtp.get('parent'):
                tap['parent'] = prevtp['parent']
            new.append(tap)
            rep['modules'].setdefault(mod, dict(uses=0, ports=ports, entry_um=xy, ip=mod in IP_MODULES))['uses'] += 1
            rep['entries'][mod] = dict(xy=xy, source=src)
            # core_conns: every clock port from its own plan tap
            conns = CC.setdefault(tn, {}).setdefault(inst, {})
            for p in ports:
                v = conns.get(p)
                if v and any(str(x).startswith('core:') for x in v):
                    rep['conns_peer_relays_removed'] += 1
                if v != [f'tap:{name}']:
                    rep['conns_rewired'] += 1
                conns[p] = [f'tap:{name}']
            for pv in P['partitions']:
                if pv['type'] == tn:
                    die_taps.append(dict(part=pv['name'], type=tn, tap=name, insertion_ps=tt, insertion_ff_ps=ff,
                                         xy_die_um=[round(v, 3) for v in type_to_die(P, pv, tx, ty)]))
        ck['taps'] = keep + new
        rep['taps_after'] += len(new)
        if ck.get('core_taps') != 'early':
            rep['mode_set_early'].append(tn)
        ck['core_taps'] = 'early'   # legacy keyword: every core tap served by the die clock, all offsets 0
        names = {tp['name']: tp for tp in ck['taps']}
        for b in ck.get('branch_buffers') or []:
            legs = [round(abs(names[d]['xy'][0] - b['xy'][0]) + abs(names[d]['xy'][1] - b['xy'][1]), 3)
                    for d in b.get('drives', []) if d in names]
            rep['branch_legs'].append(dict(type=tn, buffer=b['name'], legs_before=b.get('legs_um'),
                                           legs_after=legs))
            b['legs_um'] = legs
            b['note'] = (b.get('note', '') + ' | D-HBM-B1: legs re-derived to the centre entries; leg repeaters '
                         'still on the old leg -> CLOCK-128 retarget').lstrip(' |')
    P.setdefault('note', '')
    P['note'] = (str(P['note']) + ' | D-HBM-B1 clock-entry delta (path_hbm_clock_entry.py)').lstrip(' |')
    shutil.copytree(a.src, a.out, ignore=shutil.ignore_patterns('gates', 'gates-*', 'die_plan.json', 'core_conns.json',
                                                                 '*.png'))
    (a.out / 'die_plan.json').write_text(json.dumps(P, indent=1) + '\n')
    (a.out / 'core_conns.json').write_text(json.dumps(CC, indent=1) + '\n')
    (a.out / 'entries.json').write_text(json.dumps(rep['entries'], indent=1, sort_keys=True) + '\n')
    (a.out / 'clock_entries.json').write_text(json.dumps(core_entries, indent=1) + '\n')
    (a.out / 'clock_taps_die.json').write_text(json.dumps(die_taps, indent=1) + '\n')
    (a.out / 'clock_entry_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: (v if not isinstance(v, (dict, list)) else len(v)) for k, v in rep.items()}))


if __name__ == '__main__':
    main()
