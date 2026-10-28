#!/usr/bin/env python3
"""DIE-HBM-3 region3 (12.14b ESTIMATE only, no build): throughput-weighted region proposer + count-aligned crossing
score (MESO-COUNT-2 count_align_plan @0af33ccde0) + TOK price with and without latency hiding.

  region3_tok.py sens  SRC PDIR OUT/sens.json                      lane weight = ds_ar cycles per landing cycle
  region3_tok.py maps  SRC PDIR SENS OUTDIR                        throughput-weighted proposals (span 3.0/3.5/4.0)
  region3_tok.py score SRC PLAN V OUTDIR TAG=MAP [TAG=MAP ...]     locality.run_v3 single-map score (fish/spt feeds)
  region3_tok.py price SRC PDIR OUT.json TAG=crossings.tsv ...     ds_ar / qwen_ar tok/s, modes nohide / hide / ideal

Model notes (all model numbers UNCHECKED):
 * lane weight: +6 cycles on one lane -> b1_lane_traversal.op_deltas -> per-op added cycles; x the ds_ar S2 schedule
   sensitivity of that op (one schedule run per op at +6 cycles/record) -> ds_ar cycles per landing cycle on the lane.
 * proposer: locality.propose (greedy heaviest-pair merge, span cap, no foreign centre) on a traffic matrix whose pair
   weight = bits + LAMBDA x (sum of lane weights of the pair's ports, in bit-equivalents): the critical record chains
   (HC, COLL, SM) merge first and stay inside regions; locality.propose_tree then makes the crossing graph a near-tree.
 * price 'nohide' = DIE-HBM-2 price_landing k1 (every crossing adds K+1 to its lane; the op pays it as unit occupancy).
   'hide' = the same added cycles as PIPELINE LATENCY: the record's result (and wait bits / RAW dependents) sees it,
   but the unit is free for its next record at start + own cycles (overlapped records / records in flight; the ring
   is registers).  'hide_sx' = 'hide' in the SX schedule (dispatch skip-ahead: a held record blocks only later records with a
   region hazard or of its own unit = deeper prefetch / more records in flight), delta vs the SX base.
   'ideal' = 0 (fully hidden).
"""
import collections, copy, csv, importlib.util, inspect, json, math, sys, types
from pathlib import Path

CLK = 1.2e9
U3F = CLK / 1905.97
FAILPH = 8
DLT = 6


def setup(SRC):
    sys.path[:0] = [SRC + '/tools', SRC + '/tools/die_plan', SRC + '/tools/throughput', SRC + '/src',
                    SRC + '/tools/hbm_b2', SRC + '/tools/s81_head']
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('count_align_plan', here / 'src' / 'count_align_plan.py')
    cap = importlib.util.module_from_spec(spec); spec.loader.exec_module(cap)
    sys.modules['count_align_plan'] = cap      # MESO-COUNT-2 ring math (+ main DSU shim) before locality imports it


def load_T(SRC):
    spec = importlib.util.spec_from_file_location('T', SRC + '/tools/hbm_b2/b1_lane_traversal.py')
    T = importlib.util.module_from_spec(spec); sa = sys.argv; sys.argv = ['x']; spec.loader.exec_module(T); sys.argv = sa
    return T


def patch_schedule():
    """timing.schedule with an optional 4th cost element xl = pipeline latency (seen by dependents, not occupancy)."""
    import accepted_cost as A
    sys.path.insert(0, str(A.TOOLS))
    A.hbm_schedule('ds')                      # imports hgi_sim the way the price chain does
    from hgi_sim import timing as TM
    if getattr(TM, '_r3', False):
        return
    s = inspect.getsource(TM.schedule)
    a = "        c = costs[i][0]\n"
    b = "        c = costs[i][0]\n        xl = costs[i][3] if len(costs[i]) > 3 else 0.0\n"
    c0 = "        if mode not in (\"S0\", \"S1\"):\n            ret_w[u] = wire_of(r) if wires else 0.0\n"
    c1 = "        end[i] += xl\n" + c0
    d0 = "        last_end_unit[u] = end[i]\n"
    d1 = "        last_end_unit[u] = end[i] - xl\n"
    for x in (a, c0, d0):
        assert s.count(x) == 1, x
    s = s.replace(a, b).replace(c0, c1).replace(d0, d1)
    ns = {}
    exec(compile(s, TM.__file__ + ':r3', 'exec'), TM.__dict__, ns)
    TM.schedule = ns['schedule']; TM._r3 = True


def schedules(A, hide):
    """{wl: (run(extra, hide) , count, base)} on the hbm S2 schedule (copy of accepted_cost.hbm_schedule.run)."""
    out = {}
    for wl, name in A.DESIGNS['r25gq']['workloads'].items():
        run0, count = A.hbm_schedule(name)
        cells = run0.__closure__
        env = {n: c.cell_contents for n, c in zip(run0.__code__.co_freevars, cells)}
        recs, pos, cf, fmt, T = env['recs'], env['pos'], env['cf'], env.get('fmt'), env['T']

        def run(extra=(), lat=False, mode="S2", recs=recs, pos=pos, cf=cf, fmt=fmt, T=T):
            def g(r, dyn, L):
                c = cf(r, dyn, L)
                name = f"{r.unit}.{r.op}"
                x = sum(d for o, fm, d in extra if A.op_match(name, o) and A.fmt_match(r, fm))
                return (c[0], c[1], c[2], x) if lat else (c[0] + x, c[1], c[2])
            return T.schedule(recs, pos, mode, cost_fn=g)["total_cycles"]
        out[wl] = (run, count, run())
    return out


def first_map(count, ops, A):
    first = {}
    for k in count:
        for op in ops:
            if A.op_match(k, op):
                first[k] = op; break
    return first


def cmd_sens(SRC, PDIR, OUT):
    T = load_T(SRC); import accepted_cost as A
    patch_schedule()
    led = T.ledger(PDIR)
    ops0, _ = T.op_deltas(led, led)
    opnames = [o['op'] for o in ops0]
    par = {o['op']: o['parallel'] for o in ops0}
    S = schedules(A, False)
    run, count, base = S['ds_ar']
    first = first_map(count, opnames, A)
    opsens = {}
    for op in opnames:
        ex = tuple((k, None, float(DLT)) for k, o in first.items() if o == op)
        opsens[op] = 0.0 if not ex else (run(ex) - base) / DLT          # ds_ar cycles per op cycle (upper)
        print('op', op, round(opsens[op], 2), flush=True)
    lanes = {}
    for lid in led['lanes']:
        l2 = copy.deepcopy(led); l2['lanes'][lid]['total'] += DLT
        rows, _ = T.op_deltas(led, l2)
        dop = {o['op']: o['delta_cycles'] / DLT for o in rows if o['delta_cycles']}
        lanes[lid] = dict(w=round(sum(v * opsens[o] for o, v in dop.items()), 4), ops=dop,
                          families=led['lanes'][lid].get('families'), width=led['lanes'][lid].get('width'))
    plan = json.load(open(Path(PDIR) / 'die_plan.json'))
    port_lane = {p: ln['id'] for ln in plan['lanes'] for p in ln['ports']}
    json.dump(dict(base_ds_ar=base, op_sens=opsens, parallel=par, lanes=lanes, port_lane=port_lane, dlt=DLT),
              open(OUT, 'w'), indent=0)
    w = sorted(((v['w'], k) for k, v in lanes.items()), reverse=True)
    print('lanes', len(lanes), 'weighted>0', sum(1 for x, _ in w if x > 0), 'top', w[:8])


def hp_patch(Lc):
    """span legality = HALF-PERIMETER (w + h) / 2 <= cap (the in-region tree insertion I = v (w + h) / 2 is what sets
    the spread), plus max side <= the largest partition side (HBM bank columns are 4.32 mm tall, hubs 8.22 mm wide,
    so a 3-4 mm max-side cap leaves every partition alone)."""
    for fn in ('propose', 'propose_tree'):
        s = inspect.getsource(getattr(Lc, fn))
        old = "max(b[2] - b[0], b[3] - b[1]) > cap + 1e-6"
        assert old in s, fn
        s = s.replace(old, "((b[2] - b[0] + b[3] - b[1]) / 2 > cap + 1e-6 or max(b[2] - b[0], b[3] - b[1]) > SIDE_MAX)")
        ns = {}
        exec(compile(s, Lc.__file__ + ':r3hp', 'exec'), Lc.__dict__, ns)
        setattr(Lc, fn, ns[fn])


def cmd_maps(SRC, PDIR, SENS, OUTD):
    import locality as Lc
    hp = Path(OUTD).name.startswith('hp')
    if hp:
        hp_patch(Lc)
    sens = json.load(open(SENS))
    D = Lc.load_plan(str(Path(PDIR) / 'die_plan.json'))
    padj = Lc.part_adjacency(D)
    M = Lc.traffic(D)
    pl = sens['port_lane']; lw = {k: v['w'] for k, v in sens['lanes'].items()}
    crit = collections.Counter()
    for q in D['ports']:
        a, b = sorted((q['src'], q['dst']))
        crit[(a, b)] += lw.get(pl.get(q['id']), 0.0)
    totbits = sum(m['bits'] for m in M.values())
    totw = sum(crit.values()) or 1.0
    Path(OUTD).mkdir(parents=True, exist_ok=True)
    Lc.SIDE_MAX = max(max(p["rect"][2] - p["rect"][0], p["rect"][3] - p["rect"][1]) for p in D["parts"].values()) + 1e-6
    cfgs = ((2.0, 4.0), (3.0, 5.0), (3.0, 6.0)) if hp else ((2.0, 3.0), (2.0, 3.5), (3.0, 4.0))
    out = {}
    for lam in ((0.0, 10.0) if hp else (0.0, 1.0, 10.0)):   # critical weight in units of the die's total bits
        MW = {k: dict(m, bits=m['bits'] + lam * totbits * crit.get(k, 0.0) / totw) for k, m in M.items()}
        for s0, cap in cfgs:
            for kind in ('v1', 'tree'):
                if kind == 'v1':
                    reg = Lc.propose(D, cap, MW, padj)
                else:
                    reg = Lc.propose_tree(D, s0, cap, MW, padj)[0]
                tag = f"tok_l{lam:g}_{kind}_s{s0:g}c{cap:g}" if kind == 'tree' else f"tok_l{lam:g}_v1_c{cap:g}"
                # critical-weight fraction kept inside regions
                inside = sum(w for (a, b), w in crit.items() if reg[a] == reg[b]) / totw
                nreg = len(set(reg.values()))
                p = Path(OUTD) / f"{tag}.json"
                p.write_text(json.dumps(dict(part_region=reg), sort_keys=True))
                out[tag] = dict(regions=nreg, crit_inside=round(inside, 4), path=str(p))
                print(tag, out[tag], flush=True)
    json.dump(out, open(Path(OUTD) / 'maps_index.json', 'w'), indent=1)


def cap_patch(Lc):
    """MESO-COUNT-2 rows: a region the DIRECTED start tree does not reach gives kind 'unreached' rows without L_lo/L_hi;
    count them as FAIL (depth None, priced at FAILPH) and keep the summary keys main's locality reads."""
    s = inspect.getsource(Lc.cap_plan_corners)
    old = '                x["margin_lo_ps"] = round(x["L_lo_ps"] - 0.5 * period, 1)\n'
    new = ('                if "L_lo_ps" not in x:\n'
           '                    x.update(L_lo_ps=None, L_hi_ps=None, margin_lo_ps=None, margin_hi_ps=None, depth=None,\n'
           '                             path_ambiguous_cycles=0)\n'
           '                    res[x["port"]] = x\n'
           '                    continue\n' + old)
    assert old in s
    s = s.replace(old, new).replace('s["max_path_ambiguous_cycles"]', 's.get("max_path_ambiguous_cycles", 0)')
    s = s.replace('summ[k] += s[k]', 'summ[k] += s.get(k, 0)')
    ns = {}
    exec(compile(s, Lc.__file__ + ':r3cap', 'exec'), Lc.__dict__, ns)
    Lc.cap_plan_corners = ns['cap_plan_corners']


def cmd_tsv(SRC, PLAN, V, FEED, MAP, OUT):
    """one map x feed -> crossings TSV (price_landing format) + fail list (kind) ; same score/cap_reading as run_v3."""
    import locality as Lc
    cap_patch(Lc)
    D = Lc.load_plan(PLAN); padj = Lc.part_adjacency(D); M = Lc.traffic(D); Ttab = Lc.CA.load(Lc.TABLE)
    reg = Lc.load_regions(MAP, D)
    S = Lc.score(D, reg, float(V), FEED, padj, M, Ttab)
    cs = Lc.cap_reading(S["crossings"], D["period"])
    with open(OUT, "w") as fh:
        fh.write("id\tsrc_region\tdst_region\twidth\ton_feed\tkind\tL_lo_ps\tL_hi_ps\tdepth\tlat_cycles\tmargin_lo_ps"
                 "\tmargin_hi_ps\tphys_cycles\n")
        for r in S["crossings"]:
            fh.write(f"{r['id']}\t{r['ra']}\t{r['rb']}\t{r['width']}\t{int(r['on_feed'])}\t{r.get('K_kind')}\t"
                     f"{r.get('L_lo')}\t{r.get('L_hi')}\t{r.get('depth') or 'FAIL'}\t"
                     f"{'-' if r.get('lat') is None else r['lat']}\t{r.get('m_lo')}\t{r.get('m_hi')}\t"
                     f"{'-' if r.get('phys') is None else r['phys']}\n")
    fails = [(r['id'], r['ra'], r['rb'], r['width'], r.get('K_kind')) for r in S["crossings"] if not r.get('depth')]
    print(json.dumps(dict(map=MAP, feed=FEED, v=V, summary={k: cs[k] for k in cs if not isinstance(cs[k], (list, dict))},
                          fails=fails)))


def cmd_score(SRC, PLAN, V, OUTD, maps):
    import locality as Lc
    cap_patch(Lc)
    mi = [tuple(a.split('=', 1)) for a in maps]
    Lc.run_v3(PLAN, 'hbm', float(V), OUTD, maps_in=mi, tree_cfgs=(), feeds=('fish', 'spt', 'fwd'), render_png=True,
              v_note=f'DIE-HBM-3 region3 score @ {V} ps/mm')


def cmd_price(SRC, PDIR, OUT, args):
    T = load_T(SRC); import accepted_cost as A
    patch_schedule()
    led = T.ledger(PDIR)
    plan = json.load(open(Path(PDIR) / 'die_plan.json'))
    port_lane = {p: ln['id'] for ln in plan['lanes'] for p in ln['ports']}
    S = schedules(A, True)
    res = {}
    for arg in args:
        tag, tsv = arg.split('=', 1)
        rows = list(csv.DictReader(open(tsv), delimiter='\t'))
        add = collections.Counter()
        for r in rows:
            lid = port_lane.get(r['id'])
            if lid is None:
                continue
            add[lid] += FAILPH if r['phys_cycles'] in ('-', '') else int(r['phys_cycles'])
        led2 = copy.deepcopy(led)
        for lid, a in add.items():
            led2['lanes'][lid]['total'] += a
        ops, _ = T.op_deltas(led, led2)
        byop = {o['op']: o for o in ops}
        o = dict(crossings=len(rows), fails=sum(1 for r in rows if r['depth'] == 'FAIL'), lanes_touched=len(add),
                 op_delta={k: v['delta_cycles'] for k, v in byop.items() if v['delta_cycles']}, wl={})
        for wl, (run, count, b) in S.items():
            first = first_map(count, byop, A)
            ex = tuple((k, None, float(byop[op]['delta_cycles'])) for k, op in sorted(first.items())
                       if byop[op]['delta_cycles'])
            w = {}
            for mode, lat in (('nohide', False), ('hide', True)):
                d = run(ex, lat) - b
                w[mode] = dict(added=round(d, 1), loss_pct=round(100 * d / (b + d), 3))
                if wl == 'ds_ar':
                    w[mode]['tok_s'] = round(CLK / (U3F + d), 1)
            bsx = run((), False, "SX")             # deeper look-ahead: dispatch skip-ahead (records in flight past a held one)
            d = run(ex, True, "SX") - bsx
            w['hide_sx'] = dict(added=round(d, 1), loss_pct=round(100 * d / (bsx + d), 3), base_sx=round(bsx, 1))
            if wl == 'ds_ar':
                w['hide_sx']['tok_s'] = round(CLK / (U3F + d), 1)
            w['ideal'] = dict(added=0.0, tok_s=round(CLK / U3F, 1)) if wl == 'ds_ar' else dict(added=0.0)
            o['wl'][wl] = w
        res[tag] = o
        print(tag, json.dumps({k: o[k] for k in ('crossings', 'fails', 'lanes_touched')}),
              json.dumps(o['wl']), flush=True)
    json.dump(res, open(OUT, 'w'), indent=1)


if __name__ == '__main__':
    c, SRC = sys.argv[1], sys.argv[2]
    setup(SRC)
    if c == 'sens':
        cmd_sens(SRC, sys.argv[3], sys.argv[4])
    elif c == 'maps':
        cmd_maps(SRC, sys.argv[3], sys.argv[4], sys.argv[5])
    elif c == 'score':
        cmd_score(SRC, sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6:])
    elif c == 'tsv':
        cmd_tsv(SRC, *sys.argv[3:8])
    elif c == 'price':
        cmd_price(SRC, sys.argv[3], sys.argv[4], sys.argv[5:])
