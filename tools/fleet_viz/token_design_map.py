#!/usr/bin/env python3
"""Token path -> current design nodes (EXPLORER-2, 2026-11-12).

The token-path records (explorer/token/data/<design>.json, token_path_export 2026-10-20) name October elements and
instance globs; no current plan of record has those names, so their own element / instance join maps ~0 % of the token
onto today's dies.  This re-export joins each operator class to the types and hard cores of the CURRENT plans through
token_design_rules.json (one reviewable regex per class and die over node names, with its confidence and reason) and
writes, per design:

  classes  {cls: {nodes: [node ids], types, cores, signed, exported, confidence, why}}
  steps    {token node id: cls}            (every step of the record, AR and MTP)
  coverage share of token cycles whose class maps to >= 1 node, overall and by confidence; unmapped classes

    token_design_map.py [--index <state>/design_index.json] [--token-dir explorer/token/data] [--out <state>/token_design_map.json]

The cycle numbers are the record's (not re-priced): the page says so.
"""
import argparse, collections, json, os, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent
STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
SCHEMA = 'opentallas.fleet_viz.token_design_map.v1'


def rules_of(R, design):
    d = R['designs'].get(design) or {}
    return R['designs'].get(d['same_as']) if d.get('same_as') else d


def build(index, token_dir, rules):
    N = index['nodes']
    by_die = collections.defaultdict(list)
    for nid, n in N.items():
        if n['level'] in ('type', 'core'): by_die[n['die']].append(n)
    out = {}
    for f in sorted(pathlib.Path(token_dir).glob('*.json')):
        try: t = json.loads(f.read_text())
        except Exception: continue
        if not isinstance(t, dict) or 'nodes' not in t or 'classes' not in t: continue
        design = f.stem
        base = design[:-4] if design.endswith('_mtp') else design
        rd = rules_of(rules, base)
        if not rd: continue
        cyc = collections.Counter()
        for n in t['nodes']: cyc[n.get('cls')] += n.get('cycles') or 0
        tot = sum(cyc.values()) or 1
        classes = {}
        for c in t['classes']:
            cid = c['id']; r = (rd.get('classes') or {}).get(cid) or {}
            hit = []
            for die, rx in r.get('rules') or []:
                pat = re.compile(rx)
                hit += [n for n in by_die.get(die, []) if pat.match(n['name'])]
            hit = sorted({n['id']: n for n in hit}.values(), key=lambda n: (n['level'] != 'type', n['id']))
            classes[cid] = dict(label=c.get('label'), nodes=[n['id'] for n in hit], types=sum(1 for n in hit if n['level'] == 'type'),
                                cores=sum(1 for n in hit if n['level'] == 'core'), signed=sum(1 for n in hit if n['status']['state'] == 'signed'),
                                exported=sum(1 for n in hit if (n.get('layout') or {}).get('store')),
                                confidence=r.get('confidence') or 'none', why=r.get('why') or 'no rule for this class',
                                cycle_share=round(cyc[cid] / tot, 4))
        mapped = sum(cyc[k] for k, v in classes.items() if v['nodes'])
        byconf = collections.Counter()
        for k, v in classes.items():
            if v['nodes']: byconf[v['confidence']] += cyc[k]
        out[design] = dict(design=design, record=str(f.name), record_tool=t.get('tool'), record_head=t.get('repo_head'), dies=rd.get('dies'),
                           classes=classes, steps={n['id']: n.get('cls') for n in t['nodes']},
                           coverage=dict(mapped=round(mapped / tot, 4), **{k: round(v / tot, 4) for k, v in byconf.items()}),
                           unmapped=[k for k, v in classes.items() if not v['nodes']])
    return dict(schema=SCHEMA, generated=time.time(), index_generated=index.get('generated'), designs=out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--index', default=str(STATE / 'design_index.json'))
    ap.add_argument('--token-dir', default=str(HERE / 'explorer' / 'token' / 'data'))
    ap.add_argument('--rules', default=str(HERE / 'token_design_rules.json'))
    ap.add_argument('--out', default=str(STATE / 'token_design_map.json'))
    a = ap.parse_args()
    res = build(json.loads(pathlib.Path(a.index).read_text()), a.token_dir, json.loads(pathlib.Path(a.rules).read_text()))
    tmp = pathlib.Path(a.out + '.tmp'); tmp.write_text(json.dumps(res, separators=(',', ':'))); os.replace(tmp, a.out)
    for d, v in res['designs'].items():
        print('%-16s mapped %5.1f %% of token cycles (%s); unmapped classes: %s' % (
            d, 100 * v['coverage']['mapped'], ', '.join('%s %.1f %%' % (k, 100 * x) for k, x in v['coverage'].items() if k != 'mapped'), ', '.join(v['unmapped']) or '-'))


if __name__ == '__main__':
    sys.exit(main())
