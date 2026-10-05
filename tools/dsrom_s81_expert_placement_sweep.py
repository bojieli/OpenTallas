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
            # Exact-size draft endpoint measurements are reusable *terms*, not a
            # proof that concurrent endpoints, intermediate hops or ACKs are bound.
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
                shared_down_unchanged=[b for b in baseline if any('shared.w2' in p for p in b['phases'])],
                total_source_bound_latency_us=None, physical_admission=False,
                network=dict(primary_bidirectional_ports_per_rank=len(groups),
                    fresh_group_ports_per_rank=1, total_new_bidirectional_endpoints=8*len(groups),
                    source_provider_stage=stage['provider_homes'][str(L)],
                    x_input=dict(bytes_per_rank=10240, multicast_copies=len(groups),
                        measured_isolated_hop_cycles=x['total_cycles'], includes_vendor_and_loaded_wire=True),
                    returned_down=dict(bytes_per_expert_per_rank=5120, copies=6,
                        measured_isolated_hop_cycles=ret['total_cycles'], includes_vendor_and_loaded_wire=True),
                    GU_return=dict(bytes_per_expert_per_rank=2304, copies=6, cycles=None),
                    W2_input=dict(bytes_per_expert_per_rank=4608, copies=6, cycles=None),
                    identities=dict(expert_ids=exps, route_weight_bytes=24,
                        packet_framing_cycles=None, producer_PC='retained per-matrix ISA PC where present'),
                    credit_and_visibility='existing field go->last row write includes isolated VM visibility; '
                        'remote consumer read, publication, matched ACK, reverse credit and reissue remain required',
                    port_serialization_calendar_cycles=None, shared_down_combine_cycles=None,
                    endpoint_area_and_loaded_fanout_mm2=None),
                unbound=['actual multi-endpoint fanout/port calendar and loaded wire for this placement',
                         '2304B GU return and 4608B W2 input to/from canonical SU provider',
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
        out['layers'].append(dict(layer=L,experts=exps,canonical_baseline=baseline,
            canonical_routed_field_node_sum_us=sum(max(b['us'] for b in baseline if b['node']==n)
                 for n in (f'L{L}.ffn.experts_gu',f'L{L}.ffn.down')),
            disjoint_subregion_candidate=dict(feasible_without_relocation=False,
                reason='Each selected expert occupies all128 source regions; no disjoint canonical subregions.'),
            source_entries=entries,ROM_catalogues=catalogues,candidates=candidates,summary=summary))
        print(json.dumps(dict(layer=L,canonical=baseline,summary=summary)),flush=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=1)+'\n')
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
    p.add_argument('--source-commit',required=True)
    p.add_argument('--output',type=Path,required=True)
    return run(p.parse_args())


if __name__=='__main__':
    raise SystemExit(main())
