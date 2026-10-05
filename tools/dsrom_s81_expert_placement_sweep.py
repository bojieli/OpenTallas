#!/usr/bin/env python3
"""Opt-in, source-only concurrent-expert enumeration; no payload or RTL execution.

Retain the existing dsrom_1m_field plan's ordered phases, per-region placement,
rank slices and measured serialization rule. Enumerate all set partitions of
six selected experts onto fresh full S81 TP4 groups. Canonical residents remain
priced and intact. Only ROM bases change on the additional groups; every source
word has a literal interval translation. No disjoint-subregion assumption.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAN = ROOT / 'results/uarch/dsrom_s81_released_binding_20261004/canonical'
REC = ROOT / 'results/rtl/dsrom_recovery_20261004'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read(p):
    if str(p).endswith('.gz'):
        with gzip.open(p, 'rt') as f:
            return json.load(f)
    return json.loads(Path(p).read_text())


def partitions(items):
    """All 203 unlabeled partitions, each with source-ordered expert members."""
    if not items:
        yield []
        return
    first, *rest = items
    for parts in partitions(rest):
        yield [[first]] + parts
        for i in range(len(parts)):
            yield parts[:i] + [[first] + parts[i]] + parts[i + 1:]


def serial(phases, measured, wire):
    """Exactly dsrom_1m_field.cmd_record: idle+1 except last VM write, wire/phase."""
    if not phases:
        return dict(phases=[], phase_count=0, measured_cycles=0, wire_cycles=0,
                    total_cycles=0, us=0)
    pp = [measured[p['phase']] for p in phases]
    body = sum(p['go_to_idle_cycles'] + 1 for p in pp[:-1]) + pp[-1]['go_to_last_row_cycles']
    total = body + len(pp) * wire
    return dict(phases=[p['phase'] for p in phases], phase_count=len(pp),
                measured_cycles=body, wire_cycles=len(pp) * wire,
                total_cycles=total, us=total / 1200)


def catalogue(entries, experts, npairs, depth):
    """A single fresh-die image catalogue per expert subset, shared by partitions.

    plans are [segment,pair,superrow,count,stride,source_base,words_per_superrow].
    Relocate each full run contiguously on the SAME pair, preserving run and word
    order. The two macro row halves share this allocation; TP4 uses actual slices.
    """
    fill = [0] * npairs
    spans = []
    for e in entries:
        if e['expert'] not in experts:
            continue
        for seg, pair, sr, count, stride, base, words in e['plans']:
            target = fill[pair]
            fill[pair] += count * words
            spans.append(dict(tensor=e['tensor'], alias=e['alias'], expert=e['expert'],
                source_stage=e['stage'], segment=seg, pair=pair, superrow=sr,
                count=count, stride=stride, words_per_superrow=words,
                source_base=base, destination_base=target,
                rank_slices=e['rank_slices']))
    violations = [dict(pair=i, words=v, capacity=depth) for i, v in enumerate(fill) if v > depth]
    return dict(experts=experts, regions=list(range(128)), pairs_occupied=sum(v > 0 for v in fill),
        max_pair_words=max(fill), used_pair_words=sum(fill), pair_word_capacity=depth,
        die_pair_words_capacity=npairs * depth, physical_ROM4096_macros_per_rank_die=4*npairs,
        max_pair_fill_fraction=max(fill)/depth, capacity_fit=not violations,
        capacity_violations=violations, translation=spans,
        translation_rule='destination_base + k*words_per_superrow + j <- '
                         'source_base + k*words_per_superrow + j, '
                         '0<=k<count, 0<=j<words_per_superrow; same pair, segment, '
                         'superrow, rank slice, two row-half macros, released tensor identity')


def run(a):
    plan, field, stage, inv = map(read, (a.plan, a.field, a.stage_map, a.inventory))
    floor, links = read(a.floorplan), read(a.links)
    assert inv['stages'] == 81 and inv['pairs_per_rank_die'] == 2417 and inv['TP'] == 4
    assert len(stage['region_bounds']) == 129 and len(stage['BF_site_IDs']) == 519
    assert field['status'] == 'pass'
    assert plan['region_bounds'] == stage['region_bounds']
    # The retained plan includes the historical R93 BF change. Expert matrices are
    # FP4 and checked literally against the canonical map below; no R93 adoption.
    measured = {p['phase']: p for p in field['phases']}
    by_layer = {}
    for L in (3, 20):
        exps = plan['experts'][str(L)]
        assert len(exps) == len(set(exps)) == 6
        phases = [p for p in plan['phases'] if p['layer'] == L and
                  any(p['group'] == f'exp{e}.{kind}' for e in exps for kind in ('gu', 'w2'))]
        assert len(phases) == 12
        by_layer[L] = dict(experts=exps, phases=phases, entries=[])
    with gzip.open(a.matrix_map, 'rt') as f:
        for ln in f:
            e = json.loads(ln)
            L = e.get('layer')
            if L in by_layer and e.get('expert') in by_layer[L]['experts']:
                by_layer[L]['entries'].append(e)
    wire = 2*floor['trunk_stages']['stages_at_504']['field_one_way'] - 2
    assert wire == 80
    out = dict(schema='opentallas.dsrom.s81.expert-placement-enumeration.v1',
        adopted=False, RTL_or_inference_executed=False, source_commit=a.source_commit,
        source_sha256={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p)
                       for p in (a.plan,a.field,a.stage_map,a.inventory,a.matrix_map,a.floorplan,a.links,
                                 Path(__file__),ROOT/'tools/dsrom_1m_field.py')},
        retained_plan_uncompressed_sha256=hashlib.sha256(gzip.decompress(a.plan.read_bytes())).hexdigest(),
        clock_GHz=1.2, rank=0, TP=4,
        timing_rule='dsrom_1m_field.cmd_record: sum(idle+1) except last go->VM-visible '
                    'last row write; +80 S81 floorplan wire cycles per phase; max over dies per node',
        calibration='Exact retained per-phase region geometry, segment/operator order and output '
                    'row count; base relocation does not change that geometry. Calendar is analytical '
                    'reuse, not a measurement of a multi-die caller or changed consumer.',
        canonical_cost_retained=dict(layer_dies=inv['layer_dies'], canonical_ROM_words=inv['used_logical_words_per_stage'],
                                    no_original_payload_deleted=True), layers=[])
    for L, data in by_layer.items():
        exps, phases, entries = data['experts'], data['phases'], data['entries']
        assert len(entries) == 18
        source_index = {(e['tensor'][:-7], e['stage']): e for e in entries}
        for ph in phases:
            assert ph['out'] == 'bf16' and ph['fmts'] == ['fp4']
            assert ph['regions'] == list(range(128))
            assert measured[ph['phase']]['exact']
            assert measured[ph['phase']]['die_stage'] == ph['stage']
            for m in ph['mats']:
                e = source_index[(m['tensor'], ph['stage'])]
                placements = {}
                for seg,pair,sr,count,stride,base,words in e['plans']:
                    assert 0 <= pair < 2417 and base+count*words <= 8192
                    for k in range(count):
                        row=sr+k*stride
                        r=row%128
                        assert stage['region_bounds'][r] <= pair < stage['region_bounds'][r+1]
                        placements.setdefault(str(r),[]).append([row,seg,pair])
                assert {r:sorted(v) for r,v in placements.items()} == m['regions']
                assert e['segments'] == m['segments'] and e['rank_slices'][0]['rows'] == m['rows']
        # Full original nodes retain the shared-expert down phase and other dies.
        baseline=[]
        for n in field['nodes']:
            if n['layer'] == L and n['node'] in (f'L{L}.ffn.experts_gu', f'L{L}.ffn.down'):
                pp=[p for p in plan['phases'] if p['phase'] in n['phases']]
                c=serial(pp,measured,wire)
                assert c['measured_cycles'] == n['measured_cycles']
                assert abs(c['us']-n['total_us_s81_floorplan_wire']) < 1e-12
                baseline.append(dict(node=n['node'],stage=n['die_stage'],**c))
        shared_phases=[p for p in plan["phases"] if p["layer"]==L and p["group"]=="shared.w2"]
        shared=serial(shared_phases,measured,wire)
        candidates, catalogues = [], {}
        for index, groups in enumerate(partitions(exps)):
            groups=sorted(groups,key=lambda g:exps.index(g[0]))
            placed=[]
            for i,g in enumerate(groups):
                key=','.join(map(str,g))
                if key not in catalogues:
                    catalogues[key]=catalogue(entries,g,2417,8192)
                by_node={}
                for node in ('ffn.experts_gu','ffn.down'):
                    pp=[p for p in phases if p['node']==node and any(p['group'].startswith(f'exp{e}.') for e in g)]
                    by_node[node]=serial(pp,measured,wire)
                placed.append(dict(group=f'L{L}.candidate{index}.group{i}',experts=g,
                    physical_rank_dies=[f'L{L}.candidate{index}.group{i}.rank{r}' for r in range(4)],
                    ROM_catalogue=key, phases=by_node))
            field_cyc=sum(max(g['phases'][n]['total_cycles'] for g in placed)
                          for n in ('ffn.experts_gu','ffn.down'))
            for c in (catalogues[g['ROM_catalogue']] for g in placed):
                assert c['capacity_fit']
            # Native VM transports raw32 scalars. Draft x_row is packed BF16,
            # not a bound transport for this field's raw32 input. Keep it only
            # as a conditional reference. ret_row matches 1280 raw32 words.
            x,ret=links['hops']['x_row'],links['hops']['ret_row']
            assert x['payload_B']==5120*2 and ret['payload_B']==1280*4
            candidates.append(dict(id=index, groups=placed, group_count=len(groups),
                added_TP4_groups=len(groups),added_dies=4*len(groups),
                added_die_body_mm2=4*len(groups)*floor['die']['decision_priced_mm2'],
                die_body_price_source='floorplan.die.decision_priced_mm2; excludes unbound extra endpoint/clock costs',
                capacity_fit=True, global_phases=sum(g['phases'][n]['phase_count'] for g in placed for n in g['phases']),
                longest_die_phases_per_node=max(len(g['experts']) for g in placed),
                field_node_barrier_calendar_cycles=field_cyc,
                field_node_barrier_calendar_us=field_cyc/1200,
                shared_down_unchanged=shared,
                node_barrier_policy='all expert GU phases complete before dependent SU/quant and down node; '
                                    'consumer costs retained but unbound; no invented overlap',
                total_source_bound_latency_us=None, physical_admission=False,
                network=dict(primary_bidirectional_ports_per_rank=len(groups),
                    fresh_group_ports_per_rank=1, total_new_bidirectional_endpoints=8*len(groups),
                    source_provider_stage=stage['provider_homes'][str(L)],
                    x_input=dict(raw_VM_bytes_per_rank=20480, multicast_copies=len(groups),
                        source_bound_hop_cycles=None, packed_BF16_reference_bytes=10240,
                        conditional_reference_hop_cycles=x['total_cycles'],
                        conditional_reference='requires actual source-owned exact BF16 pack/unpack; absent',
                        reference_wire_cycles=x['wire_stage_cycles'], placement_loaded_wire_cycles=None),
                    returned_down=dict(bytes_per_expert_per_rank=5120, copies=6,
                        measured_isolated_hop_cycles=ret['total_cycles'],
                        representation='1280 raw32 VM scalars with BF16-lifted field results',
                        reference_wire_cycles=ret['wire_stage_cycles'], placement_loaded_wire_cycles=None),
                    GU_return=dict(raw_VM_bytes_per_expert_per_rank=4608, copies=6, cycles=None),
                    W2_input=dict(raw_VM_bytes_per_expert_per_rank=9216, copies=6, cycles=None),
                    identities=dict(expert_ids=exps, route_weight_bytes=24,
                        packet_framing_cycles=None, producer_PC='retained per-matrix ISA PC where present'),
                    credit_and_visibility='existing field go->last row write includes isolated VM visibility; '
                        'remote consumer read, publication, matched ACK, reverse credit and reissue remain required',
                    port_serialization_calendar_cycles=None, shared_down_combine_cycles=None,
                    endpoint_area_and_loaded_fanout_mm2=None),
                unbound=['actual multi-endpoint fanout/port calendar and loaded wire for this placement',
                         '20480B raw32 x input (draft packed BF16 10240B is conditional only)',
                         '4608B raw32 GU return and 9216B raw32 W2 input to/from canonical SU provider',
                         'actual input leases, VM writer/publication/ACK and reverse-credit caller binding',
                         'route IDs/weights packet identity and exclusion',
                         'shared down, ordered combine/allreduce and source-dependency calendar',
                         'new endpoint/clock/PG costs and in-context SS/FF']))
        assert len(candidates)==203 and len(catalogues)==63
        summary=[]
        for k in range(1,7):
            cc=[c for c in candidates if c['group_count']==k]
            best=min(cc,key=lambda c:c['field_node_barrier_calendar_cycles'])
            summary.append(dict(groups=k,enumerated=len(cc),best_candidate=best['id'],
                best_field_only_us=best['field_node_barrier_calendar_us'],
                max_phases_per_node=best['longest_die_phases_per_node'],added_dies=best['added_dies'],
                added_die_body_mm2=best['added_die_body_mm2'],whole_chain_us=None))
        # Catalogue translations reference one shared literal rank-slice table;
        # avoid repeating four rank slices for every run of every subset.
        for cat in catalogues.values():
            for span in cat['translation']:
                del span['rank_slices']
                span['rank_slice_binding']='source_entries[tensor].rank_slices; all four original slices'
        out['layers'].append(dict(layer=L,experts=exps,canonical_baseline=baseline,
            calibration_source_identity={p['phase']:dict(x_source=p['x_source'],x_sha256=plan['x_sha256'][p['phase']],
                 matrices=p['mats']) for p in phases},
            measured_field_scope=field['not_measured'],
            workload_scope='selected six-expert source workload only; other experts remain on canonical dies',
            canonical_full_field_node_barrier_sum_us=sum(max(b['us'] for b in baseline if b['node']==n)
                 for n in (f'L{L}.ffn.experts_gu',f'L{L}.ffn.down')),
            disjoint_subregion_candidate=dict(feasible_without_relocation=False,
                reason='Each selected expert occupies all128 source regions; no disjoint canonical subregions.'),
            source_entries=entries,ROM_catalogues=catalogues,candidates=candidates,summary=summary))
        print(json.dumps(dict(layer=L,canonical=baseline,summary=summary)),flush=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    finish_record(out,a)
    raw=(json.dumps(out,indent=1)+'\n').encode()
    if str(a.output).endswith('.gz'):
        a.output.write_bytes(gzip.compress(raw,mtime=0))
    else:
        a.output.write_bytes(raw)
    return 0


def finish_record(out,a):
    """Finalize existing cases only; no enumeration, phase, or payload execution."""
    plan,field,inv=map(read,(a.plan,a.field,a.inventory))
    measured={p['phase']:p for p in field['phases']}
    for layer in out['layers']:
        L=layer['layer']
        baseline=layer['canonical_baseline']
        layer['canonical_full_field_node_barrier_sum_us']=layer.pop('canonical_routed_field_node_sum_us',
            layer.get('canonical_full_field_node_barrier_sum_us'))
        layer['existing_group_reuse']=dict(capacity_established=False,
            reason='Fresh-group catalogue excludes other resident tensors. Aggregate canonical free words '
                   'are not a proof of per-pair intervals, clock/service slots or compatible live controls.',
            canonical_stages={str(b['stage']):dict(occupied_pairs=inv['occupied_pairs_per_stage'][b['stage']],
                used_pair_words=inv['used_logical_words_per_stage'][b['stage']],
                aggregate_remaining_pair_words=2417*8192-inv['used_logical_words_per_stage'][b['stage']]) for b in baseline},
            cheaper_reuse_claim=False)
        shared=serial([p for p in plan['phases'] if p['layer']==L and p['group']=='shared.w2'],measured,80)
        three=min((c for c in layer['candidates'] if c['group_count']==3),
                  key=lambda c:c['field_node_barrier_calendar_cycles'])
        for c in layer['candidates']:
            c['shared_down_unchanged']=shared
            c['node_barrier_policy']='field-node barrier calendar only; actual SU/quant/lease/publication and source dependencies unbound'
            c['network']['x_input']=dict(raw_VM_bytes_per_rank=20480, packed_BF16_bytes_per_rank=10240,
                multicast_copies=c['group_count'], source_bound_hop_cycles=None,
                conditional_packed_reference_hop_cycles=428,
                conditional_reference='draft/rlinks x_row requires actual source-owned exact BF16 pack/unpack; absent',
                reference_wire_cycles=90, placement_loaded_wire_cycles=None)
            c['network']['GU_return']=dict(raw_VM_bytes_per_expert_per_rank=4608,
                packed_BF16_bytes_per_expert_per_rank=2304,copies=6,cycles=None)
            c['network']['W2_input']=dict(raw_VM_bytes_per_expert_per_rank=9216,
                packed_BF16_bytes_per_expert_per_rank=4608,copies=6,cycles=None)
            c['network']['returned_down']=dict(bytes_per_expert_per_rank=5120,copies=6,
                measured_isolated_hop_cycles=348, reference_wire_cycles=90,
                representation='1280 raw32 VM scalars with BF16-lifted field results',
                placement_loaded_wire_cycles=None)
            c['unbound']=['actual multi-endpoint port calendar, loaded wire and endpoint/clock/PG area',
                '20480B raw32 x transport or actual source-owned exact 10240B BF16 pack/unpack',
                '4608B raw32 GU return (2304B packed), 9216B raw32 W2 input (4608B packed)',
                'actual VM writer/publication, input lease, matched ACK, reverse credit and reissue',
                'route ID/weight framing and identity/exclusion',
                'retained SU/quant, shared down and ordered combine/allreduce source-dependency calendar',
                'in-context SS/FF; existing isolated link/wire terms are not new-placement closure']
            c['field_only_dominated_by']=None
            if c['group_count'] in (4,5) and c['field_node_barrier_calendar_cycles']>=three['field_node_barrier_calendar_cycles']:
                c['field_only_dominated_by']=dict(candidate=three['id'],groups=3,
                    reason='no faster field-node calendar and strictly more added full S81 dies; FIELD ONLY')
            if L==3 and c['group_count']==1:
                c['field_only_dominated_by']=dict(canonical=True,
                    reason='same 4.2166667us field calendar, adds4 dies; original canonical group already installed')
        for cat in layer['ROM_catalogues'].values():
            for span in cat['translation']:
                span.pop('rank_slices',None)
                span['rank_slice_binding']='source_entries[tensor].rank_slices; all four original slices'
        layer['calibration_source_identity']={p['phase']:dict(x_source=p['x_source'],
            x_sha256=plan['x_sha256'][p['phase']],matrices=p['mats']) for p in plan['phases']
            if p['layer']==L and any(p['group']==f'exp{e}.{k}' for e in layer['experts'] for k in ('gu','w2'))}
        layer['measured_field_scope']=field['not_measured']
        for row in layer['summary']:
            best=layer['candidates'][row['best_candidate']]
            row['field_only_dominated_by']=best['field_only_dominated_by']
    out['finalization']=dict(source_commit=a.source_commit,tool_sha256=sha(Path(__file__)),
        enumeration_repeated=False if a.finalize_from else None,
        raw_input_sha256=sha(a.finalize_from) if a.finalize_from else None)
    summary=dict(schema=out['schema'],adopted=False,source_commit=a.source_commit,
        total_cases=sum(len(L['candidates']) for L in out['layers']),
        complete_chain_latency_us=None,
        layers=[dict(layer=L['layer'],experts=L['experts'],
             canonical_field_node_barrier_sum_us=L['canonical_full_field_node_barrier_sum_us'],
             canonical_baseline=L['canonical_baseline'],summary=L['summary'],
             existing_group_reuse=L['existing_group_reuse'],
             capacity_range=dict(min_max_pair_words=min(c['max_pair_words'] for c in L['ROM_catalogues'].values()),
                max_max_pair_words=max(c['max_pair_words'] for c in L['ROM_catalogues'].values()),
                pair_capacity=8192),total_chain_latency_us=None) for L in out['layers']])
    if a.summary:
        a.summary.parent.mkdir(parents=True,exist_ok=True)
        a.summary.write_text(json.dumps(summary,indent=1)+'\n')


def finalize(a):
    out=read(a.finalize_from)
    assert len(out['layers'])==2 and all(len(L['candidates'])==203 for L in out['layers'])
    finish_record(out,a)
    raw=(json.dumps(out,indent=1)+'\n').encode()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes(gzip.compress(raw,mtime=0) if str(a.output).endswith('.gz') else raw)
    print('FINALIZED406 existingcases; no enumeration; output',a.output,flush=True)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,default=REC/'coverage_manifest/inputs/retained_plan.json.gz')
    p.add_argument('--field',type=Path,default=ROOT/'results/rtl/dsrom_1m_allmeasured_20261004/field.json')
    p.add_argument('--stage-map',type=Path,default=CAN/'stage_map.json')
    p.add_argument('--inventory',type=Path,default=CAN/'inventory.json')
    p.add_argument('--matrix-map',type=Path,default=CAN/'matrix_map.jsonl.gz')
    p.add_argument('--floorplan',type=Path,default=ROOT/'results/rtl/dsrom_s81_fulldie_20261004/floorplan.json')
    p.add_argument('--links',type=Path,default=REC/'draft/rlinks.json')
    p.add_argument('--finalize-from',type=Path,help='annotate already computed cases; never enumerate again')
    p.add_argument('--summary',type=Path)
    p.add_argument('--source-commit',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    return finalize(a) if a.finalize_from else run(a)


if __name__=='__main__':
    raise SystemExit(main())
