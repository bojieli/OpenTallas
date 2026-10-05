"""One opt-in S81 provider-anchored service assignment in the component model.

No allocation, ISA compilation, payload computation, runtime or new hardware.
Existing HE/CROM placement anchors each layer's state. Actual field fragments
stay on their canonical dies. This is a design candidate, not accepted ownership.
"""
import collections
import math
from dsrom_s81_unified_components import solve_events


def candidate(demand, bindings, stage_map, providers, fragments, link, component,
              *, protected_group, die_screen, template, enable=False):
    if not enable:
        raise ValueError('explicit model candidate enable required')
    if len(stage_map['PHW_required_by_stage']) != 81:
        raise ValueError('S81 required')
    homes = {}
    for layer in range(40):
        reservations = [p for p in providers if p['layer'] == layer]
        selected = {p['stage'] for p in reservations}
        if len(selected) != 1 or {p['kind'] for p in reservations} != {'HE', 'CROM'}:
            raise ValueError('unique existing HE/CROM owner required')
        homes[layer] = selected.pop()
    by_alias = collections.defaultdict(list)
    for f in fragments:
        by_alias[f['layer'], f.get('original_alias') or f['alias']].append(f)
    bound = {b['node']: b for b in bindings}
    stages = {s['layer']: s for s in demand['functional_program']['stages']}
    runs, assignments, movements, issues = [], [], [], []
    current = None
    events = []
    previous = []
    layer_bytes = collections.Counter()
    # 64B/edge is the baseline packet payload, not the 1024-bit raw macro bus.
    payload = link['memory_bytes_per_port_edge']
    clock = component['clock_load']['stream_target_GHz']
    if payload != 64 or clock != 1.2:
        raise ValueError('selected baseline packet/clock source changed')
    for node in demand['nodes']:
        layer = node['scope']
        if type(layer) is not int:
            current = None
            issues.append({'node': node['id'], 'constraint':
                           'dedicated embedding/head actual owner assignment required'})
            continue
        if layer not in homes:
            raise ValueError('unknown source layer')
        home = homes[layer]
        instruction = node.get('instruction', {})
        b = bound[node['id']]
        if b.get('classification') != 'WEIGHT_PHASE':
            assignments.append({'node': node['id'], 'stage': home,
                                'rank_dies': [4*home+r for r in range(4)],
                                'provider': node['kind'] if not instruction else
                                {0:'control', 1:'native-matrix-service', 2:'su', 3:'quantizer', 4:'xu',
                                 5:'he', 6:'collective'}[instruction['unit']]})
            if node['kind'] == 'instruction':
                # Preserve consecutive native source runs; actions/fences split.
                if current is None or current['layer'] != layer or current['last']+1 != node['instruction_index']:
                    current = {'layer': layer, 'stage': home, 'nodes': [], 'last': -1}
                    runs.append(current)
                current['nodes'].append(node['id'])
                current['last'] = node['instruction_index']
            else:
                current = None
            continue
        current = None
        alias = b['alias']
        alternatives = [p['alias'] for p in b['phase_choices']]
        # Alternative experts remain alternatives; never execute all384 or
        # charge them as six committed EIDs. Each slot has its own worst bound.
        alternatives = list(dict.fromkeys(alternatives))
        choices = []
        for selected_alias in alternatives:
            fs = by_alias[layer, selected_alias]
            if not fs:
                raise ValueError('canonical field fragment missing '+selected_alias)
            rank_bytes, rank_ns, transfers = [0]*4, [0.0]*4, []
            for f in fs:
                destination = f['stage']
                if destination == home:
                    continue
                hops = abs(destination-home)
                for rank, span in enumerate(f['rank_slices']):
                    cols, rows = span['cols'], span['rows']
                    words_in, words_out = cols[1]-cols[0], rows[1]-rows[0]
                    # The functional native VM cell is raw32 (2MiB / 2^19).
                    # Protection/identity is separate, never silently free.
                    input_bytes, output_bytes = 4*words_in, 4*words_out
                    edges = math.ceil(input_bytes/payload)+math.ceil(output_bytes/payload)
                    # Conservative store-and-forward analytical schedule;
                    # repeated input fragments are charged (no free reuse).
                    ns = (2*hops*link['baseline_hop_cycles']+hops*edges)/clock
                    rank_bytes[rank] += input_bytes+output_bytes
                    rank_ns[rank] += ns
                    transfers.append({'rank':rank,'service_stage':home,'field_stage':destination,
                        'alias':f['alias'],'input_bytes':input_bytes,'output_bytes':output_bytes,
                        'hops_each_direction':hops,'serialized_packet_edges':edges,
                        'source_input_base':b['consumer_X_FP32_VM_elements'][0],
                        'result_base':b['consumer_output_base_elements'],
                        'result_row_offset':f.get('row_offset') or 0})
            choices.append({'alias':selected_alias,'bytes_per_rank':rank_bytes,
                            'analytical_transfer_ns_per_rank':rank_ns,'transfers':transfers})
        # Single-user TP4 cost is max(rank), not sum(rank). Runtime expert
        # alternatives use the maximum one-slot cost; no reassociation/sort.
        worst = max(choices,key=lambda c:max(c['analytical_transfer_ns_per_rank']))
        duration = max(worst['analytical_transfer_ns_per_rank'])
        layer_bytes[layer] += max(worst['bytes_per_rank'])
        movements.append({'node':node['id'],'home':home,'runtime_selector_slot':b.get('selector_slot'),
            'alternatives':len(choices),'field_stages':sorted({f['stage'] for a in alternatives for f in by_alias[layer,a]}),
            'worst_transfer':worst,'analytical_transfer_ns':duration})
        if duration:
            event = {'id':node['id']+'.operand_result_transport','deps':previous,'duration_ns':duration}
            events.append(event); previous=[event['id']]
    scratch = [{'layer':l,'stage':homes[l],'cells':s['scratch_elements'],
                'bytes_per_rank':4*s['scratch_elements'],'capacity_cells':1<<19,
                'fits_declared_VM':s['scratch_elements'] <= 1<<19,
                'persistent_state':s['inputs']} for l,s in stages.items()]
    if any(not s['fits_declared_VM'] for s in scratch):
        raise ValueError('candidate state exceeds existing declared VM')
    # Physical union is an explicitly proposed replacement in the existing
    # S81 screen, NOT evidence of324 installed/protected service replicas.
    outline = protected_group['slot']['outline_um']
    protected_mm2 = 128*outline[0]*outline[1]/1e6
    old_vm = template['vm_mm2']
    baseline = die_screen['decision']['area']['die_mm2']
    reticle = die_screen['reticle_mm2']
    replacement = baseline-old_vm+protected_mm2
    baseline_field = sum(die_screen['decision']['area'][k] for k in ('variable','increments','return_mm2'))
    field_budget = .98*reticle-(baseline-baseline_field-old_vm+protected_mm2)
    # Excludes separately required field metadata rotate/wholephase route and
    # native read/write overlays. Even this lower bound can refuse admission.
    fit = {'baseline_die_mm2':baseline,'reticle_mm2':reticle,
           'existing_template_services_mm2':template,
           'proposed_service_dies':4*len(set(homes.values())),
           'template_union_selected_terms_mm2':sum(template[k] for k in template if k.endswith('_mm2'))-old_vm+protected_mm2,
           'original_field_variable_increment_return_mm2':baseline_field,
           'field_budget_at_2pct_margin_before_overlays_mm2':field_budget,
           'protected_groups':128,'protected_group_outline_um':outline,
           'protected_VM_outline_mm2':protected_mm2,
           'replaced_VM_reservation_mm2':old_vm,
           'die_lower_bound_mm2':replacement,
           'over_reticle_at_least_mm2':max(0,replacement-reticle),
           'over_2pct_margin_at_least_mm2':max(0,replacement-.98*reticle),
           'fits_reticle':replacement <= reticle,
           'overlays_priced_here':False,
           'protected_publication_ports':protected_group['ports'],
           'protected_service':protected_group['service'],
           'protected_read_service':protected_group['read_service'],
           'protected_group_clock_qualified':False,
           'remedy_constraint':'free this minimum area at each selected service die while retaining actual field fragments, or coordinate/reprice a smaller field capacity and remap; no uniform shrink/relocation is performed here'}
    # These are concrete resource/route obligations, not a manufactured PASS.
    issues.extend([
        {'constraint':'protected service replacement exceeds reticle before overlays', 'area':fit},
        {'constraint':'per-stage SU/XU/HE/quantizer/collective/VM replicas and source-specific ports must match Maxwell current slot inventory',
         'affected_stages':sorted(set(homes.values()))},
        {'constraint':'native core context and mutable VM publication/remote-result restore must retain request identity, future consumers and reverse/all-copy drain',
         'component_bank_service_II_edges':component['service']['bank_service_II_edges']},
        {'constraint':'physical VM provider replica/slot fit unbound',
         'physical_provider_replicas_per_rank_die':component['area']['physical_provider_replicas_per_rank_die']},
        {'constraint':'baseline link fails required SS setup; source-bound route clock required before physical admission',
         'baseline_ss_setup_ps':link['baseline_ss_setup_ps'],'baseline_ff_hold_ps':link['baseline_ff_hold_ps']},
        {'constraint':'cross-layer persistent WINDOW/CKV/IK/SELG/CAND provider addresses require existing owner-preserving remote translation, not full-state migration or local aliases'},
    ])
    solved = solve_events(events)
    transport = solved['finish_ns'][previous[0]] if previous else 0
    return {'candidate':'HE_CROM_ANCHORED_SERVICE_STATE','default_enabled':False,
            'adopted':False,'hardware_admission':False,'parent_dispatch_ready':False,
            'physical_service_union':fit,'homes':homes,'assignments':assignments,'ordered_nonfield_runs':runs,
            'field_movements':movements,'scratch':scratch,
            'analytical_packet_transfer_ns':transport,'bytes_per_rank_by_layer':dict(layer_bytes),
            'pricing_scope':'serial store-and-forward raw32 VM operand/result transport only; repeated inputs charged; not full-token latency or measured link rate',
            'extra_vm_boundary_service_ns':None,'native_compute_ns':None,'full_token_ns':None,
            'new_hardware':False,'minimum_added_outline_mm2_per_service_die':protected_mm2-old_vm,
            'unresolved_constraints':issues,
            'compiler_consumer':'Popper emit_nonfield_run(run.nodes, run.stage, rank); retain literal source order and use emitted actual entries; no guessed entry0 offers',
            'clock_domains':{'stream_GHz':1.2,'serial_GHz':0.9},
            'link_payload_bytes_per_edge':payload,'link_credit_capacity':link['credits'],
            'physical_payload_channel_unqualified':True,
            'bandwidth_scope':'64B/edge baseline source payload limit, not a measured loaded service rate; model values are a target-clock analytical reservation only',
            'conditional_source_predicates':'all declared layer field nodes priced at one worst legal expert choice per slot; not an observed predicate/EID trajectory',
            'source_order_rule':'every source node retained; field fragments gather before dependent run; actual dynamic EIDs select native field dispatch; original collective/tree order unchanged'}


def main():
    import argparse
    import gzip
    import hashlib
    import json
    from pathlib import Path
    from dsrom_s81_execution_binding import CANONICAL, SOURCE, HASHES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', type=Path, required=True)
    parser.add_argument('--enable', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    if not a.enable:
        parser.error('explicit --enable required; model only')
    if a.out.exists():
        raise ValueError('refuse existing output')
    paths = {'matrix_map.jsonl.gz':a.owner/CANONICAL/'matrix_map.jsonl.gz',
             'stage_map.json':a.owner/CANONICAL/'stage_map.json',
             'providers.json':a.owner/CANONICAL/'providers.json',
             'demand-r5.json.gz':a.owner/SOURCE/'inputs/demand-r5.json.gz',
             'node_bindings.jsonl.gz':a.owner/SOURCE/'r3/node_bindings.jsonl.gz',
             'link.json':a.owner/'results/uarch/dsrom_baseline_link_clock_20261004/context_r1/model.json',
             'component.json':a.owner/'results/uarch/dsrom_s81_unified_components_20261004/model.json',
             'protected.json':a.owner/'results/uarch/dsrom_s81_minimum_protected_group_20261004/model.json',
             'die_screen.json':a.owner/'results/uarch/dsrom_c_recheck_20261004/model.json'}
    pins = {n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in paths.items()}
    for n in ('matrix_map.jsonl.gz','stage_map.json'):
        if pins[n] != HASHES[n]:
            raise ValueError('canonical input changed '+n)
    def load(n):
        p = paths[n]
        if n.endswith('.gz'):
            with gzip.open(p,'rt') as f:
                return ([({k:x.get(k) for k in ('layer','alias','original_alias','stage','row_offset','rows','K','rank_slices','format','segments')} if n=='matrix_map.jsonl.gz' else x) for x in (json.loads(line) for line in f)] if n.endswith('.jsonl.gz')
                        else json.load(f))
        return json.loads(p.read_text())
    result = candidate(load('demand-r5.json.gz'),load('node_bindings.jsonl.gz'),
                       load('stage_map.json'),load('providers.json'),
                       load('matrix_map.jsonl.gz'),load('link.json'),load('component.json'),
                       protected_group=load('protected.json'),die_screen=load('die_screen.json'),
                       template={'su_mm2':12.80594,'att_mm2':45.86549,'idx_mm2':7.52245,
                                 'vm_mm2':0.89234,'hc_mm2':18.31349,'collective_mm2':1.38967,
                                 'gather_mm2':1.38823,'capture_mm2':0.10868,
                                 'scope':'representative scan template, not installed replicas'},
                       enable=True)
    result['input_sha256'] = pins
    with a.out.open('x') as f:
        json.dump(result,f,indent=2);f.write('\n')


if __name__ == '__main__':
    main()
