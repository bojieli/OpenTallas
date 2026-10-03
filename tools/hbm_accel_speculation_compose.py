#!/usr/bin/env python3
"""HA7 saved-trace statistics and component composition. Never runs model inference.
Replay: python3 tools/hbm_accel_speculation_compose.py --router /tmp/claude-review-20261003/v41spec/router_full.pt
All new hardware prices are conditional, off by default. Inputs are byte-identical git snapshots.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/hbm_accel_speculation_20261003'
INPUT = OUT / 'inputs'
SPEC = 'results/speculative/v41_hbm_speculation_methods_20261003/'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def load(path, name):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def read(path):
    return json.loads(path.read_text())


def statistics(path):
    import torch
    torch.set_num_threads(2)
    traces = torch.load(path, map_location='cpu', weights_only=False)
    totals = {p: [0] * 40 for p in range(1, 9)}
    counts = {p: 0 for p in totals}
    reuse, pairs, ledger = 0, 0, []
    hits_hist = [0] * 7
    for ti, tr in enumerate(traces):
        idx = tr['router_idx'].tolist()
        L, n = tr['L'], len(idx[0])
        assert len(idx) == 40 and all(len(row) == 6 and len(set(row)) == 6 for lay in idx for row in lay)
        keys = dict(trace_index=ti, prompt_id=tr['item']['prompt_id'],
                    prompt_sha256=tr['item']['prompt_sha256'], workload=tr['item']['workload'],
                    generated_position_range=[L, n], router_key='router_idx[layer,position,top6]',
                    layers=[0, 40], tokens_key='tokens', draft_keys=sorted(map(str, tr.get('drafter_idx', {}))))
        keys['router_idx_sha256'] = hashlib.sha256(json.dumps(idx, separators=(',', ':')).encode()).hexdigest()
        ledger.append(keys)
        for p in totals:
            windows = max(0, n - p + 1 - L)
            counts[p] += windows
            for lay in range(40):
                totals[p][lay] += sum(len(set(e for row in idx[lay][q:q+p] for e in row)) for q in range(L, n-p+1))
        # Both source and target must be generated positions. The prompt/decode transition is excluded.
        for lay in idx:
            for q in range(L + 1, n):
                hit = len(set(lay[q-1]) & set(lay[q]))
                reuse += hit
                pairs += 1
                hits_hist[hit] += 1
    return dict(source_path=str(path), sha256=sha(path), traces=len(traces),
                trace_keys=ledger, union_by_p={str(p): dict(per_layer=[v/counts[p] for v in totals[p]],
                    mean=sum(totals[p])/(40*counts[p]), windows_per_layer=counts[p]) for p in totals},
                previous_token=dict(hit_experts=reuse/pairs, recall=reuse/(6*pairs), pairs=pairs,
                    hit_histogram=hits_hist, fetched_experts=6, false_prefetch_experts=6-reuse/pairs,
                    definition='lag-one set intersection on generated positions; saved selection statistics, no predictor'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--router', type=Path, required=True)
    ap.add_argument('--out', type=Path, default=OUT/'tracejoin.json')
    ap.add_argument('--stats-record', type=Path, help='reuse an immutable prior saved-selection analysis')
    a = ap.parse_args()
    stats = read(a.stats_record)['trace_statistics'] if a.stats_record else statistics(a.router)
    assert stats['sha256'] == sha(a.router)
    old = read(INPUT / SPEC / 'v41_hbm_speculation_methods.json')
    pinned_union = read(INPUT / SPEC / 'router_union.json')
    assert stats['sha256'] == pinned_union['source']['router_pt_sha256']
    union_error = max(abs(stats['union_by_p'][str(p)]['per_layer'][l] - pinned_union['union_by_p'][str(p)]['per_layer'][l])
                      for p in range(1, 9) for l in range(40))
    assert union_error <= .000501
    wmod = load(INPUT/'tools/v41_hbm_speculation_methods.py', 'ha7_w19')
    wmod.ROOT = INPUT
    wmod.COMPOSER = INPUT / SPEC / 'inputs/w19_hbm_token_compose_71b3ffc5.py'
    w = wmod.W19()
    ladder = load(INPUT/'results/uarch/hbm_accelerator_study_20261003/ladder_model.py', 'ha7_ladder')
    program = w.prog_ctx(1048576)
    ar = w.run(program)
    assert abs(ar['total_us'] - old['contexts']['1048576']['ar_us']) < .01
    draft = w.draft(pinned_union['drafter']['union_per_stage'])
    assert abs(draft['total_us'] - old['draft']['measured_union']['total_us']) < .01
    # Keep rounded historical per-layer inputs for exact replay; report full-precision statistics separately.
    unions = {p: {l: pinned_union['union_by_p'][str(p)]['per_layer'][l] for l in range(40)} for p in range(1, 7)}
    ver = {p: w.run(program, p, unions[p]) for p in range(2, 7)}
    for p in ver:
        assert abs(ver[p]['total_us'] - old['contexts']['1048576']['verify_by_P'][str(p)]['measured_union_us']) < .01
    stream4 = w.stream_per_expert
    rows, penalties = [], []
    for stacks in (4, 2):
        w.stream_per_expert = stream4 * 4 / stacks  # ASSUMED unchanged scheduling/efficiency at half stack count.
        dr = w.draft(pinned_union['drafter']['union_per_stage'])
        for p in range(2, 7):
            v = w.run(program, p, unions[p])
            stream_delta = v['parts_us']['fetch'] - ver[p]['parts_us']['fetch']
            draft_delta = dr['total_us'] - draft['total_us']
            for replicas in range(1, p+1):
                # Same measured select latency, ceil(P/replicas) sequential waves. No free replica fanout.
                select_save = (p-math.ceil(p/replicas))*w.coll['select_cycles']*8/w.coll['hz']*1e6
                rung = {r:s for r,s,_ in ladder.ds_rungs(p, include_conditional=False)}
                # Every accelerator rung is conditional. Remove R6a and recalculate overlap on increased fetch.
                rung.pop('R6a')
                extra_hide = min(v['parts_us']['fetch'] + .256, ladder.SHARED_EXPERT_HIDE_US) - rung['R5b']
                verify_conditional = v['total_us'] - sum(rung.values()) - extra_hide - select_save
                draft_conditional = ladder.ds_draft_us(include_conditional=False) + draft_delta
                step = verify_conditional + draft_conditional
                baseline_step = v['total_us'] + dr['total_us']
                for cohort, tau in old['tau_sets'].items():
                    g = p-1
                    rate = tau[str(g)]*1e6/step
                    no_replica_step = step + select_save
                    gain = no_replica_step/step-1
                    rows.append(dict(stacks_per_die=stacks, gamma=g, verify_positions=p, replicas=replicas,
                        cohort=cohort, tau=tau[str(g)], baseline_component_step_us=baseline_step,
                        conditional_verify_us=verify_conditional, conditional_draft_us=draft_conditional,
                        conditional_step_us=step, conditional_tokens_s=rate,
                        selector_saved_us=select_save, selector_gain_fraction=gain,
                        model_gate_1pct=gain >= .01, adopt=False,
                        union_stream_penalty_us=stream_delta, draft_stream_penalty_us=draft_delta))
            penalties.append(dict(stacks_per_die=stacks, P=p, verify_fetch_us=v['parts_us']['fetch'],
                                  verify_delta_us=stream_delta, draft_delta_us=draft_delta,
                                  additional_shared_overlap_us=extra_hide))
    w.stream_per_expert = stream4
    # AR optimistic prefetch bound: free timely correct hits, linear latency scaling. Real first-byte miss
    # latency may not shrink at all when any demand expert misses; recall alone cannot establish a gain.
    recall = stats['previous_token']['recall']
    ar_conditional = ladder.ds_pass_us(1, include_conditional=False)[-1][1]
    fetch_residual = max(0, ar['parts_us']['fetch'] + .256 - ladder.SHARED_EXPERT_HIDE_US)
    prefetch = dict(lag_one_recall=recall, optimistic_saved_us=ar['parts_us']['fetch']*recall,
                    optimistic_rate_gain_fraction=ar['total_us']/(ar['total_us']-ar['parts_us']['fetch']*recall)-1,
                    conditional_shared_first_residual_us=fetch_residual,
                    conditional_incremental_saved_us=fetch_residual*recall,
                    measured_prediction_recall=None, guaranteed_saved_us=0,
                    assumption='free timely hits, linear scaling, no contention; upper sensitivity only, not adoption',
                    note='misses still pay first-access; prior-token prefetch fetches 6 experts and most are false; '
                         'HA5 shared-first can already cover all AR fetch, so do not double count',
                    predictor_requirements='GPU-only held-out recall, lead time, false-positive bytes, finite buffers, demand priority')
    best = {}
    for stacks in (4, 2):
        for cohort in old['tau_sets']:
            subset = [r for r in rows if r['stacks_per_die']==stacks and r['cohort']==cohort]
            best[f'{stacks}:{cohort}'] = max(subset, key=lambda r:r['conditional_tokens_s'])
    mixed = next(k for k in old['tau_sets'] if k.startswith('current_headline'))
    b4,b2 = best[f'4:{mixed}'],best[f'2:{mixed}']
    byte_expert = read(INPUT/'results/rtl/w19_expert_fetch.json')['layout']['die_bytes_per_expert']
    dff_tree = ast.parse((INPUT/'uarch_model_75c063d38.py').read_text())
    dff_um2 = next(ast.literal_eval(n.value) for n in dff_tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'DFF_UM2' for t in n.targets))
    replica_bits = 96 * 512 * 64
    replica_cost = [dict(replicas=r, candidate_buffer_bytes=r*replica_bits//8,
        incremental_DFF_area_lower_bound_mm2=(r-1)*replica_bits*dff_um2/1e6,
        incremental_placement_lower_bound_mm2=(r-1)*replica_bits*dff_um2/1e6/.7,
        aggregate_independent_ingress_bytes_per_cycle=64*r,
        boundary_bits_per_cycle=512*r, demux_destinations=r, output_mux_sources=r, command_fanout=r,
        minimum_load_cycles_per_position=replica_bits//512,
        minimum_load_us_per_position=replica_bits//512/w.coll['hz']*1e6,
        cost_status='HA5 register-buffer lower bound; excludes logic/mux/clock/route; no fit claim') for r in range(1,7)]
    record = dict(schema='opentallas.hbm_accel_speculation.v1', source_commit=subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), status='COMPONENT COMPOSITION + CONDITIONAL SENSITIVITY; NOT ADOPTED',
        host='local CPU, saved selections only; no inference/RTL/P&R', enabled_by_default=False,
        inputs_sha256={str(p.relative_to(OUT)):sha(p) for p in sorted(INPUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts},
        source_authorities=dict(speculation_commit='d2aff19ef', inherited_pricing_commit='75c063d38',
            actual_union_rtl_owner='Sagan 01a0fa84-2959-7963-b1d4-b377be694aee',
            shared_first_selector_owner='Einstein 01a101f7-ff9c-72a1-b0aa-4359f70a01da'),
        trace_statistics=stats, replay=dict(ar_us=ar['total_us'], draft_us=draft['total_us'],
            verify_by_P=ver, max_union_rounding_error=union_error, cases=7, mismatches=0),
        measured_vs_assumed=dict(measured='saved GPU router selections; original RTL SM cases, select cycles, fetch cycles',
            composition='W19 element composition, NOT a measured full accelerator token',
            assumed='2-stack linear bandwidth scaling; unchanged select-wave timing with replicas; transferred '
                     'HA1/2/3/4 improvements, HA5 shared overlap, proportional draft collective speedup',
            trace_applicability='union samples are greedy continuation windows, not rejected draft-position router paths; verify-union proxy remains conditional; mixed_n36 tau differs from agentic_n30 router sample',
            excluded='R7a faster serial clock; new predictor; any unmeasured actual DS20/union SM successor'),
        selector=dict(cycles=w.coll['select_cycles'], hz=w.coll['hz'], index_layers=8,
            replica_costs=replica_cost, routing_tracks=None, channel_capacity=None, SS_WNS=None, FF_WNS=None,
            ingress_warning='419 cycles is go-to-done AFTER gathered-candidate load; do not count replica waves as system gain without measured concurrent ingress',
            physical_gate='NOT RUN; Einstein owns implementation; any hardware remains unready pending priced fit'),
        stream=dict(measured_us_per_expert_4stacks=stream4, two_stack_scaling='ASSUMED 2x',
            die_bytes_per_expert=byte_expert, best_mixed_two_stack_rate_penalty=1-b2['conditional_tokens_s']/b4['conditional_tokens_s'],
            study_assumed_penalty=.04, delta_from_study_fraction=(1-b2['conditional_tokens_s']/b4['conditional_tokens_s'])-.04,
            penalties=penalties), prefetch=prefetch, best_by_stacks_cohort=best, sweep=rows,
        conditional_ar_us=ar_conditional, flags=draft['flags'],
        implementation_gate=dict(adopt=False, new_RTL=False, exact='historical replay only; new hardware NOT RUN',
            physical='NOT RUN', gain='conditional model only; measured system gain pending owners'))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.exists():
        raise FileExistsError(f'Preserve prior run: choose a new --out path: {a.out}')
    a.out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(best4=b4,best2=b2,prefetch=prefetch,stream=record['stream']['best_mixed_two_stack_rate_penalty']),indent=2))


if __name__ == '__main__':
    main()
