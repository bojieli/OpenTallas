#!/usr/bin/env python3
"""Source-bound final-element footprint prerequisite, no RTL/model mutation/P&R."""
import argparse
import hashlib
import json
import math
from decimal import Decimal as D
from pathlib import Path
import re
import uarch_model as U
import w10_fullmap_slot_fit as S

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('results/uarch/w10_final_element_fit_r1')
QROOT=Path('results/physical_abi3/asap7/chip/v41_w10_elem')
QFAIL=QROOT/'ss_route_failures/p12q9.json'
QPRE=Path('results/physical_abi3/asap7/chip/w10_w18_recovery_20261001/p12q9_preflight.json')
CLOCK=Path('results/uarch/w10_clock_tree_site_budget_r1/receipt.json')
RAM=Path('results/quality/w16_w17_integer_residency_20261001/summary.json')
P5=Path('results/physical_abi3/asap7/chip/v41_w18/pair_w10p5_abstract.json')
P5LEF=Path('results/physical_abi3/asap7/chip/abstracts/ot_v41_rom_elem_q_w10p5/ot_v41_rom_elem_q.lef')
SYNTHETIC=Path('results/physical_abi3/asap7/chip/v41_w18/head_die/q_tile_1p2.lef')
MACRO=Path('physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef')
FULL=Path('results/uarch/w10_baseline_wake/fullmap_r2')

def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def read(path):return json.loads((ROOT/path).read_text())
def lef_size(path):return tuple(float(x) for x in re.search(r'\bSIZE ([\d.]+) BY ([\d.]+)',(ROOT/path).read_text()).groups())
def arg(argv,key,count=1):
    i=argv.index(key)+1
    return argv[i] if count==1 else argv[i:i+count]

def final_q_evidence(route,preflight):
    """Necessary terminal evidence only; even a clean terminal needs corner/pin gates."""
    names=('6_final.odb','6_final.sdc','6_final.spef','6_final.v')
    issues=list(preflight['preflight']['issues'])
    if route['status']!='pass' or not route['flow_completed']:issues.append('q route is not a passing completed flow')
    if not route['design']['closed']:issues.append('q element is not closed')
    artifacts=preflight['preflight']['artifacts']
    for name in names:
        matches=[v for key,v in artifacts.items() if name in key]
        if not any(isinstance(v,dict) and v.get('size_bytes',v.get('bytes',0))>0 and
                   re.fullmatch(r'[0-9a-f]{64}',str(v.get('sha256',''))) for v in matches):
            issues.append('no nonempty source-pinned '+name)
    if not preflight['element_timing_passes']:issues.append('SS/FF element timing gate has not passed')
    if not preflight['physically_clean_route']:issues.append('physical-clean route gate has not passed')
    return dict(necessary_terminal_inputs_present=not issues,issues=issues,
        current_q_footprint_binding=False,
        scope='No current q final LEF + SS/FF ETM/constraints/source/exactness binding exists in these inputs. Terminal or geometry metadata alone cannot qualify it.')

def ceiling(stages,key,extra_field_mm2=0):
    assert extra_field_mm2>=0
    pairs=U._cons_busiest_macros(stages)/2
    nq=pairs-U.CONS_BF16['pairs'];assert nq>0
    usable=U.cons_field_usable_mm2(U.CONS['overhead'],'ring',U.PRODUCT_GEOM)
    need=U.cons_field_need_mm2(stages,'analytical',key,'columns','4096m8')
    current_q=U._cons_pair_mm2(key)
    limit=current_q+(usable-need-extra_field_mm2)/nq
    return dict(stages=stages,layer_dies=4*stages,model_pairs_fractional=pairs,
        model_q_pairs_fractional=nq,BF16_column_pairs=U.CONS_BF16['pairs'],
        usable_field_mm2=usable,current_geometry_need_mm2=need,
        current_geometry_headroom_mm2=usable-need,
        scenario_extra_field_mm2=extra_field_mm2,
        maximum_q_footprint_um2=limit*1e6,
        maximum_height_at_requested_width_um=limit*1e6/U.CONS_PITCH[key]['q_um'][0],
        maximum_width_at_requested_height_um=limit*1e6/U.CONS_PITCH[key]['q_um'][1],
        q_footprint_um2_lost_per_additional_field_mm2=1e6/nq,
        area_scope='Existing analytical storage-density formula and fractional stage plan. Not integer resident placement, die geometry, scalar capacity, timing or latency qualification.')

def compose(q_outline,bf_outline):
    key='w10_final_element_fit_prerequisite'
    assert key not in U.CONS_PITCH
    U.CONS_PITCH[key]=dict(U.CONS_PITCH[U.PRODUCT_PITCH],q_um=tuple(q_outline),bf16_outline_um=tuple(bf_outline))
    try:
        stages=U.cons_min_stages('analytical',U.CONS['overhead'],'ring',U.PRODUCT_GEOM,key,'columns','4096m8')
        result=dict(outline_um=list(q_outline),q_footprint_um2=q_outline[0]*q_outline[1],
            conditional_min_layer_stages=stages,conditional_layer_dies=4*stages,
            field_need_mm2=U.cons_field_need_mm2(stages,'analytical',key,'columns','4096m8'),
            preceding_stage_need_mm2=U.cons_field_need_mm2(stages-1,'analytical',key,'columns','4096m8'),
            usable_field_mm2=U.cons_field_usable_mm2(U.CONS['overhead'],'ring',U.PRODUCT_GEOM),
            actual_q_transfer=False,full_token_rate=None,
            scope='Geometry-only substitution in unchanged unified model; scalar extras and protocol/timing unbound. Not a new candidate or qualified final-element fit.')
        return result
    finally:del U.CONS_PITCH[key]

def archive_projection(stdcell_um2,width_um,frame_y_um):
    """Same 50% site policy and existing macro/escape/halo reserve, no new layout."""
    b=S.budget();width_sites=round(width_um/.054)
    assert abs(width_sites*.054-width_um)<1e-9
    demand=math.ceil(D(str(stdcell_um2))/D('.01458'))
    blocked=b['macro_sites']+b['exclusive_escape_sites']+b['exclusive_top_bottom_halo_sites']
    rows=math.ceil((2*demand+blocked)/width_sites)
    return dict(standard_cell_um2=stdcell_um2,standard_cell_demand_sites=demand,
        width_sites=width_sites,rows=rows,density=.5,fixed_macro_escape_halo_sites=blocked,
        source_outer_frame_y_um=frame_y_um,
        outline_um=[width_um,rows*.27+frame_y_um],current_q_transfer=False,
        scope='Necessary uniform-density projection of the failed legacy q metrics using existing reserve amounts. Not current-q synthesis, legal packing, clock estimate or proposed retry. GRT already contains its historical CTS cells; no new BF16 buffer reserve added.')

def build():
    clock=read(CLOCK);ram=read(RAM);q=read(QFAIL);pre=read(QPRE);p5=read(P5)
    requested=tuple(map(float,arg(q['runner']['argv'],'--die-area',4)[2:]))
    assert requested==tuple(U.CONS_PITCH[U.PRODUCT_PITCH]['q_um'])==(510.84,126.9)
    assert q['design']['parameters']['NB']==2 and q['design']['parameters']['PP']==1
    assert pre['route_record_sha256']==sha(QFAIL)
    assert clock['slot']['rows']==625 and clock['buffer_replicas']==3873
    assert clock['slot']['density']==.5 and clock['slot']['outline_um']==[1002.89,173.07]
    assert clock['constraints']==dict(streaming_GHz=1.2,density=.5,setup_uncertainty_ps=60,hold_uncertainty_ps=25)
    bf=clock['slot']['outline_um'];structure=read(FULL/'strict_structure.json');synth=read(FULL/'1_synth.json')
    assert structure['flop_count']==91733 and structure['icg_count']==8 and len(structure['macros'])==4
    assert synth['synth__design__instance__area__stdcell']==62705.9
    measured_p5=lef_size(P5LEF)
    assert list(measured_p5)==p5['abstract']['size_um']
    assert sha(P5LEF)==p5['abstract']['files']['ot_v41_rom_elem_q.lef']
    assert 'NOT closed' in p5['element']
    macro=lef_size(MACRO)
    assert macro==(125.28,62.91)
    assert ram['geometry_reconciliation']['actual_q_PP_strip_footprint_reconciled'] is False
    assert ram['geometry_reconciliation']['historical_3749_q_fit_transferred'] is False
    key='w10_final_q_ceiling_prerequisite';assert key not in U.CONS_PITCH
    U.CONS_PITCH[key]=dict(U.CONS_PITCH[U.PRODUCT_PITCH],bf16_outline_um=tuple(bf))
    try:
        ceilings=[ceiling(s,key) for s in (41,44,45,46,47,49)]
        scalar_sensitivity=ceiling(45,key,1)
    finally:del U.CONS_PITCH[key]
    cases={
        'requested_failed_p12q9':compose(requested,bf),
        'historical_actual_nonclosing_p5_abstract':compose(measured_p5,bf),
        'historical_p5_tiling_with_channel':compose(U.CONS_PITCH['w18_measured']['q_um'],bf)}
    p45=next(x for x in ceilings if x['stages']==45)
    archive=OUT/'legacy_q_metrics';origin=read(archive/'origin.json')
    assert origin['archive_sha256']=='e20f2641bff90d379520d0ba01f2d25b8d4f82ab795748da4b5425dff1213bc3'
    for member,info in origin['members'].items():assert sha(archive/info['destination'])==info['sha256']
    old_synth=read(archive/'1_synth.json');old_grt=read(archive/'5_1_grt.json');old_fp=read(archive/'2_1_floorplan.json')
    assert old_synth['synth__design__instance__count__macros']==4
    assert old_synth['synth__design__instance__area__macros']==31525.5
    synth_q=old_synth['synth__design__instance__area__stdcell'];grt_q=old_grt['globalroute__design__instance__area__stdcell']
    projections={}
    die=list(map(float,arg(q['runner']['argv'],'--die-area',4)))
    core=list(map(float,arg(q['runner']['argv'],'--core-area',4)))
    assert die[0]==core[0] and die[2]==core[2]
    frame_y=round((core[1]-die[1])+(die[3]-core[3]),9)
    assert frame_y==.54
    for label,area in [('synthesis',synth_q),('global_route',grt_q)]:
        pr=archive_projection(area,requested[0],frame_y);pr['composed_geometry']=compose(pr['outline_um'],bf);projections[label]=pr
    metric_witness=dict(origin_sha256=sha(archive/'origin.json'),stdcell_synth_um2=synth_q,stdcell_grt_um2=grt_q,
        four_macro_area_um2=31525.5,observed_die_um2=old_grt['globalroute__design__die__area'],
        observed_core_um2=old_grt['globalroute__design__core__area'],
        observed_grt_stdcell_utilization=old_grt['globalroute__design__instance__utilization__stdcell'],
        synthesis_minimum_core_um2_before_reserves=31525.5+2*synth_q,
        requested_core_shortfall_um2_before_reserves=31525.5+2*synth_q-old_fp['floorplan__design__core__area'],
        uniform50pct_existing_outline_pass=False,
        actual_q_transfer=False,projections=projections,
        scope='Actual failed p12q9 checkpoint geometry/areas recovered from preserved retirement archive, source d417. Partial GRT is not final SS/FF or current fullmapped q. No checkpoint extracted or flow executed.')
    inputs=[QFAIL,QPRE,CLOCK,RAM,P5,P5LEF,SYNTHETIC,MACRO,FULL/'strict_structure.json',FULL/'1_synth.json',FULL/'readiness.json',
        Path('tools/uarch_model.py'),Path('tools/w10_final_element_fit.py')]
    inputs += [Path('tools/w10_fullmap_slot_fit.py')]+[p.relative_to(ROOT) for p in sorted((ROOT/archive).iterdir())]
    return dict(schema='opentallas.w10.final.element.fit.prerequisite.v1',verdict='ACTUAL_Q_FOOTPRINT_UNBOUND_FULL_ELEMENT_FIT_HOLD',
        source_sha256={str(p):sha(p) for p in inputs},adopt=False,physical_admission=False,jobs_launched=0,
        q_final_evidence=final_q_evidence(q,pre),
        geometry_sources=dict(requested_failed_outline_um=requested,
            requested_failed_density=float(arg(q['runner']['argv'],'--place-density')),
            historical_actual_p5_outline_um=measured_p5,historical_p5_is_current_PP_q=False,
            synthetic_head_placeholder_outline_um=lef_size(SYNTHETIC),synthetic_head_is_actual_q=False,
            note='Requested rectangle, historical nonclosing actual abstract and synthetic head placeholder are distinct source classes. None binds current q final area.'),
        physical_storage=dict(macro_size_um=macro,physical_macros_per_PP_pair=4,
            four_macro_LEF_area_um2=4*macro[0]*macro[1],logical_mates=2,logical_words_per_mate=8192,
            physical_parities_per_mate=2,physical_rows_per_parity=4096,
            logical_capacity_bits=2*8192*274,physical_capacity_bits=4*4096*274,
            model_macro_subtraction_um2=2*U.CONS_MACRO_MM2*1e6,
            model_storage_depth_density_ratio=U.ROM_DEPTH_OPTS['8192m8']['mb_per_mm2']/U.ROM_DEPTH_OPTS['4096m8']['mb_per_mm2'],
            scope='Exact parity capacity and actual macro geometry; they do not qualify the q logic/capture/mux/clock/pin-channel footprint. Do not subtract four4096 macro areas in place of the model two8192 baseline terms.'),
        fullmapped_element=dict(flops=91733,ICGs=8,physical_macros=4,stdcell_um2=62705.9,
            additional_clock_buffer_um2=clock['slot']['additional_clock_buffer_um2'],
            outline_um=bf,rows=625,density=.5,buffer_replicas=3873,
            exclusive_clock_channel_sites=33750,stdcell_spare_um2=clock['slot']['stdcell_spare_um2'],
            exactness_scope='13 retained cases/240 exact rows, XF8 projection; no current q geometry or contextual SS/FF credit.',
            actual_q_area_from_this_BF16_map=False,qualified_final_element=False),
        stage_q_footprint_ceilings=ceilings,geometry_only_substitutions=cases,
        archived_failed_q_area_witness=metric_witness,
        scalar_owner_dependency=dict(owner='Godel scalar-capacity owner',actual_extra_field_mm2=None,
            baseline_geometry_only_extra_headroom_at_S45_mm2=p45['current_geometry_headroom_mm2'],
            one_mm2_extra_reserve_sensitivity=scalar_sensitivity,
            formula='q_limit_um2(extra) = q_limit_um2(0) - extra_field_mm2*1e6/model_q_pairs_fractional',
            scope='Extra means incremental reserve beyond existing product scalar/hub charges. Unit sensitivity is not an actual scalar measurement; no duplicate scalar sizing.'),
        expert_owner_dependency=dict(owner='Ram0fb46',source=str(RAM),source_sha256=sha(RAM),
            expert_only_stage_count=ram['expert_only_stage_count'],experts_per_stage_capacity=ram['experts_per_stage_capacity'],
            historical_q_pair_mask=ram['geometry']['q_pairs'],historical_q_transfer=False,
            maximum_stage_expert_entries=max(s['expert_phase_entries'] for s in ram['stages']),
            expected_slices=ram['expected_slices'],integer_allocator_replayed_here=False,
            scope='Expert-only integer46 stages at historical3749 q mask is not the conditional45-stage fractional whole-field plan. No reallocation, scalar capacity or complete-stage fit credit.'),
        latency=dict(physical_element_latency_cycles=None,additional_interface_cycles=None,full_token_cycles=None,
            scope='LAT8 and inherited serial-domain model not changed; phase/capture/config/hops/protocol/scalar/SSFF remain unbound. Area-stage thresholds are not a qualified latency.'),
        constraints=clock['constraints'],headline_rate=None,
        remaining=['Current source-bound fullmapped q final LEF and SS/FF ETM/SDC/SPEF/netlist plus same-source exactness',
            'Integer full-stage q/BF16/dense/HC/constants allocation composed with Ram owner, not fractional capacity alone',
            'Godel incremental scalar/hub footprint and service latency beyond existing charges',
            'Confucius spatial clock/PG/terminal-cut and final buffer/hold/tap/endcap reserve; no duplication',
            'Clock duty remains retained trace evidence only; wire-power baseline subtraction unbound'],
        prior_failures='p12q9, c8, FRONT_PAR and bankmap failed records preserved, no retry/tuning/rebuild.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(build(),indent=2)+'\n')
