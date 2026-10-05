#!/usr/bin/env python3
"""Price only measured L20 matched admissions, with finite source retirement.

All other phases keep the recovery baseline. This is a bounded projection,
not a hardware adoption or an all-layer extrapolation.
"""
import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path

import dsrom_recovery_decision_gate as D

OUT = D.A.RECOVERY / "paired_field_gate"


def groups(data):
    if (data['completed'], data['passed'], data['expected_cases']) != (640,640,640):
        raise ValueError('incomplete paired measurement')
    by = defaultdict(list)
    for r in data['results']:
        if r['pass_'] is not True or r['calibration'] is not True:
            raise ValueError('failed region')
        by[r['group']].append(r)
    result = {}
    for name, rows in by.items():
        if {r['region'] for r in rows} != set(range(128)) or len(rows) != 128:
            raise ValueError('missing/duplicate region')
        result[name] = {}
        for mode in ('serial','overlap'):
            increments, tails, stored, row_count = [], [], [], 0
            for r in rows:
                v = r['results'][mode]
                peer = r['results']['overlap' if mode == 'serial' else 'serial']
                if not v['pass_'] or v['errors'] or v['node'][0]['fault']:
                    raise ValueError('failed terminal')
                if v['profile'][0]['input_bytes'] != peer['profile'][0]['input_bytes']:
                    raise ValueError('unequal traffic')
                a, go, end = v['events']['A'], v['events']['G'], v['events']['E']
                if len(go) != r['phases'] or len(end) != r['phases'] or len(a) != r['phases']:
                    raise ValueError('phase conservation')
                if [x[1] for x in go] != [x[1] for x in peer['events']['G']]:
                    raise ValueError('changed phase order')
                initial = a[0][1]
                increments.append([go[i][0]-(go[i-1][0] if i else initial) for i in range(len(go))])
                p, n = v['profile'][0], v['node'][0]
                if p['last_vm_commit'] != n['last_w']+1 or n['idle'] != p['last_vm_commit']+1:
                    raise ValueError('write/visibility/source-idle boundary mismatch')
                tails.append(n['idle']-go[-1][0])
                stored.append(p['last_vm_commit'])
                row_count += v['rows']
            # Max each successive source GO increment and the final owned tail.
            # This conservatively couples regions without adding a fictitious
            # installed-root barrier or borrowing asynchronous consumer credits.
            steps = [max(x[i] for x in increments) for i in range(len(increments[0]))]
            result[name][mode] = dict(regions=128, phases=len(steps), rows=row_count,
                max_stored_absolute_edge=max(stored), max_GO_step_edges=steps,
                max_last_GO_to_source_idle_edges=max(tails),
                accepted_to_source_idle_bound_edges=sum(steps)+max(tails),
                root_barrier_qualified=False, downstream_accepted_lease=None)
    return result


def candidate(table, mode):
    wire_rows = D.load(D.OUT/'inputs/field_pq.json')['nodes']
    selected = {}
    charged = {}
    for name, record in table.items():
        node, stage = name.rsplit('.st',1)
        wire = next(x['wire_stage_cycles_s81_floorplan'] for x in wire_rows
                    if x['node'] == node and x['die_stage'] == int(stage))
        value = record[mode]['accepted_to_source_idle_bound_edges']+wire
        charged[name] = dict(source_bound_edges=record[mode]['accepted_to_source_idle_bound_edges'],
                             floorplan_wire_edges_once=wire, total_edges=value)
        # Existing timing authority composes parallel die owners by maximum,
        # never by summing st37 and st38 work into one serial duration.
        selected[node] = max(selected.get(node,0), value)
    return dict(lever='field_matched_'+mode, exact=True,
        nodes={n:dict(us=t/D.A.CLK*1e6, source='matched SAME final2 L20 '+mode+
            '; source idle after actual VM visibility + floorplan wire once; downstream credit unknown')
            for n,t in selected.items()}), charged


def swiglu_candidate():
    su = D.load(OUT/'inputs/su_join.json')['swiglu']
    if su['full_shape_exact'] is not True:
        raise ValueError('SwiGLU exactness unavailable')
    nodes = {}
    for row in su['rows']:
        n = row['chain']
        nodes[n] = dict(us=row['candidate_component_us'], kind='fused_fast',
                       source='actual representative SwiGLU + quant transport; finite endpoint credits unknown')
        layer = n.partition('.')[0]
        # Routed source baseline already computes E2_MULB. Candidate does too.
        # Quantisation also lies inside the measured candidate terminal.
        covered = (['ffn.route_w','ffn.quant2'] if row['baseline_route_weight_already_fused_as_E2']
                   else ['ffn.shared_quant'])
        for suffix in covered:
            nodes[layer+'.'+suffix] = dict(us=0, kind='fused_fast', covered_by=n,
                source='covered by actual '+n+' terminal; not a second route-weight/quant operation')
    return dict(lever='su_swiglu_measured_subset', exact=True, nodes=nodes), su


def build():
    raw = json.loads(gzip.decompress((OUT/'inputs/summary.json.gz').read_bytes()))
    table = groups(raw)
    serialized, serial_charge = candidate(table,'serial')
    overlapped, overlap_charge = candidate(table,'overlap')
    s, _, _ = D.replay([serialized])
    o, _, _ = D.replay([overlapped])
    sg, su_evidence = swiglu_candidate()
    norm, norm_evidence = D.norm_subset()
    combined, _, _ = D.replay([overlapped,sg,norm])
    inputs = [OUT/'inputs/summary.json.gz', OUT/'inputs/launch_inputs.json', OUT/'inputs/su_join.json',
              OUT/'inputs/field_cone.txt', D.OUT/'inputs/field_pq.json',
              D.ROOT/'tools/dsrom_recovery_paired_field_gate.py', D.ROOT/'tools/dsrom_recovery_decision_gate.py',
              D.ROOT/'tools/dsrom_1m_allmeasured.py', D.ROOT/'tools/dsrom_1m_su.py']
    return dict(schema='opentallas.dsrom-recovery.paired-field-gate.v1',
        source_commit=D.load(OUT/'inputs/launch_inputs.json')['source_commit'],
        inputs={str(p.relative_to(D.ROOT)):D.sha(p) for p in inputs}, groups=table,
        serial_charges=serial_charge, overlap_charges=overlap_charge,
        serialized_projection=D.summary(s), overlapped_projection=D.summary(o),
        matched_L20_AR_saved_us=s['AR_us']-o['AR_us'],
        matched_L20_MTP_rate_change=o['MTP']['MTP_tok_s']/s['MTP']['MTP_tok_s']-1,
        scope='Only three actual L20 node families; all other nodes retain baseline. No historical 105us credit, all-layer extrapolation or installed-root barrier qualification.',
        combined_measured_subsets_projection=D.summary(combined),
        combined_adoption=False, combined_complete_SU=False,
        swiglu=su_evidence, swiglu_route_accounting=dict(
            baseline_source='tools/dsrom_1m_su.py::chain_swiglu already E2_MULB',
            separately_counted_route_w_in_historical_graph=True,
            covered_nodes={n:v['covered_by'] for n,v in sg['nodes'].items() if 'covered_by' in v},
            note='Subset contrast includes removal of duplicate route-weight and fused quant terms; not all hardware speedup.'),
        cold_norm=norm_evidence,
        physical=dict(verdict='REJECT_CURRENT_FIELD_SCREEN', SS_PQ1_ps=-722.82, SS_PQ0_ps=-684.06,
            full_context_qualified=False, selected_HCPOST='REJECT_SS -52.47ps; different M6A5 lane gives no qualification'),
        build_admitted=False, adoption=False,
        remaining_costs=dict(installed_context_barrier=None, finite_downstream_consumer_credits=None,
            new_context_walker_area=None, R93_conversion_area=None, routed_clock_fanout_SS_FF=None),
        repair_direction=dict(owner='Epicurus', scope='mandatory shared address cone, not PQ performance rescue',
            proposed_raw_FF=47, proposed_added_cycles=0, proposed_accepted_II=1,
            construction='capture active fam/nbeat/base33 bits and SAW14 exact next-address register at existing can_go; preserve sw and stall/last-beat recurrence',
            added_ROM_reads=0, added_boundary_ports=0, token_gain_credit=0,
            area_terms='47FF + up to99mux2 + SAW14 base-add +16bit increment/equality + protection/enable/clock/localwire; not free',
            exactness_required='registered address equals original st_a during sm_run incl first fill/stalls/last-position wrap; unchanged every actual write/idle',
            physical_required='SS60/FF25 separately launch->active, active->address and address->ROM->sw; no closure inferred'))


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=OUT/'model.json')
    a=ap.parse_args(); d=build()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(d,indent=1,sort_keys=True)+'\n')
    print(json.dumps({k:d[k] for k in ('matched_L20_AR_saved_us','matched_L20_MTP_rate_change','physical','adoption')}))
