#!/usr/bin/env python3
"""S81-ROMOPT-B (10-20): the per-stage content map of the S81 release chain (which layer weights / routed experts each
TP4 stage -- 4 rank dies, rank r = row quarter r of every matrix -- holds), balanced on ACTUAL allocated words.

Content universe (released checkpoint headers, results/quality/w16_w17_checkpoint_header_catalogue_20261001/headers,
metadata only): 40 layers x 384 routed experts (w1/w3 2304 x 5120, w2 5120 x 2304, MXFP4) + per layer the dense ops
the p4l field holds (wq_a/wkv = a_proj, wq_b, wo_b, shared w1/w3/w2 on the q pairs; indexer.wq_b on the 8 index
layers; engram.wkv on layers 1 / 14; wo_a, gate (router), compressor wkv(+wgate) on the BF pairs).  Not on layer
dies: embed / head / MTP draft (head dies), Engram tables (HBM), hc_* / norms / sinks (SU / svc registers).

Placement rule: experts in (layer, expert id) order, contiguous over the chain (a token visits the stages in order);
the attention (dense) of layer L sits on the stage that holds expert (L, 0).  Stage boundaries are chosen so every
stage's worst-pair ROM load (dense intercept + N x per-expert slope, both from xs_capacity probe runs of the actual
allocator) is equal; the exact per-stage verdict is then a full xs_capacity run of each distinct stage.

    xs_stage_map.py build --stages 97 --probe PROBE_SUMMARY.json --out MAP.json --specs SPECS.json [--plan NAME]
    xs_stage_map.py merge --map MAP.json --runs RUN_SUMMARY.json [...] [--cover] [--die-frames 122 --rom-slots 1130]
                                                                        # writes the exact verdict into the map
    xs_stage_map.py minstages --probe PROBE_SUMMARY.json                   # the fewest stages the probe costs admit
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xs_capacity as XC  # noqa: E402

ROOT = HERE.parents[2]
HDR = ROOT / 'results/quality/w16_w17_checkpoint_header_catalogue_20261001/headers'
NL, NE, TP = 40, 384, 4
DUP_LAYERS = (2, 8, 14, 20, 24, 28, 32, 36)          # MU cal1 copy-B groups (dv_mu_calendar.DUP_LAYER)
Q_TENSORS = ('attn.wq_a.weight', 'attn.wkv.weight', 'attn.wq_b.weight', 'attn.wo_b.weight', 'ffn.shared_experts.w1.weight',
             'ffn.shared_experts.w3.weight', 'ffn.shared_experts.w2.weight', 'attn.indexer.wq_b.weight', 'engram.wkv.weight')
BF_TENSORS = ('attn.wo_a.weight', 'ffn.gate.weight', 'attn.compressor.wkv.weight', 'attn.compressor.wgate.weight')


def headers():
    T, shas = {}, {}
    for f in sorted(glob.glob(str(HDR / '*.header.json'))):
        b = Path(f).read_bytes()
        shas[Path(f).name] = hashlib.sha256(b).hexdigest()
        for k, v in json.loads(b.rstrip(b' \x00')).items():
            if k != '__metadata__':
                T[k] = v
    return T, shas


def census():
    T, shas = headers()
    layers = []
    for L in range(NL):
        ex = sorted({int(m.group(1)) for k in T for m in [re.match(rf'^layers\.{L}\.ffn\.experts\.(\d+)\.w1\.weight$', k)] if m})
        assert ex == list(range(NE)), (L, len(ex))
        for e in (0, NE - 1):
            for n, shp in (('w1', [2304, 2560]), ('w3', [2304, 2560]), ('w2', [5120, 1152])):
                assert T[f'layers.{L}.ffn.experts.{e}.{n}.weight']['shape'] == shp, (L, e, n)
        q = {t: T[f'layers.{L}.{t}']['shape'] for t in Q_TENSORS if f'layers.{L}.{t}' in T}
        bf = {t: T[f'layers.{L}.{t}']['shape'] for t in BF_TENSORS if f'layers.{L}.{t}' in T}
        xs, bfo, fix, cal = XC.layer_ops(L)
        # the op lists must be exactly the tensors the checkpoint has for this layer
        assert ('attn.indexer.wq_b.weight' in q) == ('attn.idx.q' in xs), L
        assert ('engram.wkv.weight' in q) == ('eng.wkv' in xs), L
        assert ('attn.compressor.wkv.weight' in bf) == ('attn.cmp.wk' in bfo), L
        layers.append(dict(layer=L, experts=NE, q_tensors=q, bf_tensors=bf, xs_ops=xs, bf_ops=bfo, fixture=fix,
                           calendar_rows=cal, cls=cls_of(L)))
    return layers, shas


def cls_of(L):
    return 'L14' if L == 14 else 'L1' if L == 1 else 'L20' if L == 20 else 'L2' if L in (2, 8) else \
        'L24' if L in XC.IDX_SRC else 'L0'


def probe_costs(probe):
    """dense intercept (worst q pair / BF pair, phases) per class and the per-expert slope, from an xs_capacity probe"""
    s = {x['id']: x for x in json.loads(Path(probe).read_text())['specs']}
    e = s['exp_n120']
    slope = e['q_max_fill'] / e['experts']
    ph = e['cfg7_phases'] / e['experts']
    dense = {c: dict(q=s[f'dense_L{L}_n0']['q_max_fill'], bf=s[f'dense_L{L}_n0']['bf_max_fill'],
                     phases=s[f'dense_L{L}_n0']['cfg7_phases'])
             for c, L in (('L0', 0), ('L1', 1), ('L2', 2), ('L14', 14), ('L20', 20), ('L24', 24))}
    return dict(slope=slope, phases_per_expert=ph, dense=dense, source=str(probe))


def nmax(c, cls):
    d = c['dense'][cls] if cls else dict(q=0, phases=0)
    by_rom = math.floor((XC.DEPTH - 1 - d['q']) / c['slope'])
    by_cfg = math.floor((XC.CFG7_PHASES - d['phases']) / c['phases_per_expert'])
    return min(by_rom, by_cfg)


def build(nst, c, plan):
    layers, shas = census()
    total = sum(l['experts'] for l in layers)
    # equal worst-pair load: stage load = dense q + N x slope; choose the common load level by bisection
    order = [(L, e) for L in range(NL) for e in range(NE)]

    def deal(level):
        st, i = [], 0
        while i < len(order):
            dense = None
            n = 0
            load = 0.0
            while i < len(order):
                L, e = order[i]
                add = c['slope'] + (c['dense'][cls_of(L)]['q'] if e == 0 else 0)
                if e == 0 and dense is not None:
                    break                      # never two attentions on one stage
                if n and load + add > level:
                    break
                if e == 0:
                    dense = L
                load += add
                n += 1
                i += 1
            st.append(dict(first=order[i - n], n=n, dense_layer=dense, load=load))
        return st
    lo, hi = c['slope'], XC.DEPTH * 4.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if len(deal(mid)) > nst:
            lo = mid
        else:
            hi = mid
    st = deal(hi)
    stages = []
    i = 0
    for k, s in enumerate(st):
        ex = order[i:i + s['n']]
        i += s['n']
        runs = []
        for L, e in ex:
            if runs and runs[-1][0] == L and runs[-1][2] == e - 1:
                runs[-1][2] = e
            else:
                runs.append([L, e, e])
        dl = s['dense_layer']
        lay = sorted({L for L, _ in ex} | ({dl} if dl is not None else set()))
        cal = sum(layers[L]['calendar_rows'] for L in lay)
        stages.append(dict(stage=f'R{k:03d}', dies=[f'R{k:03d}.r{r}' for r in range(TP)], layers=lay, dense_layer=dl,
                           dense=(dict(q_pairs=sorted(layers[dl]['q_tensors']), bf_pairs=sorted(layers[dl]['bf_tensors']),
                                       xs_ops=layers[dl]['xs_ops'], bf_ops=layers[dl]['bf_ops']) if dl is not None else None),
                           experts=runs, n_experts=s['n'], model_load=round(s['load'], 1),
                           model_fill_pct=round(100 * s['load'] / XC.DEPTH, 2), calendar_rows=cal,
                           copy_b=bool(dl in DUP_LAYERS),
                           spec=spec_id(dl, s['n'])))
    assert sum(s['n_experts'] for s in stages) == total
    return dict(schema='opentallas.s81_dv.stage_map.v1', plan=plan, stages_count=len(stages), requested_stages=nst,
                rank_dies_per_stage=TP, layer_dies=TP * len(stages), experts=total, costs=c,
                content_not_on_layer_dies=dict(head_dies=['embed.weight', 'head.weight', 'norm.weight', 'mtp.* (DSpark draft)'],
                                               hbm=['layers.{1,14}.engram.embed (Engram tables)'],
                                               su_svc_registers=['hc_*', '*_norm.weight', 'attn.attn_sink', 'ffn.gate.bias*',
                                                                 'attn.indexer.{wk,k_norm,weights_proj}', 'engram.{q,k}_weight']),
                copy_b_note='MU cal1 copy B (80 dies) duplicates the dies of the stage(s) holding the attention of '
                            'layers 2/8/14/20/24/28/32/36: same ROM content, so their capacity verdict is the copy-A one',
                header_sha256=shas, stages=stages)


def spec_id(dl, n, half=None):
    if half is not None:                              # DENSE2 split map: A / B halves, X = expert-only stage
        return f'{"exp" if dl is None else "L%d" % dl}{"" if half == "X" else half}_n{n}'
    return f'{"exp" if dl is None else "L%d" % dl}_n{n}'


# ------------------------------------------------------------------------------------------------ DENSE2 split map
def probe_costs_split(probe, rows=None):
    """DENSE2 costs from ONE actual-allocator probe run on the target inventory: per-expert slope / phases from the
    expert-only probes (largest N; linearity of the q worst pair checked over every N probed: identical layouts), dense
    intercepts per class for the A half (a_proj rows [0, R)) and the B half (rows [R, 448) + every other dense op)"""
    s = {x['id']: x for x in json.loads(Path(probe).read_text())['specs']}
    bad = [k for k, v in s.items() if not v['pass'] and v['dense_layer'] is not None]
    assert not bad, ('dense probe specs fail', bad)
    refused = [dict(n=v['experts'], q=v['q_max_fill'], fault=(v['first_fault'] or {}).get('fault'))
               for v in s.values() if v['dense_layer'] is None and not v['pass']]
    ex = sorted((v for v in s.values() if v['dense_layer'] is None and v['experts'] and v['pass']), key=lambda v: v['experts'])
    assert len(ex) >= 2, 'need >= 2 expert-only probes'
    big = ex[-1]
    slope = big['q_max_fill'] / big['experts']
    ph = big['cfg7_phases'] / big['experts']
    lin = [dict(n=v['experts'], q=v['q_max_fill'], q_per_expert=round(v['q_max_fill'] / v['experts'], 3)) for v in ex]
    assert all(v['q_max_fill'] <= slope * v['experts'] + 1e-9 for v in ex), ('expert q not linear-bounded', lin)
    dense = {}
    for half in ('A', 'B'):
        dense[half] = {c: dict(q=s[f'dense_L{L}{half}_n0']['q_max_fill'], bf=s[f'dense_L{L}{half}_n0']['bf_max_fill'],
                               phases=s[f'dense_L{L}{half}_n0']['cfg7_phases'])
                       for c, L in (('L0', 0), ('L1', 1), ('L2', 2), ('L14', 14), ('L20', 20), ('L24', 24))}
    return dict(slope=slope, phases_per_expert=ph, dense_split2=dense, dense_split2_rows=rows, expert_probes=lin,
                expert_probes_refused=refused,
                frames=big['frames'], source=str(probe))


def build_split(nst, c, plan, level=None):
    """the build() rule with every dense layer split over two consecutive stages: per layer L the chain items are
    A(L) (a_proj rows [0, R)), B(L) (a_proj rows [R, 448) + every other dense op), then experts (L, 0..383); a stage
    holds at most ONE dense item (never two halves / attentions on one stage); stage load = sum of item loads
    (dense intercept + N x slope); boundaries by bisection on the common load level (or a fixed `level`).
    Causality: A(L) needs only x_L (complete on A or upstream: experts (L-1, *) end on A or before), B(L) receives
    A's a_proj outputs on the stage link; every op downstream of a_proj sits on B or later."""
    layers, shas = census()
    total = sum(l['experts'] for l in layers)
    items = []
    for L in range(NL):
        items += [('A', L, None), ('B', L, None)] + [('e', L, e) for e in range(NE)]

    def add_of(it):
        k, L, _ = it
        return c['slope'] if k == 'e' else c['dense_split2'][k][cls_of(L)]['q']

    def ph_of(it):
        k, L, _ = it
        return c['phases_per_expert'] if k == 'e' else c['dense_split2'][k][cls_of(L)]['phases']

    def deal(lv):
        st, i = [], 0
        while i < len(items):
            dense, n0, load, phs, ne = None, i, 0.0, 0.0, 0
            while i < len(items):
                it = items[i]
                add = add_of(it)
                if it[0] != 'e' and dense is not None:
                    break
                if i > n0 and (load + add > lv or phs + ph_of(it) > XC.CFG7_PHASES):
                    break
                if it[0] != 'e':
                    dense = (it[0], it[1])
                else:
                    ne += 1
                load += add
                phs += ph_of(it)
                i += 1
            st.append(dict(lo=n0, hi=i, dense=dense, load=load, phases=phs, n=ne))
        return st
    if level is None:
        lo, hi = c['slope'], XC.DEPTH * 4.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if len(deal(mid)) > nst:
                lo = mid
            else:
                hi = mid
        level = hi
    st = deal(level)
    stages = []
    for k, s_ in enumerate(st):
        its = items[s_['lo']:s_['hi']]
        runs = []
        for kind, L, e in its:
            if kind != 'e':
                continue
            if runs and runs[-1][0] == L and runs[-1][2] == e - 1:
                runs[-1][2] = e
            else:
                runs.append([L, e, e])
        half, dl = s_['dense'] if s_['dense'] else ('X', None)
        lay = sorted({r[0] for r in runs} | ({dl} if dl is not None else set()))
        cal = sum(layers[L]['calendar_rows'] for L in lay)
        dense = None
        if dl is not None:
            dense = dict(half=half, a_proj_rows=(c.get('dense_split2_rows'), 'of 448 rank rows', 'A owns [0,R)' if half == 'A' else 'B owns [R,448)'))
            if half == 'B':
                dense.update(q_pairs=sorted(layers[dl]['q_tensors']), bf_pairs=sorted(layers[dl]['bf_tensors']),
                             xs_ops=layers[dl]['xs_ops'], bf_ops=layers[dl]['bf_ops'])
            else:
                dense.update(q_pairs=['attn.wq_a.weight (rows [0,R))'], bf_pairs=[], xs_ops=['attn.a_proj (rows [0,R))'], bf_ops=[])
        stages.append(dict(stage=f'R{k:03d}', dies=[f'R{k:03d}.r{r}' for r in range(TP)], layers=lay, dense_layer=dl,
                           dense_split2=half, dense=dense, experts=runs, n_experts=s_['n'], model_load=round(s_['load'], 1),
                           model_fill_pct=round(100 * s_['load'] / XC.DEPTH, 2), model_phases=round(s_['phases'], 1),
                           calendar_rows=cal, copy_b=bool(dl in DUP_LAYERS and half == 'B'),
                           spec=spec_id(dl, s_['n'], half)))
    assert sum(s_['n_experts'] for s_ in stages) == total
    halves = collections_counter((s_['dense_layer'], s_['dense_split2']) for s_ in stages if s_['dense_layer'] is not None)
    assert sorted(halves) == sorted((L, h) for L in range(NL) for h in 'AB') and set(halves.values()) == {1}, halves
    return dict(schema='opentallas.s81_dv.stage_map.v1', plan=plan, dense_split2=True, stages_count=len(stages),
                requested_stages=nst, rank_dies_per_stage=TP, layer_dies=TP * len(stages), experts=total, costs=c,
                model_level=level, header_sha256=shas, stages=stages)


def collections_counter(it):
    import collections
    return collections.Counter(it)


def min_stages_split(c):
    """fewest stages whose every model load < DEPTH and cfg7 phases <= 1,024 (greedy deal at the largest legal level)"""
    m = build_split(0, c, 'min', level=XC.DEPTH - 1)
    assert all(s_['model_load'] < XC.DEPTH and s_['model_phases'] <= XC.CFG7_PHASES for s_ in m['stages'])
    return m['stages_count']


def specs_of(m):
    seen = {}
    for s in m['stages']:
        seen.setdefault(s['spec'], dict(id=s['spec'], dense_layer=s['dense_layer'], experts=s['n_experts'],
                                        calendar_rows=s['calendar_rows']))
        if 'dense_split2' in s:
            seen[s['spec']].update(dense_split2=s['dense_split2'], dense_split2_rows=m['costs'].get('dense_split2_rows'))
        seen[s['spec']]['calendar_rows'] = max(seen[s['spec']]['calendar_rows'], s['calendar_rows'])
    return list(seen.values())


def cmd_build(a):
    if a.dense_split2:
        c = probe_costs_split(a.probe, a.split_rows)
        nst = a.stages or min_stages_split(c)
        m = build_split(nst, c, a.plan or f'{nst}-stage DENSE2 split (a_proj rows over 2 stages), balanced on probe load')
        Path(a.out).write_text(json.dumps(m, indent=1) + '\n')
        sp = specs_of(m)
        if a.specs:
            Path(a.specs).write_text(json.dumps(sp, indent=1) + '\n')
        w = max(m['stages'], key=lambda s: s['model_load'])
        print(f'STAGE_MAP_SPLIT {m["plan"]}: {m["stages_count"]} stages ({TP * m["stages_count"]} layer dies), {len(sp)} specs, '
              f'worst model fill {w["model_fill_pct"]} % ({w["stage"]} N {w["n_experts"]} dense {w["dense_layer"]}{w["dense_split2"]}), '
              f'min stages {min_stages_split(c)}')
        return 0
    assert a.stages, '--stages required (one-stage map)'
    c = probe_costs(a.probe)
    m = build(a.stages, c, a.plan or f'{a.stages}-stage contiguous, balanced on probe worst-pair load')
    Path(a.out).write_text(json.dumps(m, indent=1) + '\n')
    sp = specs_of(m)
    if a.specs:
        Path(a.specs).write_text(json.dumps(sp, indent=1) + '\n')
    w = max(m['stages'], key=lambda s: s['model_load'])
    print(f'STAGE_MAP {m["plan"]}: {m["stages_count"]} stages, {len(sp)} distinct specs, worst model fill '
          f'{w["model_fill_pct"]} % ({w["stage"]} N {w["n_experts"]} dense {w["dense_layer"]}), N range '
          f'{min(s["n_experts"] for s in m["stages"])}..{max(s["n_experts"] for s in m["stages"])}')
    return 0


def _pin_env(env):
    """the OT_XS_* flags that change the allocator result (seconds/paths excluded): runs only cover each other on equal pins"""
    return {k: v for k, v in sorted((env or {}).items()) if k.startswith('OT_XS_') and k != 'OT_XS_STAGE_MAP'}


def cmd_merge(a):
    m = json.loads(Path(a.map).read_text())
    res, recs = {}, []
    for f in a.runs:
        r = json.loads(Path(f).read_text())
        for s in r['specs']:
            res[s['id']] = dict(s, run=str(f), env=r['env'])
            recs.append(res[s['id']])
    envs = {json.dumps(_pin_env(r['env'])) for r in recs}
    if a.cover and len(envs) > 1:   # DRIVE-S81-MAP141: covering across runs is only sound on one pinned flag set
        raise SystemExit(f'merge --cover: runs disagree on OT_XS_* pins: {sorted(envs)}')
    miss = []
    for s in m['stages']:
        rec = res.get(s['spec'])
        if rec is None and a.cover:
            # DRIVE-S81-MAP141 (S81-SWEET coverage rule): a stage with dense layer L and N experts is covered by a PASS record
            # of the SAME dense layer (None = expert-only) with >= N experts under the same pins -- the q/bf fill is monotone
            # in N on a fixed dense op set; the calendar-row check is re-done below on this stage's own rows.
            c = [r for r in recs if r.get('pass') and r.get('dense_layer') == s['dense_layer'] and r['experts'] >= s['n_experts']]
            if c:
                rec = dict(min(c, key=lambda r: (r['experts'], r['id'])))
                rec['covered_by'] = rec['id']
        if rec is not None:
            cap = dict(rec)
            cap['calendar_rows'] = s['calendar_rows']
            cap['calendar_margin'] = XC.CAL_ROWS - s['calendar_rows']
            cap['pass'] = bool(cap['pass']) and s['calendar_rows'] <= XC.CAL_ROWS
            s['capacity'] = cap
        else:
            miss.append(s['spec'])
    m['verdict'] = dict(stages_checked=len(m['stages']) - len(miss), missing=sorted(set(miss)),
                        stages_pass=sum(1 for s in m['stages'] if s.get('capacity', {}).get('pass')),
                        all_pass=not miss and all(s['capacity']['pass'] for s in m['stages']))
    if a.cover:
        m['verdict']['rule'] = 'exact id, else covered by a PASS of the same dense layer with >= N experts (same OT_XS_* pins)'
    if recs and len(envs) == 1:
        m['verdict']['env'] = _pin_env(recs[0]['env'])
    if a.die_frames is not None:   # DRIVE-S81-MAP141: the die inventory this map was qualified on (dv_plan --stage-map asserts it)
        m['die_frames'], m['rom_slots'] = a.die_frames, a.rom_slots
    Path(a.out or a.map).write_text(json.dumps(m, indent=1) + '\n')
    print('STAGE_MAP_VERDICT', json.dumps(m['verdict']))
    return 0 if m['verdict']['all_pass'] else 1


def cmd_minstages(a):
    c = probe_costs(a.probe)
    for n in range(80, 200):
        m = build(n, c, 'probe')
        if m['stages_count'] <= n and all(s['model_load'] < XC.DEPTH and s['n_experts'] <= nmax(c, cls_of(s['dense_layer']) if s['dense_layer'] is not None else None)
                                          for s in m['stages']):
            print('MIN_STAGES', n, 'worst model fill', max(s['model_fill_pct'] for s in m['stages']))
            return 0
    return 1


def cmd_table(a):
    """markdown per-stage table of a (merged) map: exact xs_capacity numbers where present, else the probe model"""
    m = json.loads(Path(a.map).read_text())
    print(f'| stage | layers | dense | experts (layer:first-last) | N | q worst pair | q fill % | q margin | BF fill % | '
          f'cfg7 phases (margin) | calendar rows (margin) | verdict |')
    print('|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|')
    for s in m['stages']:
        c = s.get('capacity')
        ex = ' '.join(f'{L}:{a}-{b}' for L, a, b in s['experts'])
        if c:
            q = f'{c["q_max_fill"]} | {c["q_fill_pct"]} | {c["q_margin_words"]} | {c["bf_fill_pct"]} | {c["cfg7_phases"]} ({c["cfg7_margin"]})'
            v = 'PASS' if c['pass'] else '**FAIL**'
        else:
            q = f'~{s["model_load"]:.0f} | ~{s["model_fill_pct"]} | ~{XC.DEPTH - s["model_load"]:.0f} | - | -'
            v = 'model only (exact run pending)'
        print(f'| {s["stage"]} | {",".join(map(str, s["layers"]))} | {"-" if s["dense_layer"] is None else "L%d" % s["dense_layer"] + s.get("dense_split2", "")} | '
              f'{ex} | {s["n_experts"]} | {q} | {s["calendar_rows"]} ({XC.CAL_ROWS - s["calendar_rows"]}) | {v} |')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest='cmd', required=True)
    b = sp.add_parser('build')
    b.add_argument('--stages', type=int, required=False)
    b.add_argument('--dense-split2', action='store_true', help='DENSE2: every dense layer split over 2 stages (probe '
                   'must carry dense_L<L>A_n0 / dense_L<L>B_n0 and expert-only specs)')
    b.add_argument('--split-rows', type=int, help='DENSE2 rows R of A (recorded; the probe run sets it)')
    b.add_argument('--probe', required=True)
    b.add_argument('--out', required=True)
    b.add_argument('--specs')
    b.add_argument('--plan')
    g = sp.add_parser('merge')
    g.add_argument('--map', required=True)
    g.add_argument('--runs', nargs='+', required=True)
    g.add_argument('--out')
    g.add_argument('--cover', action='store_true', help='DRIVE-S81-MAP141: accept a PASS of the same dense layer with >= N experts')
    g.add_argument('--die-frames', type=int, help='record the frame inventory the runs used (dv_plan --stage-map asserts it)')
    g.add_argument('--rom-slots', type=int)
    n = sp.add_parser('minstages')
    n.add_argument('--probe', required=True)
    t = sp.add_parser('table')
    t.add_argument('--map', required=True)
    a = p.parse_args(argv)
    return dict(build=cmd_build, merge=cmd_merge, minstages=cmd_minstages, table=cmd_table)[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
