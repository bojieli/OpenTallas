#!/usr/bin/env python3
"""Widen dense HBM shared E/W face windows to the default pin budget, on the TYPE declarations.

path_hbm_face6.py repacks port-level windows (canonical plans). In the batch plans (B1 and successors) the
abutting port windows resolve from the partition types' bus / ft_slot declarations, so this variant repacks
each dense shared face in die frame and writes the new window back onto every type declaration that resolves
the port (both ends where both declare it).

- Trigger: a shared E/W face whose ports exceed --trigger pins/um (the G0 default budget is 6/um).
- Every port on that shared face is repacked in its original along-face order, centred on its old centre
  where room allows, at <= --pins-per-um (default 5.5) and <= pin_track_max (schema.window_for), on the
  0.192-um grid with a 0.576-um gap and 8.64-um face margins.
- Refuses (exit 1) when a face is too short or when two instances of one type would need different windows.
- Never raises a limit, never adds a per-type face budget. Station / reset / clock rebuild is a later step
  (path_hbm_repair.py on the changed types).
"""
import argparse, collections, json, math, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / 'tools' / 'die_plan'), str(HERE)]
import schema as S

G = 0.192; GAP = 0.576; MARGIN = 8.64


def q_up(v): return math.ceil(v / G - 1e-8) * G
def q_dn(v): return math.floor(v / G + 1e-8) * G


def die_to_type(P, part, win):
    p = P.parts[part]; w, h = P.types[p['type']]['outline_um']
    a, b = win[0] - p['origin_um'][1], win[1] - p['origin_um'][1]
    if p.get('orient', 'R0') in ('MX', 'R180'):
        a, b = h - b, h - a
    return [round(a, 3), round(b, 3)]


def decl(P, raw_types, part, bus):
    """the mutable type declaration (dict, window key) that resolves bus on part, or None."""
    t = raw_types[P.parts[part]['type']]
    for b in t.get('buses', []):
        if b['name'] == bus and 'window_um' in b and 'face' in b and 'layers' in b:
            return b, 'window_um'
    for s in t.get('ft_slots', []):
        for sfx, wk in (('_i', 'in_window_um'), ('_o', 'out_window_um')):
            if bus == s['name'] + sfx and wk in s:
                return s, wk
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--src', type=Path, required=True); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--pins-per-um', type=float, default=5.5); ap.add_argument('--trigger', type=float, default=6.0)
    a = ap.parse_args()
    if a.out.exists(): raise SystemExit('output must be new')
    raw = json.loads((a.src / 'die_plan.json').read_text())
    P = S.Plan(json.loads((a.src / 'die_plan.json').read_text()), a.src / 'die_plan.json')
    groups = collections.defaultdict(list)
    for pid, pr in P.ports.items():
        if pr.get('face') not in ('E', 'W') or S.DIE_PART in (pr['src']['part'], pr['dst']['part']): continue
        groups[tuple(sorted((pr['src']['part'], pr['dst']['part'])))].append(pid)
    assign = {}; rep = {'pin_budget': a.pins_per_um, 'trigger': a.trigger, 'faces': [], 'windows': [], 'changed_types': set()}
    for ns, pids in sorted(groups.items()):
        prs = [P.ports[q] for q in pids]
        dens = [S.port_pins_count(q) / abs(q['window_um'][1] - q['window_um'][0]) for q in prs]
        if max(dens) <= a.trigger: continue
        prs.sort(key=lambda q: (sum(q['window_um']), q['id']))
        lo = max(P.rect(n)[1] for n in ns) + MARGIN; hi = min(P.rect(n)[3] for n in ns) - MARGIN
        lo, hi = q_up(lo), q_dn(hi)
        sizes = [q_up(max(abs(q['window_um'][1] - q['window_um'][0]) if S.port_pins_count(q) / abs(q['window_um'][1] - q['window_um'][0]) <= a.pins_per_um else 0,
                          S.window_for(0, S.port_pins_count(q), q['layers'], P.layers, per_um=a.pins_per_um, track_max=P.budgets['pin_track_max'])))
                 for q in prs]
        need = sum(sizes) + GAP * (len(sizes) - 1)
        if need > hi - lo + 1e-6: raise SystemExit(f'{ns}: needs {need:.3f} um, available {hi - lo:.3f} um')
        latest = []; end = hi
        for L in sizes[::-1]: latest.append(end - L); end -= L + GAP
        latest.reverse(); end = lo
        for q, L, late in zip(prs, sizes, latest):
            old = list(q['window_um']); want = sum(old) / 2 - L / 2
            begin = q_up(max(end, min(want, late)))
            if begin + L > hi + 1e-6: raise SystemExit(f'{ns}: quantized face exhausted at {q["id"]}')
            new = [round(begin, 3), round(begin + L, 3)]; end = begin + L + GAP
            n_decl = 0
            for side in ('src', 'dst'):
                part, bus = q[side]['part'], q[side]['bus']
                d = decl(P, raw['partition_types'], part, bus)
                if d is None: continue
                n_decl += 1
                tw = die_to_type(P, part, new); key = (P.parts[part]['type'], bus)
                if key in assign and assign[key][1] != tw:
                    raise SystemExit(f'type {key}: instance windows disagree {assign[key]} vs {tw} ({part})')
                assign[key] = (d, tw, part)
            if not n_decl: raise SystemExit(f'{q["id"]}: no type declaration')
            if old != new:
                rep['windows'].append({'port': q['id'], 'parts': list(ns), 'pins': S.port_pins_count(q), 'before': old, 'after': new})
        rep['faces'].append({'parts': list(ns), 'ports': len(prs), 'used_um': round(need, 3), 'available_um': round(hi - lo, 3)})
    for (tn, bus), (d, tw, part) in assign.items():
        obj, wk = d
        if obj[wk] != tw:
            obj[wk] = tw; rep['changed_types'].add(tn)
    rep['changed_types'] = sorted(rep['changed_types'])
    rep['required_next'] = 'rebuild FT/internal stations, reset and lane latency on changed_types (path_hbm_repair.py), then G0'
    shutil.copytree(a.src, a.out)
    (a.out / 'die_plan.json').write_text(json.dumps(raw, indent=1) + '\n')
    (a.out / 'face6t_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({'faces': len(rep['faces']), 'changed_ports': len(rep['windows']), 'changed_types': rep['changed_types'],
                      'max_face_use': max([f['used_um'] / f['available_um'] for f in rep['faces']] + [0])}, indent=1))


if __name__ == '__main__': main()
