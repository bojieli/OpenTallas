"""S81-RATE3 (10-20): compose the S81 DS ROM rate from the COMPILED die field calendars (xs_field_calendar die, real
p4l-MU topology) on top of the CALPIPE scenario (tools/toksim_s81_compose.py --scenario calpipe).

usage (repo root): python3 results/rtl/s81_rate3_1020/compose_rate3.py CAL_DIR OUT_DIR
  CAL_DIR/<case>/die_field_calendar.json for case in legacy_s0 (8 owners everywhere, the old compile), topo_s0
  (OT_XS_TOPO=1, physical frames per slice), prop2_s0 (TOPO + OT_XS_PROP=1 + the measured down / gu tails: free-ownership ops dealt in proportion to the
  frames).  Every op value is a compiled span (== RTL go-sequence span, CALPIPE/ROM12 benches) plus the record's own
  unchanged wire / CAP adder:
    wq_b   record 1987 (first capture origin)  -> compiled span (spine go0 origin, conservative; ROM12 convention)
    wo_b   901 = 701 + 200        wo_a 3531 = 2893 + 638      router 1419 = 1269 + 150
    experts_gu 3680 (span, same origin)        down 3084 = 2889 + 195
  Options on top (separately reported, each with its qualification):
    F8  window_load issued at the job CFG (own row ready), not after q_rope: the lower_svc compiled frame order (CFG,
        OWN_ROW, WIN_LOAD, ATTN_Q.., GO = max(q, WIN_LOAD + W_SLACK 560)) -- dense layers only (sparse window_load
        waits for idx.topk_final); DAG edge q_rope -> window_load removed, window_load = W_SLACK 560 (> measured 532)
    RTAG BF label queue (claude/s81-rtag-1020 0cdf5107a): BF period 231 -> 130, span (n-1) 130 + tail (wo_a 352,
        router 345, measured r160 P130)   -- RTL in the closed BF front: needs re-closure
    TOPK INDEXED13 / HQ quarter + TAIL_FINAL 276: attn.idx.topk_final 6698 -> 669 on every indexed layer
        (claude/s81-ratefix-topk-1019 f05a86644 run_t276)  -- RTL: quarter not yet closed / bound
"""
import hashlib, importlib.util, json, sys
from pathlib import Path

R = Path.cwd()
spec = importlib.util.spec_from_file_location('tc', R / 'tools/toksim_s81_compose.py')
tc = importlib.util.module_from_spec(spec); spec.loader.exec_module(tc)
CAL, O = Path(sys.argv[1]), Path(sys.argv[2])
O.mkdir(parents=True, exist_ok=False)
ADD = {'attn.wo_b': 200, 'attn.wo_a': 638, 'ffn.router': 150, 'ffn.experts_gu': 0, 'ffn.down': 195, 'attn.wq_b': 0}
OLD = {'attn.wo_b': 901, 'attn.wo_a': 3531, 'ffn.router': 1419, 'ffn.experts_gu': 3680, 'ffn.down': 3084, 'attn.wq_b': 1987}
TAIL130 = {'attn.wo_a': 352, 'ffn.router': 345}
W_SLACK = 560


def cal(case):
    d = json.loads((CAL / case / 'die_field_calendar.json').read_text())
    L0, L2 = d['layers']['L0']['ops'], d['layers']['L2']['ops']
    for op in ADD:
        assert (L0[op]['nphases'], L0[op]['predicted_span']) == (L2[op]['nphases'], L2[op]['predicted_span']), (case, op)
    return {op: dict(n=L0[op]['nphases'], P=L0[op]['period'], span=L0[op]['predicted_span']) for op in ADD}, d


def values(c, rtag):
    v = {}
    for op in ADD:
        span = c[op]['span']
        if rtag and op in TAIL130:
            span = (c[op]['n'] - 1) * 130 + TAIL130[op]
        v[op] = span + ADD[op]
    return v


orig_nc, orig_dags = tc.node_cycles, dict(tc.DAGS)


def dag_f8(wl, p):
    d = json.loads(p.read_text())
    N = {n['id']: n for n in d['nodes']}
    pred = {}
    for e in d['edges']:
        pred.setdefault(e['dst'], []).append(e['src'])
    cut = set()
    for n in d['nodes']:
        if n.get('op') == 'attn.window_load' and not any(N[s].get('op') == 'attn.idx.topk_final' for s in pred.get(n['id'], [])):
            for s in pred.get(n['id'], []):
                if N[s].get('op') == 'attn.q_rope':
                    cut.add((s, n['id']))
            n['critical'] = False      # re-solved: the fixed critical sum must not keep the hidden load
    add = []
    for (s, t) in cut:   # q_rope must still precede every consumer of the window (scores): keep it as a direct edge
        for x in [e['dst'] for e in d['edges'] if e['src'] == t]:
            if not any(e['src'] == s and e['dst'] == x for e in d['edges']):
                add.append(dict(src=s, dst=x, bytes=None, link='rate3 F8: q_rope -> window consumer (was via window_load)',
                                cycles=0, critical=False))
    d['edges'] = [e for e in d['edges'] if (e['src'], e['dst']) not in cut] + add
    q = O / 'dag_f8' / p.name
    q.parent.mkdir(exist_ok=True)
    q.write_text(json.dumps(d) + '\n')
    return q, len(cut)


def run(name, case, rtag=False, topk=False, f8=False):
    c, raw = cal(case)
    v = values(c, rtag)
    hits = {}

    def nc(n, ov):
        cyc, how = orig_nc(n, ov)
        op = n.get('op')
        if cyc is not None and op in v and abs(cyc - OLD[op]) < 0.01:
            hits[op] = hits.get(op, 0) + 1
            return float(v[op]), how
        if topk and cyc is not None and op == 'attn.idx.topk_final' and abs(cyc - 6698) < 0.01:
            hits[op] = hits.get(op, 0) + 1
            return 669.0, how
        if f8 and op == 'attn.window_load' and cyc is not None and abs(cyc - 532) < 0.01:
            hits['window_load_wslack'] = hits.get('window_load_wslack', 0) + 1
            return float(W_SLACK), how
        return cyc, how
    tc.node_cycles = nc
    cuts = {}
    if f8:
        tc.DAGS = {}
        for wl, p in orig_dags.items():
            q, k = dag_f8(wl, p)
            tc.DAGS[wl] = q
            cuts[wl] = k
    try:
        r = tc.build(tc.OUT / 'elements', 'calpipe')
    finally:
        tc.node_cycles, tc.DAGS = orig_nc, dict(orig_dags)
    r['rate3'] = dict(case=case, compile_env=raw.get('env'), op_values=v, compiled={o: c[o] for o in c}, substitutions=hits,
                      rtag=rtag, topk=topk, f8=f8, f8_cut_edges=cuts)
    (O / (name + '.json')).write_text(json.dumps(r, indent=1) + '\n')
    s = {wl: {k: r['workloads'][wl][k] for k in ('T_cycles', 'T_cycles_fixed', 'T_cycles_solved', 'tok_s')} for wl in ('ar', 'mtp')}
    s['mu'] = {wl: {k: r['multi_user'][wl][k] for k in ('users', 'aggregate_tok_s', 'per_user_tok_s')} for wl in r['multi_user']}
    s['substitutions'] = hits
    s['op_values'] = v
    print('COMPOSE_RATE3', name, s['ar']['tok_s'], s['mtp']['tok_s'], hits, flush=True)
    return s


CASES = [('calpipe_ref', None, {}),                     # the existing CALPIPE scenario (no substitution)
         ('legacy8_compiled', 'legacy_s0', {}),          # old 8-owner compile (= ROM12 'CALPIPE + GU' + 8-phase wq_b)
         ('topo_compiled', 'topo_s0', {}),               # physical frames per slice, heads fixed
         ('prop_compiled', 'prop2_s0', {}),              # + proportional ownership (wo_b / down / wo_a groups)
         ('prop_f8', 'prop2_s0', dict(f8=True)),          # + window_load at CFG (compiled lower_svc order)
         ('prop_f8_rtag', 'prop2_s0', dict(f8=True, rtag=True)),
         ('prop_f8_topk', 'prop2_s0', dict(f8=True, topk=True)),
         ('prop_f8_rtag_topk', 'prop2_s0', dict(f8=True, rtag=True, topk=True)),
         ('topo_f8_rtag_topk', 'topo_s0', dict(f8=True, rtag=True, topk=True))]
summary = {}
for name, case, kw in CASES:
    if case is None:
        r = tc.build(tc.OUT / 'elements', 'calpipe')
        summary[name] = {wl: {k: r['workloads'][wl][k] for k in ('T_cycles', 'tok_s')} for wl in ('ar', 'mtp')}
        print('COMPOSE_RATE3', name, summary[name]['ar']['tok_s'], summary[name]['mtp']['tok_s'], flush=True)
        continue
    if not (CAL / case / 'die_field_calendar.json').exists():
        print('COMPOSE_RATE3_SKIP', name, case); continue
    summary[name] = run(name, case, **kw)
(O / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
files = [R / 'tools/toksim_s81_compose.py', tc.BASE, *orig_dags.values(), *(tc.OUT / 'elements').glob('*.json'),
         *(tc.OUT / 'scenarios/calpipe').glob('*.json'), *CAL.glob('*/die_field_calendar.json')]
(O / 'input_sources.json').write_text(json.dumps({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=1) + '\n')
