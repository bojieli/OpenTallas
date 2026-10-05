#!/usr/bin/env python3
"""Actual retained live-cell census plus pending full-parent capacity contract.

No TT unit extrapolation, checkpoint payload, RTL, physical run or admission.
Historical mapped netlists are not new source/pipeline/package qualification.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from hbm_tc_perimeter_strip_model import cts_count

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'results/uarch/hbm_tc_parent_capacity_20261002'
PRIOR='eae4f69a0fb87dc0e2dd7099eb6c8401d3d634d4'
SOURCE='000ba0898f5120a66d5905ccff333ebbbe28394d'
WITNESS='b33395215e09a8517f2da77d3f043435005ab8fe'


def snap(x,pitch=.27):return math.ceil((x-1e-9)/pitch)*pitch


def row_evidence(d):
    cuts=[];warnings=[]
    for p,f in d['files'].items():
        t=f.get('text','')
        for m in re.finditer(r'initial (\d+) rows \((\d+) sites\) were cut with (\d+) shapes for a total of (\d+) rows \((\d+) sites\)',t):
            a,b,c,e,g=map(int,m.groups());cuts.append(dict(path=p,sha256=f['sha256'],initial_rows=a,initial_sites=b,cut_shapes=c,remaining_row_fragments=e,remaining_sites=g,remaining_row_area_um2=g*.054*.27,removed_site_area_um2=(b-g)*.054*.27))
        for line in t.splitlines():
            if 'WARNING PDN-' in line:warnings.append(dict(path=p,text=line))
    return dict(actual_retained_row_cut_records=cuts,actual_PDN_warning_records=warnings,
        DEF_paths=d['DEF_paths'],placed_parent_endpoints_available=False,
        row_fragment_coordinates_available=False,complete_PDN_via_geometry_available=False,
        no_warning_is_treated_as_free_tracks=True,unobserved_capacity_credit_um2=0)


def budget(c,W,H,ceiling):
    ff=c['unique_FF']['count'];levels,n=cts_count(ff)
    # Reuse prior explicit count/stock-cell caps, rather than silently assuming
    # zero parent CTS/hold overhead in a pre-CTS mapped netlist.
    overhead=dict(CTS_buffer_cap=dict(count=n,area_um2=n*.4374),
        hold_buffer_cap=dict(count=2*ff+2,area_um2=(2*ff+2)*.0729),
        signal_buffer_cap=dict(count=ff,area_um2=ff*.0729))
    area=c['mapped_stdcell']['area_um2'];needed=area+sum(v['area_um2'] for v in overhead.values())
    gap=max(0,needed/.5-ceiling)
    # A necessary area deficit at fixed width is not a sufficient floorplan.
    minimum_dH=snap(gap/(W-4))
    # Dedicated new row band gives no old-whitespace or decap credit. Its
    # nominal capacity still must subtract actual route/PDN/via exclusions.
    band_height=snap(needed/(.5*(W-4)))
    guard=4.32
    band=[2.,snap(H+guard),W-2.,snap(H+guard)+band_height]
    slot=[W,snap(band[3]+2.)]
    return dict(live_mapped_cell_area_um2=area,live_mapped_FF_count=ff,
        parent_CTS_hold_signal_count_caps=overhead,CTS_level_counts=levels,
        mandatory_parent_cell_reservation_cap_um2=needed,placement_utilization_policy=.5,
        cell_area_ceiling_without_further_exclusions_um2=.5*ceiling,
        necessary_added_area_um2_at_policy=gap,necessary_minimum_height_delta_at_fixed_width_um=minimum_dH,
        protected_parent_register_control_arithmetic_band_um=band,
        protected_band_nominal_row_area_um2=(band[2]-band[0])*(band[3]-band[1]),
        zero_old_whitespace_credit=True,zero_decap_credit=True,
        candidate_inventory_plus_dedicated_band_slot_um=slot,
        candidate_slot_growth_um=[0,slot[1]-H],candidate_32SM_slot_delta_mm2=32*W*(slot[1]-H)/1e6,
        outline_is_conditional_not_adopted=True,
        actual_fit_verified=False,
        required_extra_height_formula='ceil_row((unavailable_row_area + channel_site_exclusions + PDN_via_keepout_area + qualified_package_area_delta/0.5)/(W-4))',
        CTS_hold_caps_are_not_measured_delay_cures=True,
        no_parent_SS_FF_closure_claim=True)


def transport_reservation(c,W,H,ceiling,nets,ratio):
    """Unique source net/endpoint reservation bounds; no topology admission.

    Shared-tree lower count is max stages per net; branch upper count charges
    each actual distinct endpoint once. Constants/clock/reset are excluded.
    Iterate added transport FF/CTS/hold area and its band reach to a fixed point.
    """
    base_ff=c['unique_FF']['count'];base_area=c['mapped_stdcell']['area_um2']
    extra=0;trace=[]
    for iteration in range(32):
        cc=dict(c,unique_FF=dict(c['unique_FF'],count=base_ff+extra),
                mapped_stdcell=dict(c['mapped_stdcell'],area_um2=base_area+extra*.37908))
        b=budget(cc,W,H,ceiling);rect=b['protected_parent_register_control_arithmetic_band_um']
        corners=[rect[:2],rect[2:],[rect[0],rect[3]],[rect[2],rect[1]]]
        lower=upper=0;families={}
        for net in nets.values():
            if net['role']=='clock_reset' or net['constant_zero']:continue
            ep={(p['instance'],p['pin']):p['center_um'] for p in net['endpoints']}
            stages=[max(0,math.ceil(ratio*max(abs(q[0]-p[0])+abs(q[1]-p[1]) for q in corners)/504)-1) for p in ep.values()]
            lo=max(stages,default=0);hi=sum(stages);lower+=lo;upper+=hi
            role=net['role'];r=families.setdefault(role,dict(unique_nets=0,distinct_endpoints=0,shared_tree_FF_lower=0,branch_FF_upper=0))
            r['unique_nets']+=1;r['distinct_endpoints']+=len(ep);r['shared_tree_FF_lower']+=lo;r['branch_FF_upper']+=hi
        trace.append(dict(iteration=iteration,extra_transport_FF_priced=extra,required_branch_FF_upper=upper,shared_tree_FF_lower=lower,slot_um=b['candidate_inventory_plus_dedicated_band_slot_um']))
        if upper<=extra:
            return dict(route_length_ratio_case=ratio,per_source_unique_family=families,
                balanced_transport_FF_count_interval=[lower,upper],priced_transport_FF_upper=extra,
                fixed_point_trace=trace,parent_capacity_with_transport=b,
                source_matched_pin_centers_are_projected_successor_abstract=True,
                actual_parent_producer_consumer_pin_coordinates=False,
                counts_are_declared_reservations_not_synthesized_successor_cells=True,
                transport_clock_period_ps=833,no_clock_uncertainty_relaxation=True,
                physical_topology_and_alignment_gate_required=True)
        extra=upper
    raise ValueError('transport/area reservation failed to converge; do not admit')


def build():
    pins=[]
    def git(path,rev=PRIOR):
        b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT)
        pins.append(dict(git=rev,path=path,sha256=hashlib.sha256(b).hexdigest()));return b
    if (ROOT/'tools/hbm_tc_perimeter_strip_model.py').read_bytes()!=git('tools/hbm_tc_perimeter_strip_model.py'):
        raise ValueError('pinned CTS count helper drift')
    old=json.loads(git('results/uarch/hbm_tc_perimeter_strip_20261002/model.json'))
    manifests=json.loads(gzip.decompress(git('results/uarch/hbm_tc_perimeter_strip_20261002/net_manifest.json.gz')))
    witness=json.loads(git('results/rtl/parent_BF16_product_underflow_witness_20261002/witness.json',WITNESS))
    bmul=git('rtl/v41rom/ot_v41_bmul2.sv',SOURCE)
    if hashlib.sha256(bmul).hexdigest()!=witness['source_sha256']:raise ValueError('arithmetic witness source mismatch')
    tc=git('rtl/gpu/ot_gpu_tc_col.sv',SOURCE).decode()
    if 'ot_v41_bmul2 u_mul' not in tc:raise ValueError('column dependency drift')
    models={}
    for name,label in [('qwen','Qwen'),('deepseek_v41','DS')]:
        def local(suffix):
            p=DEST/(label+suffix);b=p.read_bytes();pins.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(b).hexdigest()))
            return json.loads(gzip.decompress(b) if suffix.endswith('.gz') else b)
        d=local('_retained.json.gz');meta=local('_metadata.json');c=d['census'];metrics=d['metrics']['1_synth.json']
        if c['mapped_stdcell']['count']!=metrics['synth__design__instance__count__stdcell']:raise ValueError('live cell count does not reproduce retained import')
        if abs(c['mapped_stdcell']['area_um2']-metrics['synth__design__instance__area__stdcell'])>.5:raise ValueError('live area does not reproduce rounded import')
        if c['unsupported_assignments']:raise ValueError('unresolved aliases')
        # Validate canonical library areas against the locked stock LEF rather
        # than taking a TT arithmetic-unit scalar from a different mapping.
        platform=json.loads(git('results/uarch/hbm_tc_geometry_prerequisite_20261001/platform_source.json'))
        lef=platform['files']['lef/asap7sc7p5t_28_R_1x_220121a.lef']['text']
        for master in c['mapped_stdcell']['master_counts']:
            match=re.search(r'^MACRO '+re.escape(master)+r'\b(.*?)^END '+re.escape(master),lef,re.M|re.S)
            wh=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',match[1]);area=float(wh[1])*float(wh[2])
            if abs(area-d['library_area_and_output_ports'][master]['area_um2'])>1e-8:raise ValueError('cell area differs from locked LEF')
        prior=old['models'][name];a=next(a for a in prior['alternatives'] if a['id']==prior['selected_model_alternative_id'])
        W,H=a['parent']['inventory_slot_cost_um'];res=prior['co_resident_parent_capacity']['residual_geometric_area_ceiling_um2']
        bb=budget(c,W,H,res);models[name]=dict(actual_retained_mapped_census=c,
            retained_source_parameter_evidence=meta['canonical_source_attributes_and_parameters'],
            retained_macro_views=meta['retained_macro_views'],row_and_PDN_evidence=row_evidence(d),
            proposed_full_inventory=a['parent']['placements'],inventory_macro_count=len(a['parent']['placements']),
            current_failed_TC_perimeter_outline_um=a['outline_um'],parent_capacity=bb,
            transport_and_slot_reservation_cases={str(r):transport_reservation(c,W,H,res,manifests[name]['nets'],r) for r in [1.,1.25]},
            matrix_parent_inventory_only=True,full_goal_inventory_verified=False,
            full_goal_missing_resident_obligations=dict(SIMT_FP32_lanes=128,scratch_KB=64,RF='source-pinned capacity/ports/slot provider required',HC_SU='source-pinned parent placement/package provider required'),
            mapping_corner_scope='Qwen retained parent uses historical TT mapping/ot_hdc_fadd; DS retained parent maps SS/LAT7. Actual historical cell counts are not a TT per-unit arithmetic extrapolation and are not current repaired-target closure.',
            historical_mapping_is_not_full_current_target_qualification=True,
            current_target_package_delta_status='Epicurus numerical repair area/latency and parent qualified arithmetic package bindings required; historical arithmetic pipeline/source identity must be joined before current mapping reuse',
            full_target_RF_SIMD_scope=prior['co_resident_parent_capacity']['SIMD_RF_scope'],
            parent_signal_unique_channel_demand=prior['parent_partition_channel_demand'],
            free_directional_tracks_verified=0,full_inventory_including_perimeter_retained=True,
            arithmetic_cell_attribution='FF semantic owners plus disjoint/shared combinational cone masks; mask0 output-only and mask8 feed logic retained, never dropped',
            clock_contract=dict(period_ps=833,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,relaxation=False))
    endpoint_tables={}
    for name,m in models.items():
        points={r['name']:{'input':[],'output':[]} for r in m['proposed_full_inventory'] if 'TC' in r['kind']}
        for n in manifests[name]['nets'].values():
            if n['role']=='clock_reset' or n['constant_zero']:continue
            family='output' if n['role']=='output' else 'input'
            for p in n['endpoints']:
                if p['instance'] in points:points[p['instance']][family].append(p['center_um'])
        table=[]
        for r in m['proposed_full_inventory']:
            if r['name'] not in points:continue
            cases={}
            for ratio,case in m['transport_and_slot_reservation_cases'].items():
                band=case['parent_capacity_with_transport']['protected_parent_register_control_arithmetic_band_um']
                corners=[band[:2],[band[0],band[3]],band[2:],[band[2],band[1]]]
                lengths={role:max(abs(a[0]-p[0])+abs(a[1]-p[1]) for a in corners for p in pp) for role,pp in points[r['name']].items()}
                cases[ratio]=dict(projected_signal_pin_to_proposed_parent_band_max_Manhattan_um=lengths,
                    transport_reference_stages={role:max(1,math.ceil(length*float(ratio)/504)) for role,length in lengths.items()})
            table.append(dict(instance=r['name'],proposed_origin_um=[r['x'],r['y']],cases=cases,
                old_ready_commit_wire_stages='ABSENT_PLACED_PROVIDER',actual_endpoint_coordinates=False,
                successor_pin_projection_source='eae4f69 net_manifest endpoint centers; unchanged macro origins, larger resident band per transport case'))
        endpoint_tables[name]=table
        m['per_macro_ready_commit_transport_cases']=table
    events=[]
    for e in old['event_dependency_plan']:
        events.append(dict(e,per_macro_ready_commit_transport_table_ref=e['model']+'.per_macro_ready_commit_transport_cases',
            target_mapping_admission=False,old_parent_readiness_never_assumed_free=True,
            physical_column_assignment_provider_required=True,
            dependency_composition='result_visible_new = max(source_service_ready,actual_input_arrival_new) + source_issue_body + shape_specific_drain + TC_strip_delta + output_commit_shift; follow actual_graph_consumers_PCs',
            delta_composition='TC_strip_delta + exposed_input_ready_shift + (new_output_commit_stage-old_output_commit_stage); old stages and slack required',
            proposed_band_cases_are_geometry_sensitivity_not_actual_ready_commit_latency=True))
    return dict(schema='hbm-parent-actual-census-capacity-prerequisite-v1',pins=pins,models=models,event_dependency_plan=events,
        DS_event_count=sum(e['model']=='deepseek_v41' for e in events),Qwen_event_count=sum(e['model']=='qwen' for e in events),
        arithmetic_admission_dependency=dict(owner='Epicurus',witness_commit=WITNESS,source_git=SOURCE,source_sha256=hashlib.sha256(bmul).hexdigest(),
            shared_bmul2_consumers=dict(Qwen_columns_per_SM=64,Qwen_lanes_per_column=32,DS_columns_per_SM=32,DS_lanes_per_column=16),
            operand_scope='DS BF16 passes arbitrary BF16 weights. Existing Qwen INT8-to-BF16 weight decoder cannot emit witness weight 3b80; common source dependency still applies, and ordinary BF16 SCORES/PV feed mapping remains separately unqualified. Structural consumer census is not a claim that every workload reaches the witness.',
            witness=witness,repair_hardware_work_duplicated=False,gate='BLOCKED_FINITE_BF16_UNDERFLOW_RNE_AND_ERROR_FLAG; repair sizing/latency/SSFF context required before any new physical-model adoption'),
        failed_unchanged=old['failed_unchanged'],no_admission=True,no_checkpoint_payload_reads=True,no_RTL_PnR=True,
        actual_parent_row_endpoint_provider_required=dict(existing_retained_paths=['ot-pve1:/home/ubuntu/w13work/sm_v12','ot-pve3:/home/ubuntu/w13work/sm_q'],
            missing=['placed driver/load FF and cell access rectangles','post-cut ROW fragment coordinates and placement blockages','complete SPECIALNETS PDN stripes and via bboxes by layer','post-CTS SS/FF clocks, minmax paths and actual ready/commit stage/slack bindings'],
            provider='Parent/retained-artifact owner must supply bounded text DEF/report export from existing retained databases; this agent never opens ODB or launches a flow. No new synthesis/P&R needed to export historical metadata, but historical export cannot qualify the repaired target.',
            future_full_target_gate='final arithmetic-owner delta -> verified complete capacity/endpoint model -> floorplan -> one full target element -> SS/FF qualification -> replication'))


def artifact():return (json.dumps(build(),sort_keys=True,indent=2)+'\n').encode()


if __name__=='__main__':
    p=DEST/'model.json'
    if p.exists():raise SystemExit('refuse to overwrite evidence')
    p.write_bytes(artifact())
