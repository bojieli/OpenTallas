#!/usr/bin/env python3
"""Bind actual complete-element maps to one geometry/clock budget successor."""
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_noECC_complete_element_mapping_20261002/terminal_pair'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n):return json.loads((BASE/'inputs'/n).read_text())
def snap(n):return math.ceil(n/2160)*2160
def buffer_tree(load,prices):
    """Capacitance-only BUFx4 tree; no wire/slew/skew upper-bound claim."""
    b=prices['BUFx4_ASAP7_75t_R'];limit=prices['ICGx1_ASAP7_75t_R']['pins']['GCLK']['max_capacitance']
    if load<=limit:return dict(end_buffers=0,parent_buffers=0,cell_count=0,ICG_load_fF=load,wire_budget_at_ICG_fF=limit-load)
    end=math.ceil(load/b['pins']['Y']['max_capacitance']);count=end;parent=0
    demand=end*b['pins']['A']['capacitance']
    while demand>limit:
        n=math.ceil(demand/b['pins']['Y']['max_capacitance']);parent+=n;count+=n;demand=n*b['pins']['A']['capacitance']
    return dict(end_buffers=end,parent_buffers=parent,cell_count=count,ICG_load_fF=demand,wire_budget_at_ICG_fF=limit-demand)

def build():
    hashes=json.loads((BASE/'input_hashes.json').read_text())
    for name,h in hashes.items():
        if sha(BASE/name)!=h:raise ValueError('mapped evidence changed '+name)
    q=load('q_inventory.json');bf=load('BF_terminal.json')['runs'][0]['inventory'];prices=load('clock_cell_prices.json')
    reserve=load('element_reservation.json');selector=load('selector_current.json');join=load('source_geometry_current.json')
    if join['candidate']!=reserve['candidate']:raise ValueError('candidate mismatch')
    output={}
    for case,inv,cls in [('q',q,'q_pair'),('bfcolumn',bf,'BF16_column_pair')]:
        r=reserve['elements'][cls];profiles={};bufcounts=[];bufareas=[]
        for corner,m in inv.items():
            if m['raw_4096_macro_count']!=4 or m['unmapped_nonmacro_types']:raise ValueError('incomplete hardware map')
            branches={}
            for k,v in m['clock_nets'].items():
                if v['source_ICG']=='root':continue
                branches[v['source_ICG']]=dict(actual_pin_cap_fF=v['pin_cap_fF'],sinks=v['sinks'],
                    source_unbuffered_ICG_cap_ratio=v['pin_cap_fF']/46.08,
                    capacitance_only_BUF4_construction=buffer_tree(v['pin_cap_fF'],prices[corner]))
            n=sum(x['capacitance_only_BUF4_construction']['cell_count'] for x in branches.values())
            bufcounts.append(n);bufareas.append(n*prices[corner]['BUFx4_ASAP7_75t_R']['area_um2'])
            profiles[corner]=dict(branches=branches,buffer_cells_capacitance_only=n,
                buffer_cell_area_um2=bufareas[-1],root_clock_pin_cap_fF=sum(x['pin_cap_fF'] for x in m['clock_nets'].values() if x['source_ICG']=='root'),
                all_mapped_clock_pin_cap_fF=sum(x['pin_cap_fF'] for x in m['clock_nets'].values()),
                buffer_construction_not_STA_CTS_or_route=True)
        cell_area=inv['ss']['stdcell_area_um2']
        repair_wake=(8-inv['ss']['distinct_WAKE_FF_output_nets'])*prices['ss']['DFFASRHQNx1_ASAP7_75t_R']['area_um2']
        capture_area=sum((x['bbox_DBU'][2]-x['bbox_DBU'][0])*(x['bbox_DBU'][3]-x['bbox_DBU'][1])/1e6 for x in r['capture_regions'])
        w=r['outline_DBU'][2];oldh=r['outline_DBU'][3];cut=r['compute_control_clock_region_DBU'][0]
        cells_with_construct=cell_area+max(bufareas)+repair_wake
        required_core=2*cells_with_construct
        available=r['area_reservation']['proposed_remaining_cell_region_plus_capture_strips_um2']
        newh=max(oldh,snap((required_core-capture_area)*1e6/(w-cut)))
        ff=sum(n for k,n in inv['ss']['master_counts'].items() if k.startswith('DFF'))
        raw=gzip.decompress((BASE/case/'mapped.json.gz').read_bytes())
        output[case]=dict(source_class=cls,mapped_json_sha256=hashlib.sha256(raw).hexdigest(),
            hardware_cells=inv['ss']['cells'],FF_cells=ff,ICG_cells=inv['ss']['master_counts']['ICGx1_ASAP7_75t_R'],physical_macros=4,
            mapped_stdcell_area_um2=cell_area,capture_FF=inv['ss']['capture_flops_identified'],
            source_full_carrier_capture_bits=1096,unused_high2_per_bank_optimized_FF_only=8,
            physical_macro_width_bits=274,source_capture_enable_block='literal element.sv746..749; SS/FF actual mapped source provenance retained',
            clock_profiles=profiles,actual_FF_provenance=inv['ss']['source_FF_count_by_location'],
            WAKE=dict(declared_local_regs=8,distinct_mapped_output_nets=inv['ss']['distinct_WAKE_FF_output_nets'],
                source_keep_dont_touch_nets_preserved=True,required_local_replica_retention_PASS=False,
                mandatory_synthesis_attribute_propagation_not_new_engine_logic=True,
                modeled_7missing_WAKE_FF_cell_um2=repair_wake,
                no_new_q_resynthesis_in_this_record=True),
            area=dict(previous_outline_DBU=r['outline_DBU'],previous_allocated_cell_and_capture_um2=available,
                measured_cell_area_at_source50pct_um2=2*cell_area,
                current_reservation_margin_before_CTS_wire_um2=available-2*cell_area,
                modeled_capacitance_only_clock_buffer_cell_um2=max(bufareas),
                modeled_clock_and_8local_WAKE_core_um2=required_core,
                deterministic_positive_only_height_DBU=newh,
                proposed_outline_DBU=[0,0,w,newh],
                extra_reservation_over_already_priced_frame_um2=w*(newh-oldh)/1e6,
                maxwell_must_replace_named_frame_once=True,no_shrink_or_area_credit=True,
                extra_clock_wire_slew_hold_PG_vias_not_zero_or_free=True),
            SSFF_setup_hold_closed=False,physical_G0=False)
    return dict(schema='opentallas.dsrom.noECC.mapped-complete-element-join.v1',candidate=reserve['candidate'],
        generator_sha256=sha(Path(__file__)),input_hashes_sha256=sha(BASE/'input_hashes.json'),elements=output,
        source_manifest_sha256=sha(BASE/'inputs/physical_source_manifest.json'),literal_source_files=21,
        macro_depth=4096,physical_macros_per_logical_slot=2,no_NP_depth_stage_TP_sweep=True,
        current_parent_source_join=dict(commit='4c6720068bef9950993182216c0a897865f2706b',
            native_local_retirement=join['source_capacity']['native_local_retirement'],
            no_new_ACK_wire_or_global_request_pool=join['source_capacity']['no_new_local_ACK_wire'],
            parent_CFG_VM_root_origins_not_assumed_free=True),
        current_selector=dict(commit='4d3b551e7',slot=selector['slot_proposal'],
            composed_ROM=selector['composition']['ROM'],old1p5088_proxy_is_historical_only=True,
            actual_provider_operator_count_still_owned_by_Maxwell_Epicurus=True),
        capture_constraints=reserve['capture_constraints'],
        ROM_ECC_required=False,configuration_ROM_ECC_required=False,
        SRAM_HBM_link_mutable_control_protection_retained=True,
        physical_admission=dict(PnR=False,reason='Actualmaps show localWAKE replicas merged; clocktrees notinstalled or timed, q cellreservation too small. Preserve literal arithmetic/ports and qualify actual keeper/buffer/capture context beforeP&R.',
            next='Propagate existing localWAKE keep/dont_touch intent to realFFcells in synthesis contract; model complete mapped branch buffering/placement and actual parent IO. Reuse current maps for all inventory/timing preparation; no duplicate q/BF synthesis under unchanged flow.'),
        failed_records_unchanged=True,full_token_or_parent_die_closure=False)

if __name__=='__main__':
    out=BASE/'model.json';data=(json.dumps(build(),indent=2,sort_keys=True)+'\n').encode()
    if out.exists() and out.read_bytes()!=data:raise ValueError('preserve prior verdict; successor required')
    out.write_bytes(data);print(sha(out))
