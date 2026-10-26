"""TOK-QK-PRICE 2026-10-26: price D-QC-FE-REACH stations (a) and PROVISIONAL landed clock-region crossings (b) in the QC
static-schedule ledger (base: claude/tok-qk-qce-1026@1121cb654, v7 re-derived = 296,341 cyc/token).

    python3 price.py prep [TREE_JSON]   -> part_taps.json (from the CLOCK-MESH QC tree, if given), regions_*.json, add_*.json,
                                           cases.json (rederive_edges_ext.py args per case)
    python3 price.py rederive           -> out/edges_<case>_rederived.json + out/rederive_<case>.txt for every case
    (compose: run_compose.sh on the QCE compose tree -> compose/q_<case>.json)
    python3 price.py report             -> result.json

(a) FE-REACH: per-lane added cycles = the generator latency table (claude/path-qc-fereach-1026@87bdf5071
    physical/die_plan/qwen_compute/fe_reach_report.json lane_rows; n = ceil(L/(405-12)) - 1 - core FIRM stations, one
    value per port role over slw/sle) -> fe_reach_lane_rows.json here.  The added cycles go on the bind lane that lands on
    the FE in-bus (generator rule 'lanes landing on the bus get fixed_cycles += n'), i.e. landed_stages += n, and every
    10-20 ledger law that reads that lane picks it up (pass st/ch/sc, dv hops, L9).
(b) landed crossings (COORD 01:22 ruling (1)): a bind lane whose source and sink partitions lie in different clock regions
    (root + level-1 + level-2 H-tree split lines) gets one landing = E + 1 = K + 1 edges with K = 2 (10-18 landed-parent
    standard tools/landed_parent/specs: 'E = K = 3 (+4 edges per landing, was +3)', short crossings K = 2 -> +3).
    Region of a partition = region of the centroid of its clock taps (CLOCK-MESH QC tree, plan 2dd204af).
    Two split-line sets: 'lit' = the current QC H-tree splits (x 7804.08 / 15608.16 / 23412.24, y 13132.8); 'aln' = the
    same tree with every split moved to the nearest slice-column / slice-row-vs-top-cluster-row boundary (no slice or
    cluster cut).  CLOCK-MESH-2 has not posted a crossing list: both are PROVISIONAL candidate sets.
"""
import gzip, hashlib, json, re, subprocess, sys
from bisect import bisect
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BG_PATH = HERE.parent / 'bus_groups_v7.json.gz'
K_LAND = 3
W, H = 31216.32, 26265.6


def col(p):
    m = re.match(r'^(?:sl|c)_([EW])(\d)_', p)
    if not m:
        return None
    return 5 - int(m.group(2)) if m.group(1) == 'W' else 6 + int(m.group(2))


def prep(tree=None):
    if tree:
        t = json.loads(Path(tree).read_text())
        P = defaultdict(list)
        for tp in t['taps']:
            P[tp['part']].append(tp['xy'])
        pt = dict(source=f'{tree} (sha256 {hashlib.sha256(Path(tree).read_bytes()).hexdigest()[:16]}; CLOCK-MESH QC tree, '
                         'plan 2dd204af, claude/clock-mesh-2355@fdb5b851c7)',
                  root=t['nodes']['0']['region'], parts={})
        for p, v in sorted(P.items()):
            xs, ys = [a for a, _ in v], [b for _, b in v]
            pt['parts'][p] = dict(n=len(v), cx=round(sum(xs) / len(v), 3), cy=round(sum(ys) / len(v), 3),
                                  x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys))
        (HERE / 'part_taps.json').write_text(json.dumps(pt, indent=0) + '\n')
    pt = json.loads((HERE / 'part_taps.json').read_text())['parts']
    BG = json.load(gzip.open(BG_PATH))
    lanes = {}
    for g in BG['landing']:
        for m in g['members']:
            lanes.setdefault(m['lane'], (g['src_part'], g['sink_part']))
    # aligned split lines: x between slice/cluster columns 2|3, 5|6, 8|9; y between the slice row and the top cluster row
    cx = defaultdict(lambda: [1e9, -1e9])
    for p, v in pt.items():
        c = col(p)
        if c is not None:
            cx[c][0] = min(cx[c][0], v['x0']); cx[c][1] = max(cx[c][1], v['x1'])
    xa = [round((cx[a][1] + cx[a + 1][0]) / 2, 2) for a in (2, 5, 8)]
    sl_top = max(v['y1'] for p, v in pt.items() if p.startswith('sl_'))
    ct_bot = min(v['y0'] for p, v in pt.items() if re.match(r'^c_[EW]\d_t', p))
    ya = round((sl_top + ct_bot) / 2, 2)
    SPL = dict(lit=dict(x=[W / 4, W / 2, 3 * W / 4], y=H / 2), aln=dict(x=xa, y=ya))
    fe = json.loads((HERE / 'fe_reach_lane_rows.json').read_text())
    add_fe = {r['lane']: r['added'] for r in fe['lane_rows']}
    cases = {}
    for v, s in SPL.items():
        def reg(p):
            q = pt[p]
            return (bisect(s['x'], q['cx']), int(q['cy'] >= s['y']))
        cross, cls = {}, Counter()
        for l, (a, b) in lanes.items():
            ra, rb = reg(a), reg(b)
            if ra != rb:
                lvl = 'root' if (ra[0] < 2) != (rb[0] < 2) else ('L1' if ra[1] != rb[1] else 'L2')
                cross[l] = dict(src=a, sink=b, level=lvl)
                ptype = lambda p: re.sub(r'^c_[EW]\d_(\w\w)_\d+', r'c_\1', re.sub(r'^sl_[EW]\d_', 'sl_', p))
                cls[f'{ptype(a)}->{ptype(b)} {lvl}'] += 1
        # CB16 path (x-in hc -> cluster, cluster fabric a/b, rs cluster -> st_a): + K per crossed class on the worst cluster
        per_cl = defaultdict(lambda: dict(xin=0, fab=0, rs=0))
        for l, c in cross.items():
            a, b = c['src'], c['sink']
            if a.startswith('sl_') and re.match(r'sl_[EW]\d_hc\d$', a) and b.startswith('c_'):
                per_cl[b[:4]]['xin'] = 1
            elif a.startswith('c_') and b.startswith('c_'):
                per_cl[a[:4]]['fab'] = min(2, per_cl[a[:4]]['fab'] + 1)
            elif a.startswith('c_') and b.startswith('sl_'):
                per_cl[a[:4]]['rs'] = 1
        cb_add = K_LAND * max([sum(d.values()) for d in per_cl.values()] or [0])
        # inter-slice lanes (sl_<S> -> sl_<S'>, S != S') are priced per crossed hop (--hop-add), not through the 11 x max
        # hop law; the L9 pair word pays one landing if its fe -> neighbour fw lane crosses (--l9-add)
        hop_x = {l for l, c in cross.items() if c['src'].startswith('sl_') and c['sink'].startswith('sl_')
                 and col(c['src']) != col(c['sink'])}
        hops_crossed = sorted({tuple(sorted((col(cross[l]['src']), col(cross[l]['sink'])))) for l in hop_x})
        hop_add = K_LAND * len(hops_crossed)
        l9_add = K_LAND if any('__l9_' in l for l in hop_x) else 0
        add_cl = {l: K_LAND for l in cross if l not in hop_x}
        add_both = dict(add_fe)
        for l, k in add_cl.items():
            add_both[l] = add_both.get(l, 0) + k
        (HERE / f'regions_{v}.json').write_text(json.dumps(dict(
            splits=s, k_land=K_LAND, rule='lane crosses if src/sink tap-centroid regions differ', crossings=len(cross),
            by_class=dict(cls.most_common()), cb16_per_slicecol=per_cl, cb16_add=cb_add, hops_crossed=hops_crossed,
            hop_add=hop_add, l9_add=l9_add, lanes=cross), indent=1) + '\n')
        (HERE / f'add_cl_{v}.json').write_text(json.dumps(add_cl, indent=0) + '\n')
        (HERE / f'add_fecl_{v}.json').write_text(json.dumps(add_both, indent=0) + '\n')
        x = ['--cb-add', str(cb_add), '--hop-add', str(hop_add), '--l9-add', str(l9_add)]
        cases[f'v7cl_{v}'] = ['--add', f'add_cl_{v}.json', '--hop-ext', '--l9-stb', *x]
        cases[f'v7fecl_{v}'] = ['--add', f'add_fecl_{v}.json', '--hop-ext', '--l9-stb', *x]
        print(v, s, 'crossings', len(cross), 'cb_add', cb_add, 'hops', hops_crossed, 'hop_add', hop_add, 'l9_add', l9_add)
    (HERE / 'add_fe.json').write_text(json.dumps(add_fe, indent=0) + '\n')
    cases['v7ctl'] = []                                              # must reproduce ../edges_v7_rederived.json
    cases['v7ctl_ext'] = ['--hop-ext', '--l9-stb']                   # extensions alone (no added cycles): must be equal too
    cases['v7fe'] = ['--add', 'add_fe.json', '--hop-ext', '--l9-stb']
    cases['v7fe_lawhop'] = ['--add', 'add_fe.json']                  # 10-20 hop/L9 port sets only (lower bound)
    (HERE / 'cases.json').write_text(json.dumps(cases, indent=1) + '\n')


def rederive():
    cases = json.loads((HERE / 'cases.json').read_text())
    for c, args in cases.items():
        args = [HERE / a if a.endswith('.json') else a for a in args]
        r = subprocess.run([sys.executable, str(HERE / 'rederive_edges_ext.py'), str(BG_PATH), c, *map(str, args)],
                           capture_output=True, text=True, cwd=HERE)
        if r.returncode:
            raise SystemExit(f'{c}: {r.stderr[-1500:]}')
        print(c, r.stdout.strip().splitlines()[-1])


if __name__ == '__main__' and sys.argv[1] != 'report':
    {'prep': lambda: prep(sys.argv[2] if len(sys.argv) > 2 else None), 'rederive': rederive}[sys.argv[1]]()


def report():
    """result.json: compose results (compose/q_<case>.json, toksim_compose via ../compose_edges.py on intel2) + per-edge
    deltas vs the control (cycles x boundaries per layer, x 36 layers on the chained critical path)."""
    q = {c: json.loads((HERE / 'compose' / f'q_{c}.json').read_text())['result']['1u'] for c in json.loads((HERE / 'cases.json').read_text())}
    E = {c: {e['rederive_key']: e['cycles'] * len(e['at']) for e in json.loads((HERE / 'out' / f'edges_{c}_rederived.json').read_text())} for c in q}
    base = q['v7ctl']['cycles_per_token']
    res = dict(schema='opentallas.token_pass.qc_price_delta.v1', base='claude/tok-qk-qce-1026@1121cb654 v7 re-derived (law)',
               base_cycles_per_token=base, cases={})
    for c, d in q.items():
        res['cases'][c] = dict(args=json.loads((HERE / 'cases.json').read_text())[c], cycles_per_token=d['cycles_per_token'],
                               tok_s=d['tok_s'], chained_per_layer=d['layer']['chained'], l0_cold=d['layer']['l0_cold'],
                               delta_cycles_per_token=d['cycles_per_token'] - base,
                               delta_pct_cycles=round(100 * (d['cycles_per_token'] / base - 1), 3),
                               e2e_loss_pct=round(100 * (1 - base / d['cycles_per_token']), 3),
                               edge_delta_per_layer={k: v - E['v7ctl'][k] for k, v in E[c].items() if v != E['v7ctl'][k]})
    (HERE / 'result.json').write_text(json.dumps(res, indent=1) + '\n')
    for c, d in res['cases'].items():
        print(c, d['cycles_per_token'], d['tok_s'], d['delta_cycles_per_token'], d['e2e_loss_pct'], d['edge_delta_per_layer'])


if __name__ == '__main__' and sys.argv[1] == 'report':
    report()
