#!/usr/bin/env python3
"""Analytic recomposition only; no new RTL measurements or physical admission."""
import argparse
import collections
import copy
import hashlib
import itertools
import json
from pathlib import Path

REC = 'results/rtl/dsrom_recovery_20261004'
BASE = 'results/rtl/dsrom_1m_allmeasured_20261004/draft_blocks.json'

def longest(g, t):
    finish, path = {}, {}
    while len(finish) < len(g):
        ready = [n for n in g if n not in finish and all(d in finish for d in g[n]['deps'])]
        if not ready:
            raise ValueError('cyclic or missing dependency')
        for n in ready:
            ds = g[n]['deps']
            p = max(ds, key=lambda d: finish[d]) if ds else None
            finish[n] = (finish[p] if p else 0) + t[n]
            path[n] = (path[p] if p else []) + [n]
    end = max(finish, key=finish.get)
    return finish[end], path[end]

def recovery_graph(g):
    g = copy.deepcopy(g)
    for n in ('experts_gu', 'swiglu', 'route_w', 'quant2', 'down'):
        del g['ffn.' + n]
    g['ffn.shared_down'] = {'deps': ['ffn.shared_quant']}
    for r in range(5):
        chain = {'x_hop': ['ffn.norm.scale'], 'rquant': [f'ffn.x_hop.r{r}'],
                 'ids_hop': ['ffn.top6_order'], 'w_hop': ['ffn.weights'],
                 'experts_gu': [f'ffn.rquant.r{r}', f'ffn.ids_hop.r{r}'],
                 'swiglu': [f'ffn.experts_gu.r{r}'],
                 'route_w': [f'ffn.swiglu.r{r}', f'ffn.w_hop.r{r}'],
                 'quant2': [f'ffn.route_w.r{r}'], 'down': [f'ffn.quant2.r{r}'],
                 'ret_hop': [f'ffn.down.r{r}']}
        g.update({f'ffn.{n}.r{r}': {'deps': ds} for n, ds in chain.items()})
    g['ffn.combine_allreduce']['deps'] = [f'ffn.ret_hop.r{r}' for r in range(5)] + ['ffn.shared_down']
    return g

def serialized(g, assignment):
    g = copy.deepcopy(g)
    previous = {}
    for r, lane in enumerate(assignment):
        if lane in previous:
            # Full row retires before that replica accepts another row: no invented buffering/overlap.
            dep = f'ffn.ret_hop.r{previous[lane]}'
            for n in ('x_hop', 'ids_hop', 'w_hop'):
                g[f'ffn.{n}.r{r}']['deps'].append(dep)
        previous[lane] = r
    return g

def sweep(root):
    pins = {}
    def load(p):
        raw = (root / p).read_bytes()
        pins[p] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    base = load(BASE)
    recovered = load(REC + '/draft/draft_blocks_recovery.json')
    pl = load(REC + '/draft/placement.json')
    floorplan = load('results/rtl/dsrom_s81_fulldie_20261004/floorplan.json')
    die_mm2 = pl['dies']['die_mm2']
    assert die_mm2 == floorplan['die']['decision_priced_mm2'] == 839.239
    links = load(REC + '/draft/rlinks.json')
    comp = load(REC + '/composition.json')
    g0 = load(REC + '/draft_sweep_inputs/block_graph.json')
    for p in ['tools/dsrom_draft_placement_sweep.py', 'tools/dsrom_1m_draft_blocks.py', 'tools/dsrom_1m_measure.py', 'tools/uarch_model.py', 'tools/arch_budget_v41.py', 'tools/decode_critical_path.py', 'results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json']:
        pins[p] = hashlib.sha256((root / p).read_bytes()).hexdigest()
    assert base['exact'] and links['status'] == 'pass'
    rg = recovery_graph(g0)
    times = []
    for st in range(3):
        key = f'mtp.{st}'
        old = {n: v['us'] for n, v in base['nodes'][key].items()}
        assert abs(longest(g0, old)[0] - base['block_us'][st]) < .001
        t = {n: v['us'] for n, v in recovered['stages'][key]['nodes'].items()}
        assert abs(longest(rg, t)[0] - recovered['block_us'][st]) < .001
        times.append(t)
    mtp = comp['MTP']
    def metrics(blocks):
        total = sum(blocks)
        delta = total - mtp['draft_terms']['blocks_us']
        return dict(block_us=[round(x, 5) for x in blocks], draft_blocks_us=round(total, 5),
                    draft_us=round(mtp['draft_us'] + delta, 5),
                    MTP_tok_s=round(mtp['tau'] * 1e6 / (mtp['step_us'] + delta), 3))
    rows = []
    for ep in (1, 2, 3, 5):
        values, assignments, paths = [], [], []
        for t in times:
            best = min(((*longest(serialized(rg, a), t), a) for a in ([(0,1,2,3,4)] if ep == 5 else itertools.product(range(ep), repeat=5))),
                       key=lambda x: (x[0], x[2]))
            values.append(best[0]); paths.append(best[1]); assignments.append(best[2])
        total_dies = 4 + 12 * ep
        rows.append(dict(name=f'DP1-EP{ep}', **metrics(values), total_draft_dies=total_dies,
                         added_dies=total_dies-12, added_die_mm2=round((total_dies-12)*die_mm2, 6),
                         replica_links_per_primary_rank=3*ep, replica_link_instances=12*ep, both_end_replica_endpoint_instances=24*ep,
                         row_to_replica=assignments, critical_paths=paths,
                         latency_scope='conditional conservative schedule; measured five-row SU charge per row retained; no replica reuse until return retires',
                         added_endpoint_area_mm2=None, qualified_draft_us=None, qualified_MTP_tok_s=None))
    # Co-location can share the primary with stage-0 expert group; same L0 pairs are disjoint.
    # Stage 0 keeps the existing batch graph; stage 1/2 use the serial remote EP1 schedule above.
    old0 = {n: v['us'] for n, v in base['nodes']['mtp.0'].items()}
    dp_values = [longest(g0, old0)[0]] + rows[0]['block_us'][1:]
    rows.append(dict(name='DP1-co-location-alone', **metrics(dp_values), total_draft_dies=12,
                     added_dies=0, added_die_mm2=0, replica_links_per_primary_rank=2,
                     replica_link_instances=8, both_end_replica_endpoint_instances=16, stage0_experts_local=True,
                     max_rank_words=2307072+9175040, rank_word_capacity=pl['capacity']['die_words'], bank_union_verified=False,
                     placement_scope='prospective retain original three expert TP4 groups; co-locate all primary blocks with stage0 experts; new caller/links binding unqualified',
                     added_endpoint_area_mm2=None, qualified_draft_us=None, qualified_MTP_tok_s=None))
    frequencies = {}
    for st in range(3):
        key = f'mtp.{st}'
        cnt = collections.Counter(e for r in base['stages'][key]['experts'] for e in r)
        frequencies[key] = sorted((dict(expert=e, count=n) for e, n in cnt.items()), key=lambda x: (-x['count'], x['expert']))
        assert sum(cnt.values()) == 15
    # Keep the published in-die expert-pair placement. Sparse hot contents do not release whole dies.
    hot = []
    for k in (1, 2, 3):
        chosen = {st: [x['expert'] for x in fs[:k]] for st, fs in frequencies.items()}
        selected = 0
        words = 0
        for st, es in chosen.items():
            selected += sum(x['count'] for x in frequencies[st] if x['expert'] in es)
            for tensor in pl['tensors']:
                name = tensor['tensor']
                if any(name == st+f'.ffn.experts.{e}.w{w}.weight' for e in es for w in (1,2,3)):
                    words += sum(s['words'] for s in tensor['slices'] if s['rank'] == 0 and s['group'].endswith('rep0'))
        hot.append(dict(name=f'EP5-hot-top{k}-per-stage', experts=chosen, routed_hits=selected,
                        routed_total=45, extra_replica_rank_words_total=4*words,
                        fixed_group_added_dies=52, added_dies=52, added_die_mm2=round(52*die_mm2,6),
                        packed_added_dies=None, packed_added_die_mm2=None,
                        replica_links_per_primary_rank=15, replica_link_instances=60, both_end_replica_endpoint_instances=120,
                        draft_us=None, MTP_tok_s=None, added_endpoint_area_mm2=None,
                        reason='hot/cold split needs independently bound partial-return/golden ID-order join and SU service timings; existing link measurement returns a complete three-expert row; no invented partial-return timing or new packing'))
    return dict(schema='opentallas.dsrom-draft-placement-sweep.v1', source_commit='d44e40bfd1b4cbe77115ec0526e1b2f7b4c4aab1',
                status='ANALYTIC_CONDITIONAL_NO_ADOPTION', source_pins=pins, variants=rows+hot,
                routing_frequency=frequencies, routing_scope='this 1M anchor three draft stages x five rows x three experts; historical window127rows synthetic as preserved original record; not corpus frequency',
                composition_anchor=dict(path=REC+'/composition.json', MTP=mtp, reason='same pinned composition snapshot as inputs; all non-placement terms held constant'),
                endpoint_counts='replica_link_instances counts point-to-point links; both-end endpoint instances = 2x; area/serialization/fanout/context unresolved',
                physical_admitted=False, full_token_measured=False,
                unbound=['star fanout/serialization/credits under concurrent rows', 'additional endpoint area and S81 slot/PG/clock/route fit', 'replica row reuse caller and return visibility; extra per-row service turnaround unknown', 'DP1 co-location bank union and return routing owner binding', 'hot/cold partial sum return in unchanged golden order'],
                area_discrepancy=dict(exact_52_die_mm2=round(52*die_mm2,6), directive_mm2=43678,
                                      directive_minus_exact_mm2=round(43678-52*die_mm2,6), basis='839.239mm2 source die price; endpoint area excluded'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path)
    a=p.parse_args();d=sweep(a.root);out=a.output or a.root/(REC+'/levers/draft_sweep.json');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps([{'name':v['name'],'draft_us':v['draft_us'],'MTP_tok_s':v['MTP_tok_s'],'added_dies':v['added_dies']} for v in d['variants']],indent=2))
if __name__ == '__main__':main()
