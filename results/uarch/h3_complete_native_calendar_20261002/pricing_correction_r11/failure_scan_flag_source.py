#!/usr/bin/env python3
"""Pinned, additive pricing corrections; no adoption or full-shape latency claim."""
import argparse
import ast
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'results/uarch/h3_complete_native_calendar_20261002/pricing_correction_r11'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_inputs(directory):
    manifest = json.loads((directory / 'input_manifest.json').read_text())
    result = {}
    for key, spec in manifest['inputs'].items():
        data = (directory / spec['archive']).read_bytes()
        if sha(data) != spec['sha256']:
            raise ValueError('source hash mismatch: ' + key)
        result[key] = data
    return result


def solve(nodes, sink):
    """Same recurrence as frozen Graph.solve(True), including wire latency."""
    finish, start, critical = {}, {}, {}
    for name, n in nodes.items():
        if any(d not in finish for d in n['deps']):
            raise ValueError('unresolved/non-topological dependency: ' + name)
        for k in ('issue', 'depth', 'ctrl', 'wire_in', 'wire_out'):
            if not math.isfinite(n.get(k, 0)) or n.get(k, 0) < 0:
                raise ValueError('invalid cost: ' + name)
        parent = max(n['deps'], key=finish.__getitem__) if n['deps'] else None
        pf = finish[parent] if parent else 0
        ps = max((start[d] for d in n['deps']), default=0)
        s = (ps if n['stream'] and n['deps'] else pf) + n['ctrl']
        f = (max(s + n['issue'], pf) if n['stream'] and n['deps'] else s + n['issue']) + n['depth']
        start[name] = s + n.get('wire_in', 0)
        finish[name] = f + n.get('wire_in', 0) + n.get('wire_out', 0)
        critical[name] = parent
    path, n = [], sink
    while n is not None:
        path.append(n)
        n = critical[n]
    return finish[sink], path[::-1]


def local_select_cost(beats, tail, occupancy, users=1, units=1):
    """Separate input service, last-input tail and segment reuse occupancy.

    A cohort waits for prior cohorts to free their tables. The first cohort's
    tail belongs in depth exactly once, not also in issue. No scorer overlap.
    """
    if min(beats, tail, occupancy, users, units) <= 0 or occupancy < beats + tail:
        raise ValueError('invalid finite select segment')
    rounds = math.ceil(users / units)
    return {'issue': max(beats * users, (rounds - 1) * occupancy + beats),
            'depth': tail, 'occupancy': occupancy, 'cohorts': rounds,
            'stream': False}


def local_select_successor(source, timing, latency, corrected=True):
    """Compile the retained literal Ops method with one bounded issue correction.

    No imported canonical module or global is mutated. The old expression must
    match exactly before this successor can bind the source implementation.
    """
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Ops')
    method = copy.deepcopy(next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                               and n.name == 'tselect_local'))
    assignments = [n for n in ast.walk(method) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'issue' for t in n.targets)]
    expected = ast.parse('max(beats * self.mb, math.ceil(self.mb / units) * occ)', mode='eval').body
    if len(assignments) != 1 or ast.dump(assignments[0].value) != ast.dump(expected):
        raise ValueError('changed direct local-select issue source')
    replacement = ast.parse(
        'max(beats * self.mb, (math.ceil(self.mb / units) - 1) * occ + beats)', mode='eval').body
    if corrected:
        assignments[0].value = replacement
    namespace = {'math': math, 'TS': timing, 'tselect_latency': latency}
    module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
    exec(compile(module, '<source-bound-local-select-successor-r11>', 'exec'), namespace)
    return namespace['tselect_local']


def direct_select_replay(inputs, config, ctx):
    sc = json.loads(inputs['select_scale'])
    cd = json.loads(inputs['select_candidate'])
    ship = next(c for c in cd['configurations'] if c['name'] == 'candidate_shipped_p64_wb64')
    timing = dict(lanes=sc['parameters']['W'], lat0=sc['parameters']['lat0'],
                  cand_score_lanes=ship['score_lanes'], cand_lanes=ship['tselect_lanes'],
                  cand_front=ship['lat0'] - sc['parameters']['lat0'])
    latency = lambda n: 2 * math.ceil(n / timing['lanes']) + timing['lat0']
    source = inputs['decoder'].decode()
    cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'Params')
    default = next(ast.literal_eval(n.value) for n in cls.body if isinstance(n, ast.AnnAssign)
                   and isinstance(n.target, ast.Name) and n.target.id == 'select_units')
    class GraphCapture:
        def add(self, name, deps, **kw):
            return kw
    class OpsCapture:
        g = GraphCapture()
        mb = 1
        bctrl = 0
        cyc = staticmethod(float)
    ops = OpsCapture()
    ops.p = type('P', (), {'select_units': default, 'tselect_units': 0})()
    old = local_select_successor(source, timing, latency, corrected=False)
    new = local_select_successor(source, timing, latency)
    rows = []
    for layer, mode in config['modes'].items():
        if not mode['scans_index']:
            continue
        n = ctx // config['compress_ratios'][int(layer)]
        cap = mode.get('index_scan_entries_cap') or n
        n = math.ceil(min(n, cap) / 4)
        variants = [False, True] if int(layer) == config['candidate_source_layer_id'] else [False]
        for cand in variants:
            k = config['candidate_topk_blocks'] if cand else config['index_topk']
            args = dict(n=n, k=k, cand=cand)
            a, b = old(ops, 'capture', [], int(layer), **args), new(ops, 'capture', [], int(layer), **args)
            rows.append({'layer': int(layer), 'candidate': cand, 'positions_per_die': n,
                         'source_units_selected': a['tselect_units'],
                         'old_issue_cycles': a['issue'], 'corrected_issue_cycles': b['issue'],
                         'tail_cycles': b['depth'], 'scorer_overlap': False})
    return rows


def bind_candidates(nodes, config):
    nodes = copy.deepcopy(nodes)
    src = f"L{config['candidate_source_layer_id']}.attn.cand.final"
    if src not in nodes:
        raise ValueError('missing candidate publication')
    consumers = []
    for layer, mode in config['modes'].items():
        if mode['mode'] != 'reindex':
            continue
        name = f'L{layer}.attn.idx.score'
        if name not in nodes:
            raise ValueError('missing candidate consumer: ' + name)
        if src not in nodes[name]['deps']:
            nodes[name]['deps'].append(src)
        consumers.append(name)
    if not consumers:
        raise ValueError('dangling candidate final')
    return nodes, consumers


def emitter_contract(source):
    tree = ast.parse(source)
    # Actual nested expert closure, not incidental documentation strings.
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    closure = funcs['project_gate_up']
    calls = [n for n in ast.walk(closure) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == 'linq']
    paired = [n for n in calls if '"w1"' in ast.unparse(n).replace("'", '"')
              or '"w3"' in ast.unparse(n).replace("'", '"')]
    if len(paired) != 2 or any('XN' not in ast.unparse(n) for n in paired):
        raise ValueError('changed gate/up same-x emitter contract')
    attn = funcs['attention']
    acalls = [n for n in ast.walk(attn) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == 'linq']
    acalls = [n for n in acalls if any(k in ast.unparse(n) for k in ('wq_a', 'wkv'))]
    if len(acalls) != 2 or any('XN' not in ast.unparse(n) for n in acalls):
        raise ValueError('changed attention same-x emitter contract')
    literal = ast.unparse(tree)
    for required in ('sh = expert(m.k_exp)', 'sh[0]()', 'ex = [expert(k) for k in range(m.k_exp)]',
                     'ex[0][0]()', 'ex[1][0]()', 'ex[k + 2][0]()'):
        if required not in literal:
            raise ValueError('changed routed/shared repetition source: ' + required)
    return {'gate_up': [ast.unparse(n) for n in paired],
            'attention': [ast.unparse(n) for n in acalls]}


def phase_nodes(nodes, config, clock, costs):
    """Exposed serial second-phase sensitivity, routed by existing consumers.

    Small-field differential costs are calibration parameters, not bounds on
    the full-shape phase. Every inserted phase waits for its predecessor's last
    result, so phase completion cannot be hidden by generic stream overlap.
    """
    if clock <= 0 or any(not math.isfinite(v) or v <= 0 for v in costs.values()):
        raise ValueError('unknown/invalid phase calibration')
    additions, aliases, ledger = {}, {}, []
    for layer in range(config['num_layers']):
        for suffix, count, family in [('attn.a_proj', 1, 'a_proj'),
                                      ('ffn.shared_gu', 1, 'gate_up'),
                                      ('ffn.experts_gu', config['experts_per_token'], 'gate_up')]:
            source = f'L{layer}.{suffix}'
            if source not in nodes:
                raise ValueError('missing priced source phase: ' + source)
            parent = source
            additions[source] = []
            for repetition in range(count):
                name = source + f'.asbuilt_second_phase{repetition}'
                node = {'deps': [parent], 'issue': costs[family] / clock,
                        'depth': 0.0, 'ctrl': 0.0, 'stream': False,
                        'kind': 'calibrated_phase_delta', 'layer': layer}
                additions[source].append((name, node))
                ledger.append({'name': name, 'source': source, 'family': family,
                               'repetition': repetition, 'deps': [parent],
                               'cycles': costs[family], 'same_x': 'XN'})
                parent = name
            aliases[source] = parent
    result = {}
    for name, original in nodes.items():
        n = copy.deepcopy(original)
        n['deps'] = [aliases.get(d, d) for d in n['deps']]
        result[name] = n
        for newname, extra in additions.get(name, []):
            result[newname] = extra
    return result, ledger


def qwen_calibration(receipt):
    if receipt['status'] != 'pass':
        raise ValueError('Qwen receipt failed')
    a, b, c = (receipt['runs'][key] for key in 'ABC')
    if a['ar256_images'] or not b['ar256_images'] or a['coll_depth'] != b['coll_depth']:
        raise ValueError('unmatched Qwen geometry')
    if a['binary_sha256'] != b['binary_sha256']:
        raise ValueError('unmatched Qwen binary')
    if any(r['mismatches'] or not r['source_stable'] for r in (a,b,c)):
        raise ValueError('Qwen numerical/source refusal')
    if not a['x_sha256'] == b['x_sha256'] == c['x_sha256']:
        raise ValueError('Qwen payload mismatch')
    return {'split128_cycles': a['cycles'], 'one256_cycles': b['cycles'],
            'saved_cycles': {k: a['cycles'][k] - b['cycles'][k] for k in a['cycles']},
            'depth256_cycles': c['cycles'], 'scope': 'matched L0/L1 functional component only',
            'headline_adoption': False, 'physical_qualification': False}


def build(inputs):
    snapshot = json.loads(inputs['graph'])
    config, nodes, clock = snapshot['config'], snapshot['nodes'], snapshot['row']['clock_hz']
    contract = emitter_contract(inputs['emitter'].decode())
    baseline, _ = solve(nodes, snapshot['sink'])
    if abs(baseline * 1e6 - snapshot['row']['T_us']) > 1e-8:
        raise ValueError('graph/producer baseline mismatch')
    measurement = json.loads(inputs['phase_measurement'])
    if measurement['status'] != 'pass' or measurement['golden_mismatch'] != 0:
        raise ValueError('failed phase calibration')
    cases = {r['name']: r for r in measurement['cases']}
    for family in measurement['ab'].values():
        split = sum(cases[n]['wall_cycles_rtl'] for n in family['split'])
        merged_cost = cases[family['merged']]['wall_cycles_rtl']
        if (not family['rows_bit_identical_split_vs_merged'] or
                split != family['split_wall_cycles'] or merged_cost != family['merged_wall_cycles'] or
                split - merged_cost != family['saved_cycles']):
            raise ValueError('inconsistent phase differential calibration')
    costs = {k: measurement['ab'][name]['saved_cycles'] for k, name in
             [('gate_up','expert_gate_up'),('a_proj','attn_a_proj')]}
    fixed, consumers = bind_candidates(nodes, config)
    merged, _ = solve(fixed, snapshot['sink'])
    split, ledger = phase_nodes(fixed, config, clock, costs)
    asbuilt, path = solve(split, snapshot['sink'])
    historical = next(r for r in json.loads(inputs['historical_row'])['rows'] if r['design'] == 'proposal')
    if historical['clock_hz'] != clock:
        raise ValueError('historical/graph clocks differ: cannot transfer cycles')
    cycles = sum(n['cycles'] for n in ledger)
    return {'schema': 'native-calendar.pricing-correction.r11', 'headline_adoption': False,
            'producer_baseline': snapshot['row'],
            'historical_3809_row': historical,
            'authority_gap_us': baseline*1e6 - historical['T_us'],
            'current_source_DAG_cases_us': {'unchanged': baseline*1e6,
                'candidate_bound_merged_pairs': merged*1e6,
                'candidate_bound_two_phase_sensitivity': asbuilt*1e6},
            'phase_calibration_cycles': costs, 'phase_pair_count': len(ledger),
            'phase_exposed_serial_sum_cycles': cycles,
            'current_DAG_exposed_delta_cycles': (asbuilt - merged) * clock,
            'historical_exposed_serial_assumption': 'all 320 paired phase deltas exposed; not full-shape bound',
            'historical_3809_exposed_sensitivity_us': historical['T_us'] + cycles/clock*1e6,
            'candidate_consumers': consumers, 'emitter_contract': contract,
            'phase_ledger': ledger, 'sensitivity_critical_path': path,
            'literal_direct_select_cases': direct_select_replay(inputs, config, snapshot['row']['ctx']),
            'select_correction': {'direct_Ops': 'issue=max(ingress, preceding-cohort occupancy+ingress); depth=tail once',
                'architecture_proposal': 'arch_budget._select_price already replaces direct Ops issue/depth; no duplicate subtraction',
                'scorer_overlap_adopted': False},
            'qwen': qwen_calibration(json.loads(inputs['qwen_measurement'])),
            'unknowns': ['small-field phase differential transfer to full shape is not a measured bound',
                'six routed experts still grouped into one base phase; five extra phases/layer not closed by pair merge',
                'attention base phase also fuses index/compressor weights beyond the wq_a/wkv pair',
                'candidate dependency is source model contract; complete runtime reindex consumption not qualified',
                'current-source graph differs from historical 3809 row; scalar historical sensitivity is not a historical DAG replay',
                'whole token endpoint ownership/CDC/backpressure and SS/FF timing remain unqualified']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=DEFAULT)
    p.add_argument('--verify', action='store_true')
    args = p.parse_args()
    record = build(load_inputs(args.out))
    data = (json.dumps(record, indent=2, sort_keys=True) + '\n').encode()
    target = args.out / 'model.json'
    if args.verify:
        if target.read_bytes() != data:
            raise ValueError('cold pricing replay mismatch')
    else:
        if target.exists():
            raise ValueError('refuse overwrite of evidence')
        target.write_bytes(data)
    print(json.dumps({'verify': args.verify, 'sha256': sha(data), 'pairs': record['phase_pair_count'],
                      'cycles': record['phase_exposed_serial_sum_cycles'],
                      'cases_us': record['current_source_DAG_cases_us'], 'headline_adoption': False}))

if __name__ == '__main__':
    main()
