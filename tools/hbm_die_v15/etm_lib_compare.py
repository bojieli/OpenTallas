#!/usr/bin/env python3
"""Compare two ETM liberty models arc by arc (HBM-IDXETM 2026-10-18: hierarchical vs flat SYNTH ETM check).

    etm_lib_compare.py REF.lib TEST.lib [--abs PS] [--rel FRAC] [--json OUT]

Per pin: direction, clock flag, capacitance; per timing() group keyed (pin, related_pin, timing_type, timing_sense):
every table (cell_rise/fall, rise/fall_transition, rise/fall_constraint) value-by-value.  A value matches when
|ref - test| <= max(--abs, --rel * |ref|) (default 5 ps / 3 %).  PASS = identical pin set, identical arc key set,
every table value matching and input capacitance within 5 %.  Prints OT_ETM_COMPARE PASS|FAIL + the worst entries.
"""
import argparse, json, re, sys

TOK = re.compile(r'"(?:[^"\\]|\\.)*"|[{}();:,]|[^\s{}();:,"]+')


def parse(path):
    toks = TOK.findall(re.sub(r'/\*.*?\*/', '', open(path).read(), flags=re.S))
    i = 0

    def group():
        nonlocal i
        node = dict(attrs={}, groups=[])
        while i < len(toks):
            t = toks[i]
            if t == '}':
                i += 1
                return node
            name = t
            i += 1
            if toks[i] == ':':                         # simple attribute
                i += 1
                v = []
                while toks[i] != ';':
                    v.append(toks[i]); i += 1
                i += 1
                node['attrs'][name] = ' '.join(v).strip('"')
            elif toks[i] == '(':                       # group or complex attribute
                i += 1
                args = []
                while toks[i] != ')':
                    if toks[i] != ',':
                        args.append(toks[i].strip('"'))
                    i += 1
                i += 1
                if i < len(toks) and toks[i] == '{':
                    i += 1
                    g = group()
                    g['type'] = name; g['args'] = args
                    node['groups'].append(g)
                else:
                    if i < len(toks) and toks[i] == ';':
                        i += 1
                    cur = node['attrs'].get(name)
                    node['attrs'][name] = (cur if isinstance(cur, list) else []) + [args]
            else:
                i += 1
        return node
    root = group()
    return root['groups'][0]


def model(path):
    lib = parse(path)
    cells = [g for g in lib['groups'] if g['type'] == 'cell']
    if len(cells) != 1:
        sys.exit(f'{path}: expected one cell, got {len(cells)}')
    pins, arcs = {}, {}

    def pins_of(g):
        for p in g['groups']:
            if p['type'] == 'pin':
                yield p
            elif p['type'] == 'bus':
                yield from pins_of(p)
    for p in pins_of(cells[0]):
        n = p['args'][0]
        a = p['attrs']
        pins[n] = dict(direction=a.get('direction'), clock=a.get('clock') == 'true',
                       cap=float(a['capacitance']) if 'capacitance' in a else None)
        for t in p['groups']:
            if t['type'] != 'timing':
                continue
            ta = t['attrs']
            key = (n, ta.get('related_pin', ''), ta.get('timing_type', 'combinational'), ta.get('timing_sense', ''))
            tabs = {}
            for tb in t['groups']:
                vals = tb['attrs'].get('values', [])
                nums = [float(x) for row in vals for s in row for x in s.split(',') if x.strip()]
                tabs[tb['type']] = nums
            arcs[key] = tabs
    return cells[0]['args'][0], pins, arcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref'); ap.add_argument('test')
    ap.add_argument('--abs', type=float, default=5.0); ap.add_argument('--rel', type=float, default=0.03)
    ap.add_argument('--json')
    a = ap.parse_args()
    rc, rp, ra = model(a.ref)
    tc, tp, ta = model(a.test)
    out = dict(ref=a.ref, test=a.test, ref_cell=rc, test_cell=tc, pins=len(rp), arcs_ref=len(ra), arcs_test=len(ta))
    out['pins_only_ref'] = sorted(set(rp) - set(tp))[:20]
    out['pins_only_test'] = sorted(set(tp) - set(rp))[:20]
    out['arcs_only_ref'] = [list(k) for k in sorted(set(ra) - set(ta))][:20]
    out['arcs_only_test'] = [list(k) for k in sorted(set(ta) - set(ra))][:20]
    out['n_arcs_only_ref'] = len(set(ra) - set(ta)); out['n_arcs_only_test'] = len(set(ta) - set(ra))
    attr_bad = []
    for n in set(rp) & set(tp):
        r, t = rp[n], tp[n]
        if r['direction'] != t['direction'] or r['clock'] != t['clock']:
            attr_bad.append([n, 'dir/clock', r, t])
        elif r['direction'] == 'input' and r['cap'] and t['cap'] is not None and abs(r['cap'] - t['cap']) > 0.05 * r['cap'] + 1e-4:
            attr_bad.append([n, 'cap', r['cap'], t['cap']])
    out['pin_attr_mismatch'] = len(attr_bad); out['pin_attr_examples'] = attr_bad[:10]
    worst, bad, nval = [], 0, 0
    for k in set(ra) & set(ta):
        for tb, rv in ra[k].items():
            tv = ta[k].get(tb)
            if tv is None or len(tv) != len(rv):
                bad += 1; worst.append((1e9, list(k), tb, rv[:3], (tv or [])[:3])); continue
            for x, y in zip(rv, tv):
                nval += 1
                d = abs(x - y)
                if d > max(a.abs, a.rel * abs(x)):
                    bad += 1
                worst.append((d, list(k), tb, x, y))
    worst.sort(key=lambda w: -w[0])
    out['values_compared'] = nval; out['values_mismatch'] = bad
    out['max_abs_diff_ps'] = worst[0][0] if worst else 0.0
    out['worst'] = [dict(diff=w[0], arc=w[1], table=w[2], ref=w[3], test=w[4]) for w in worst[:15]]
    ok = (not out['n_arcs_only_ref'] and not out['n_arcs_only_test'] and not out['pins_only_ref']
          and not out['pins_only_test'] and not bad and not attr_bad)
    out['verdict'] = 'PASS' if ok else 'FAIL'
    if a.json:
        json.dump(out, open(a.json, 'w'), indent=1)
    print(f"OT_ETM_COMPARE {out['verdict']} pins={len(rp)} arcs={len(ra)}/{len(ta)} only_ref={out['n_arcs_only_ref']} "
          f"only_test={out['n_arcs_only_test']} values={nval} mismatch={bad} max_abs={out['max_abs_diff_ps']:.3f} "
          f"pin_attr_mismatch={len(attr_bad)}")
    for w in out['worst'][:5]:
        print('  worst', json.dumps(w))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
