#!/usr/bin/env python3
"""Immutable actual mapped cache successor, with epoch-protected ingress floor.

All16 original wide tile footprints and full face/clock relay obligations are
retained. No outline change, route, or unmeasured protection-area credit.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import hbm_svc_dma_wide_plan as W

ROOT=Path(__file__).resolve().parents[1]


def model():
    directory=ROOT/'results/uarch/hbm_svc_dma_physical_20261010'
    pc_path=directory/'cache_pc_mappedshape_a8717d65e.json'
    pc=json.loads(pc_path.read_text())
    assert pc['verdict']=='PASS_mapped_shape' and not pc['unmapped_cells']
    native_path=directory/'native32_reference_mappedshape.json'
    native=json.loads(native_path.read_text())
    assert native['verdict']=='PASS_mapped_shape' and not native['unmapped_cells']
    epoch_source=directory/'ingress_model_b8a17bef3.py'
    node=next(n.value for n in ast.walk(ast.parse(epoch_source.read_text()))
              if isinstance(n,ast.keyword) and n.arg=='native_response_ingress_before_II2_banks')
    assert not any(isinstance(n,(ast.Call,ast.Attribute,ast.Name)) for n in ast.walk(node))
    ingress=eval(compile(ast.Expression(node),str(epoch_source),'eval'),{'__builtins__':{}},{})
    assert ingress['protected_storage_bits_per_PC']==40960
    wide=W.plan()
    payload=128*(256+32);paired=128*32
    policies=[dict(name='payload_ECC_unreset_metadata_reset',area_um2_per_pc=payload*.2916+paired*.37908),
              dict(name='all_ingress_storage_reset',area_um2_per_pc=(payload+paired)*.37908)]
    native_reserves=[dict(name='unprotected_reference_floor',area_um2_per_pc=native['mapped_logic_area_um2_per_PC'],
                         protected=False,protected_uplift_um2=None),
                     dict(name='provisional1000_protected_reserve',area_um2_per_pc=1000,
                         protected=None,protected_uplift_um2=None)]
    points=[]
    for policy in policies:
        for nr in native_reserves:
            tiles=[]
            for template in wide['tiles']:
                count=len(template['pc_ids']);slot=template['w_um']*template['h_um']
                actual_cache_banks_macro=count*pc['total_PC_area_um2']
                ingress_ff=count*policy['area_um2_per_pc']
                native_area=count*nr['area_um2_per_pc']
                relay=template['relay_ff_area_floor_um2']
                total=actual_cache_banks_macro+ingress_ff+native_area+relay
                thresholds={str(p):dict(area_budget_um2=slot*p/100,remaining_floor_um2=slot*p/100-total,
                        floor_fit=total<=slot*p/100) for p in (65,70,75,80)}
                tiles.append(dict(master=template['master'],w_um=template['w_um'],h_um=template['h_um'],
                    pc_ids=template['pc_ids'],slot_um2=slot,
                    macro_count=len(template['macros']),macro_geometry_fit=template['macro_geometry_fit'],
                    actual_cache_controller_area_um2=count*pc['mapped_controller_area_um2_per_PC'],
                    actual_hard_bank_logic_area_um2=count*pc['hard_bank_logic_area_um2_per_PC'],
                    actual_eight_macro_area_um2=count*pc['eight_real_macro_area_um2_per_PC'],
                    actual_total_cache_pc_area_um2=actual_cache_banks_macro,
                    native_reference_or_reservation_um2=native_area,
                    native_protected_uplift_um2=None,
                    epoch_protected_ingress_storage_bits=count*40960,epoch_protected_ingress_FF_floor_um2=ingress_ff,
                    ingress_decoder_publication_slots=None,ingress_decoder_publication_area_um2=None,
                    ingress_mux_protection_pointer_control_area_um2=None,
                    physical_face_traffic_bits=wide['physical_replicated_slice_face_bits_per_stack'],
                    logical_face_traffic_bits=wide['logical_face_bits_per_stack'],
                    relay_reservation_ff_count=template['relay_reservation_ff_count'],relay_FF_area_floor_um2=relay,
                    face_clock_roots=8,slice_height_um=120,source_clock_latency_ps=None,
                    clock_CTS_hold_routing_added_area_um2=None,
                    measured_cache_plus_reserved_native_ingress_relay_area_floor_um2=total,
                    total_utilization_floor=total/slot,planning_thresholds=thresholds,
                    current_total_area='UNKNOWN; additional finite decoder/publication/control/clock/hold/wiring costs not measured'))
            points.append(dict(ingress_FF_policy=policy['name'],native_reserve_policy=nr['name'],
                ingress_FF_floor_um2_per_pc=policy['area_um2_per_pc'],native_area_um2_per_pc=nr['area_um2_per_pc'],
                tiles=tiles,max_total_utilization_floor=max(t['total_utilization_floor'] for t in tiles),
                fits_all_floors_at_percent={str(p):all(t['planning_thresholds'][str(p)]['floor_fit'] for t in tiles)
                    for p in (65,70,75,80)},
                failures_by_percent={str(p):[t['master'] for t in tiles if not t['planning_thresholds'][str(p)]['floor_fit']]
                    for p in (65,70,75,80)}))
    sources=[pc_path,native_path,epoch_source,Path(__file__),ROOT/'tools/hbm_svc_dma_wide_plan.py',
             ROOT/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib']
    return dict(schema=1,status='ACTUAL_CACHE_AND_EPOCH_INGRESS_FLOOR_NOT_COMPLETE_MAPPED_TOTAL',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        cache_mapping_commit='a8717d65e',cache_mapped_controller_um2_per_pc=pc['mapped_controller_area_um2_per_PC'],
        cache_actual_four_bank_eight_macro_um2_per_pc=pc['total_PC_area_um2'],
        cache_RTL_sha256=pc['RTL_source_sha256'],cache_mapping_scope=pc['scope'],
        predecessor_combined2000_budget_verdict=pc['reservation_verdict'],
        previous_guessed_cache_sensitivities_preserved=True,
        epoch_ingress_model_commit='b8a17bef3',epoch_ingress_source_inventory=ingress,
        ingress_bits=dict(payload_ECC_bits_per_pc=payload,paired_slot_index_epoch_fault_bits_per_pc=paired,
            total_bits_per_pc=40960,total_bits_four_stacks=40960*128,
            adds_two_epoch_paired_bits_per_entry=True,finite_decoder_publication_slots=None,
            pointer_control_mux_logic_area_um2=None),
        native=dict(reference_mapped_um2_per_pc=native['mapped_logic_area_um2_per_PC'],
            reference_metadata_protected=False,protected_uplift_um2_per_pc=None,
            reserve_um2_per_pc=1000,reserve_is_provisional=True,RTL_sha256=native['RTL_source_sha256']),
        die=dict(**wide['die'],horizontal_reticle_headroom_um=33000-wide['die']['proposed_outline_um'][0],
            vertical_reticle_headroom_um=26000-wide['die']['proposed_outline_um'][1],
            outline_changed_in_this_revision=False,horizontal_growth_not_assumed=True),
        geometry_fit=wide['geometry_fit'],points=points,current_total_fit='UNKNOWN',route_admission=False,
        bulk_jobs_launched=False,
        required_gates=['actual protected ingress full mapping including finite decoder publication and pointer/control',
                        'protected native successor measured mapping','real corridors and VM inventory',
                        'every PHY response accepted without backpressure; exact transactions and measured>=90%HBMroof',
                        'in-context SS/FF physical closure and measured host admission'],
        planning_policy='65/70/75/80% sensitivity floors; actual need drives area or die changes, no arbitrary adoption cap')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path)
    a=parser.parse_args()
    if a.out and a.out.exists():raise FileExistsError('Use a new immutable inventory path')
    j=model()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(j,indent=2)+'\n')
    summary={k:v for k,v in j.items() if k!='points'}
    summary['points']=[{k:v for k,v in p.items() if k!='tiles'} for p in j['points']]
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
