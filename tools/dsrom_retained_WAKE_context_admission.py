"""Actual retained WAKE loads, bounded local capacity and exact SS/FF endpoints.

No synthesis, timing, P&R or source changes. Construction floors do not admit
physical implementation until source-matched PG/CTS/IO exclusions are supplied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import dsrom_PAR2_mapped_q_growth_join as G

BASE=G.P.ROOT/'results/uarch/dsrom_retained_WAKE_context_admission_20261002'


def build():
    inp=BASE/'inputs';m,fields,macros,cfg,bands=G.build()
    raw=(inp/'model.json').read_bytes();retained=json.loads(raw)
    origins=json.loads((inp/'origins.json').read_text())
    for n,r in origins.items():
        h=hashlib.sha256((inp/n).read_bytes()).hexdigest()
        if h!=r.get('serialized_sha256',r.get('sha256')):raise ValueError('retained context pin changed')
    if retained['candidate']!=m['candidate']:raise ValueError('one candidate')
    validation=json.loads((inp/'validation.json').read_text())
    if validation['q_and_BF_real_WAKEDFF']!=8 or validation['q_and_BF_distinct_WAKE_outputs']!=8:
        raise ValueError('retained mapped8 output gate')
    geo=json.loads((inp/'geometry.json').read_text());classes={};total_floor=0;old_floor=0
    # Same FF-corner BUF4 master price already present in a910 construction.
    for name,n in [('q',1686),('bfcolumn',362)]:
        case=retained['cases'][name];old=G.json.loads((G.BASE/'mapped_element_a910.json').read_text())['elements'][name]
        wake=case['WAKE_retention']['cells']
        if len(wake)!=8 or len({tuple(c['connections']['QN']) for c in wake.values()})!=8:
            raise ValueError('actual retained8 cell/output identity')
        if any(not c['type'].startswith('DFF') or int(c['attributes']['keep'],2)!=1 or int(c['attributes']['dont_touch'],2)!=1 for c in wake.values()):
            raise ValueError('actual mapped DFF retention attributes')
        if case['outline_DBU']!=old['area']['proposed_outline_DBU']:raise ValueError('frame changed')
        if len(case['actual_ICG_cells'])!=8 or len(case['macro_identity_bijection'])!=4:
            raise ValueError('actual clock/macro inventory')
        corners={}
        price=old['clock_profiles']['ff']['buffer_cell_area_um2']/old['clock_profiles']['ff']['buffer_cells_capacitance_only']
        for corner,branches in case['SS_FF_clock_pin_loads'].items():
            count=sum(b['BUF4_capacitance_only']['cell_count'] for b in branches.values())
            corners[corner]=dict(actual_clock_nets=len(branches),
                actual_pin_cap_fF=sum(b['pin_cap_fF'] for b in branches.values()),
                buffer_cells_construction=count,buffer_cell_area_um2=count*price,
                includes_root_and_eight_gated_branches=True,
                no_wire_slew_or_CTS_closure=True)
        new_floor=corners['ff']['buffer_cell_area_um2']
        total_floor+=n*new_floor;old_floor+=n*old['clock_profiles']['ff']['buffer_cell_area_um2']
        # Retained mapped area includes all8 actual WAKE FFs. Do not re-add7.
        residual=case['available_cell_capture_reservation_um2']-case['source50pct_cell_debit_um2']-2*new_floor
        classes[name]=dict(replicas=n,outline_DBU=case['outline_DBU'],
            actual_mapped_cell_area_um2=case['mapped_cell_area_um2'],
            actual_geometry_cell_capture_capacity_um2=case['available_cell_capture_reservation_um2'],
            residual_after_clock_floor_at50pct_um2=residual,clock=corners,
            real8WAKE_pass=True,WAKE_extra7_already_in_mapped_area=True,
            PG_growth_strip_DBU=case['PG_template_growth_required_strip_DBU'],
            source_PDN_rectangles=geo[name]['source_PDN_template_rectangles'],
            translated_macro_pin_OBS_PG=geo[name]['translated_macro_pin_OBS_PG'],
            crossing_capacity_before_new_vias_clock_spacing=geo[name]['crossing_capacity'],
            actual_top_port_widths={k:dict(direction=p['direction'],bits=len(p['bits'])) for k,p in case['actual_top_ports'].items()},
            mapped_instances_unplaced=True,fullframe_routed_fit=False)
    # Positive extra root-clock floor only, no mapped-area savings credit.
    extra=max(0,2*(total_floor-old_floor)/1e6)
    m['area']['retained_full_root_clock_buffer_increment_at50pct_mm2']=extra
    m['area']['combined_noncontainment_policy_screen_mm2']+=extra
    m['area']['remaining_before_unpriced_interfaces_mm2']=858-m['area']['combined_noncontainment_policy_screen_mm2']
    m['retained_WAKE_context']=dict(origins=origins,classes=classes,
        all8actualWAKE_retained=True,old_a910_failure_preserved=True,
        full_clock_buffer_cell_floor_mm2=total_floor/1e6,
        no_actual_mapping_area_saving_credit=True,
        local_residual_is_not_free_die_or_routing_capacity=True)
    m['SS_FF_plan']=dict(period_ps=833.3333333333334,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        endpoints=[
          dict(path='rootclk ->8WAKE.D;8WAKE.QN -> corresponding8ICG.ENA',setup_edges=1,hold='actual launch edge; enable/minpulse and reset recovery/removal included'),
          dict(path='macro banks leaf4/5/6/7 CLK/address/CE -> matched MB/PP cap0/cap1 on leaf0',setup_edges=2,hold='actual launch edge; no arithmetic/control multicycle exception'),
          dict(path='selected cap0/cap1.Q through real hold/enable mux -> lane consumer leaf1',setup_edges=1,hold='actual crossleaf skew, data/valid/tag alignment'),
          dict(path='lane/chain/tree/return valid/control plus full BF optional compute',setup_edges=1,hold='original source clock edges and staged arithmetic')],
        actual_macro_SS_clkq_and_FF_hold_required=True,
        real_top_driver_arrival_slew_output_load_required=True,
        generated_clock_and_gating_insertion_skew_required=True,
        broad_source_SDC_must_be_endpoint_narrowed=True,
        input_output_zero_delay_not_admitted=True)
    m['context_build_gate']=dict(mapped_retention=True,reservation_geometry=True,
        macro_pin_OBS_PG_template=True,source_bound_extended_PG_via_exclusion_model=False,
        source_bound8WAKE_ICG_buffer_placement_cuts=False,
        real_parent_IO_arrival_load=False,
        selector_clock_reset_pin_corridor_context=False,
        endpoint_specific_SS_FF_constraints=False,
        no_cold_mapping_required=True,installed_CTS_or_PDN_not_a_prebuild_requirement=True,PnR_admitted=False,
        next='Arch exports extended qstrip PDN/via/channel union, physical clock cuts and parent IO; Epicurus fullselector port/clock context; source-specific STA plan above. Reuse mapped netlists.')
    m['geometry_G0']['mapped_q_BF_WAKE_G0_PASS']=True
    m['geometry_G0']['physical_build_admitted']=False
    m['schema']='opentallas.dsrom.retained-WAKE-context-admission.v1'
    m['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return m


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('immutable record')
    a.output.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
