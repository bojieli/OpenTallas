#!/usr/bin/env python3
"""Join literal FIELD allocations to actual first-pass instances; never infer timing."""
import argparse, collections, gzip, hashlib, json
from pathlib import Path
from canonical_layout import load


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bind_pairs(insts, layout):
    byname = {i['name']: i for i in insts}
    assert len(byname) == len(insts), 'duplicate instance name'
    pairs = {}
    for root, frame in layout['frames'].items():
        for pair in range(*frame['pairs']):
            bf = pair in layout['bf_ids']
            required = {f'e{pair}': 'dsfd_bf_front_static' if bf else 'ot_v41_rom_elem_q_qxpq_w10',
                        f's{pair}': 'ot_s81_cfg7_seq_bfp' if bf else 'ot_s81_cfg7_seq',
                        **{f'c{pair}_{j}': 'ot_rom_4096x72_m8' for j in range(7)}}
            if bf:
                required.update({f'e{pair}w': 'dsfd_bf_col', f'e{pair}e': 'dsfd_bf_col'})
            children = []
            for name, master in required.items():
                assert name in byname, ('missing actual FIELD child', name)
                i = byname[name]
                assert i['master'] == master, ('unexpected FIELD master', name, i['master'], master)
                assert i['region'] == f'frame_{root}', ('FIELD root mismatch', name, i['region'], root)
                # Actual children must lie inside the source-pinned coarse frame.
                x, y = frame['origin_um']; w, h = frame['outline_um']
                assert i['x'] >= x - .001 and i['y'] >= y - .001, ('outside frame', name)
                assert i['x'] + i['w'] <= x + w + .001 and i['y'] + i['h'] <= y + h + .001, ('outside frame', name)
                children.append(i)
            pairs[pair] = dict(pair_id=pair, root_id=root, bf=bf, actual_children=children)
    assert set(pairs) == set(range(layout['pair_count']))
    return pairs



def bind_cfg_ports(buses, pairs):
    byname = {b[0]: b for b in buses}
    assert len(byname) == len(buses), 'duplicate actual bus name'
    count = 0
    for p in pairs:
        required = [(f'ra_{p}', 12, {(f's{p}', 'a'), *((f'c{p}_{j}', 'a') for j in range(7))})]
        for j in range(7):
            required.extend([(f'rc_{p}_{j}', 1, {(f's{p}', f'ce{j}'), (f'c{p}_{j}', 'ce')}),
                             (f'rq_{p}_{j}', 72 if pairs[p]['bf'] else 48, {(f'c{p}_{j}', 'rd'), (f's{p}', f'q{j}')})])
        for name, width, endpoints in required:
            assert name in byname, ('missing actual CFG bus', name)
            b = byname[name]
            assert b[2] == width and {tuple(e) for e in b[3]} == endpoints, ('actual CFG port mismatch', name)
            count += 1
        pairs[p]['actual_cfg_buses'] = [byname[name] for name, _, _ in required]
    return count


def run(a):
    a.out.mkdir(parents=True, exist_ok=False)
    plan = json.load(gzip.open(a.plan, 'rt'))
    assert plan['scope'] == 'FIRST_PASS_PRE_HOP_PRE_FINAL_PINS_NOT_USABLE_FOR_QUALIFICATION'
    layout = load(a.layout.resolve(), a.root.resolve())
    pairs = bind_pairs(plan['insts'], layout)
    cfg_buses = bind_cfg_ports(plan['buses'], pairs)
    verdict = json.loads(a.verdict.read_text())
    assert verdict['decoder_matrix_capacity_PASS'] and not verdict['failures']
    assert verdict['counts']['declarations'] == verdict['counts']['placed']
    stage = json.loads((a.root / layout['stage_map']).read_text())
    nstages = len(stage['PHW_required_by_stage'])
    assert len(stage['rank_dies']) == 4*nstages
    assert {(d['stage'],d['rank']) for d in stage['rank_dies']} == {(s,r) for s in range(nstages) for r in range(4)}
    assert len({d['die_id'] for d in stage['rank_dies']}) == 4*nstages
    allocator_matches = {}
    for name in ('stage_map.json','providers.json','inventory.json','mapping_verdict.json','home_order_check.json','auxiliary_obligations.json'):
        expected=(a.root/layout['stage_map']).parent/name
        actual=a.matrices.parent/name
        assert json.loads(expected.read_text()) == json.loads(actual.read_text()), ('allocator does not match placed topology', name)
        allocator_matches[name]=dict(expected_sha256=sha(expected),actual_sha256=sha(actual),json_equal=True)
    groups = collections.defaultdict(list); phases = collections.Counter(); fragments = plans = 0
    with gzip.open(a.out/'pairs.jsonl.gz', 'wt') as dest:
        for p in sorted(pairs): dest.write(json.dumps(pairs[p], separators=(',', ':'))+'\n')
    with gzip.open(a.matrices, 'rt') as source, gzip.open(a.out/'field_fragment_homes.jsonl.gz', 'wt') as dest:
        for line in source:
            m = json.loads(line); s = m['stage']
            assert m['compiled_NP'] == len(pairs) and 0 <= s < nstages
            phase = phases[s]; phases[s] += 1
            assert phase < 1024
            used = set(); roots = set()
            for segment, pair, first, n, stride, start, words in m['plans']:
                assert pair in pairs and pair not in used
                assert m['format'] != 'bf16' or pairs[pair]['bf'], ('BF allocation on Q hardware', pair)
                used.add(pair); root = pairs[pair]['root_id']; roots.add(root)
                assert all((first+j*stride) % 128 == root for j in range(n))
                plans += 1
            entry = dict(fragment=fragments, layer=m['layer'], alias=m['alias'], stage=s, phase=phase,
                         matrix_sha256=hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',', ':')).encode()).hexdigest(),
                         allocated_pair_ids=sorted(used), root_ids=sorted(roots),
                         actual_engine_refs=[dict(pair_id=p, engine=f'e{p}', sequencer=f's{p}', cfg7=[f'c{p}_{j}' for j in range(7)]) for p in sorted(used)],
                         rank_slices=m['rank_slices'], physical_owner_ranks=m.get('physical_owner_ranks',list(range(4))),
                         final_die_instance_bound=False, cycle_bound=False, native_qualified=False)
            dest.write(json.dumps(entry,separators=(',', ':'))+'\n')
            groups[m['layer'],m.get('original_alias',m['alias'])].append(dict(fragment=fragments,stage=s,phase=phase,alias=m['alias']))
            fragments += 1
    assert fragments == verdict['counts']['declarations']
    missing=[]; nodes=refs=0
    with gzip.open(a.bindings,'rt') as source,gzip.open(a.out/'source_field_operation_homes.jsonl.gz','wt') as dest:
        for line in source:
            b=json.loads(line)
            if not b.get('address_bound'): continue
            nodes+=1; choices=[]
            for c in b['phase_choices']:
                allocated=groups.get((b['layer'],c['alias']))
                if not allocated: missing.append(dict(node=b['node'],layer=b['layer'],alias=c['alias'])); continue
                choices.append(dict(source_alias=c['alias'],expert=c.get('expert'),fragments=allocated)); refs+=4*len(allocated)
            dest.write(json.dumps(dict(node=b['node'],template_sha256=b['template_word_sha256'],canonical_choices=choices,required_ranks=[0,1,2,3],runtime_selection_bound=False,cycle_bound=False,native_qualified=False),separators=(',', ':'))+'\n')
    report=dict(schema='opentallas.s81.first-pass-literal-field-join.v1',status='STRUCTURAL_FIELD_JOIN_PASS' if not missing else 'STRUCTURAL_FIELD_JOIN_FAIL',
                qualified=False,source_commit=plan['source_commit'],generator_sha256=plan['generator_sha256'],plan_scope=plan['scope'],
                sources={str(p):sha(p) for p in [a.plan,a.layout,a.matrices,a.verdict,a.bindings,Path(__file__)]},
                counts=dict(actual_instances=len(plan['insts']),actual_buses=len(plan['buses']),bound_cfg_buses=cfg_buses,pairs=len(pairs),bf_pairs=len(layout['bf_ids']),roots=len(layout['frames']),stages=nstages,required_rank_dies=4*nstages,fragments=fragments,plans=plans,source_field_nodes=nodes,rank_fragment_references=refs),
                allocator_matches=allocator_matches,phase_counts=dict(phases),missing=missing,
                unbound=['final emitted die hierarchy and rank instance identities','final pins/hops/clock/reset and transfer cycles','native ROM operand/result ports and programmes','SU and HCX actual producer homes','runtime expert selection','static resource/commit calendar and native throughput'])
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('sources','phase_counts','missing')}))
    return bool(missing)


def main():
    p=argparse.ArgumentParser()
    for name in ('plan','layout','matrices','verdict','bindings','out','root'): p.add_argument('--'+name,type=Path,required=True)
    return run(p.parse_args())

if __name__=='__main__': raise SystemExit(main())
