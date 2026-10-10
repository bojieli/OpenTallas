#!/usr/bin/env python3
"""Complete inventory successor: reserve every unbackpressured native beat.

Builds on immutable cache/native sensitivity without changing predecessors.
Only FF storage floors are priced for protected ingress; mux/protection/control
logic and physical repair remain UNKNOWN. No build or route admission.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import hbm_svc_dma_wide_control_sweep as C

ROOT=Path(__file__).resolve().parents[1]


def native_inventory():
    source=ROOT/'results/uarch/hbm_svc_dma_physical_20261010/ingress_model_cfc724c70.py'
    module=ast.parse(source.read_text())
    keyword=next(n for n in ast.walk(module) if isinstance(n,ast.keyword)
                 and n.arg=='native_response_ingress_before_II2_banks')
    # The pinned source dictionary contains literals and integer arithmetic.
    # No execution of the source model, imports or external paths is needed.
    assert not any(isinstance(n,(ast.Call,ast.Attribute,ast.Name)) for n in ast.walk(keyword.value))
    value=eval(compile(ast.Expression(keyword.value),str(source),'eval'),{'__builtins__':{}},{})
    return value,source


def sweep(native_control_um2_per_pc=1000.0):
    base=C.sweep(native_control_um2_per_pc)
    native,source=native_inventory()
    assert native['entries_per_PC']==128 and native['protected_storage_bits_per_PC']==40704
    assert not native['native_return_backpressure_allowed']
    assert native['reserve_every_burst_beat_before_native_issue']
    entries=native['entries_per_PC']
    payload_ecc=entries*(native['payload_bits_per_entry']+native['planned_SECDED_bits_per_entry'])
    metadata=entries*native['planned_paired_metadata_bits_per_entry']
    policies=[dict(name='data_ECC_unreset_metadata_reset',payload_ECC_FF_area_um2=payload_ecc*.2916,
                   paired_metadata_FF_area_um2=metadata*.37908,
                   area_floor_um2_per_pc=payload_ecc*.2916+metadata*.37908,
                   qualification='data/ECC no reset; protected metadata reset; control/reset RTL gate pending'),
              dict(name='all_storage_reset_conservative',payload_ECC_FF_area_um2=payload_ecc*.37908,
                   paired_metadata_FF_area_um2=metadata*.37908,
                   area_floor_um2_per_pc=(payload_ecc+metadata)*.37908,
                   qualification='sensitivity if implementation resets all storage, not a required reset policy')]
    points=[]
    for policy in policies:
        for point in base['points']:
            tiles=[]
            for old in point['tiles']:
                count=len(old['pc_ids']);floor=count*policy['area_floor_um2_per_pc']
                total=old['prospective_total_area_um2']+floor
                tests={str(p):dict(capacity_um2=old['slot_um2']*p/100,
                       remaining_ff_floor_um2=old['slot_um2']*p/100-total,
                       reservation_floor_fit=total<=old['slot_um2']*p/100) for p in (65,70,75,80)}
                tiles.append(dict(master=old['master'],pc_ids=old['pc_ids'],slot_um2=old['slot_um2'],
                    existing_bank_cache_native_relay_reservation_um2=old['prospective_total_area_um2'],
                    protected_ingress_storage_bits=count*(payload_ecc+metadata),
                    protected_ingress_FF_area_floor_um2=floor,
                    ingress_mux_protection_control_logic_um2=None,
                    ingress_pointer_credit_reservation_logic_um2=None,
                    complete_inventory_area_floor_um2=total,complete_inventory_utilization_floor=total/old['slot_um2'],
                    planning_thresholds=tests,
                    qualification='floor only; all additional ingress logic/CTS/hold/routing remains UNKNOWN'))
            points.append(dict(cache_reserve_um2_per_pc=point['cache_control_reserve_um2_per_pc'],
                native_control_reserve_um2_per_pc=native_control_um2_per_pc,
                ingress_FF_policy=policy['name'],ingress_FF_area_floor_um2_per_pc=policy['area_floor_um2_per_pc'],
                tiles=tiles,max_complete_inventory_utilization_floor=max(t['complete_inventory_utilization_floor'] for t in tiles),
                fits_all_floor_reservations_at_percent={str(p):all(t['planning_thresholds'][str(p)]['reservation_floor_fit'] for t in tiles)
                    for p in (65,70,75,80)},
                failures_by_percent={str(p):[t['master'] for t in tiles if not t['planning_thresholds'][str(p)]['reservation_floor_fit']]
                    for p in (65,70,75,80)}))
    inputs=[source,Path(__file__),ROOT/'tools/hbm_svc_dma_wide_control_sweep.py',
            ROOT/'results/uarch/hbm_svc_dma_physical_20261010/native32_reference_mappedshape.json',
            ROOT/'results/uarch/hbm_svc_dma_physical_20261010/bank_wide_mappedshape.json',
            ROOT/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib']
    return dict(schema=1,status='COMPLETE_INGRESS_STORAGE_FLOOR_SENSITIVITY_NOT_MAPPED_TOTAL',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        native_model_source_commit='cfc724c70',native_ingress_source_inventory=native,
        predecessor=dict(cache_native_only_record='results/uarch/hbm_svc_dma_physical_20261010/wide32_control_reserve_sensitivity.json',
            predecessor_record_preserved=True,predecessor_does_not_include_mandatory_native_ingress=True,
            four_entry_proposal_admission='FAIL preserved: PHY cannot be backpressured; reserve all beats before native issue'),
        storage=dict(entries_per_bank=32,banks_per_pc=4,entries_per_pc=entries,
            payload_ECC_bits_per_pc=payload_ecc,paired_metadata_bits_per_pc=metadata,
            total_protected_bits_per_pc=payload_ecc+metadata,
            total_protected_bits_four_stacks=128*(payload_ecc+metadata),
            additional_to_cache_context_and_native_CAM=True,
            DFFHQNx1_area_um2=.2916,DFFASRHQNx1_area_um2=.37908,
            policies=policies,logic_area_um2=None),
        admission_contract=dict(PHY_return_backpressure=False,reserve_every_burst_beat_before_issue=True,
            reservation_release='dispatch queued beat into fixed write-commit pipeline',
            worst_case_four_sector_native_leases_per_pc=32,arbitrarily_unbalanced_bank_stream_guarantee=False),
        native_reference=base['native_control'],protected_cache_minimum=base['protected_cache_minimum'],
        die=base['die'],geometry_fit=base['geometry_fit'],points=points,
        current_total_fit='UNKNOWN: actual complete protected ingress/cache/native mapping and physical closure pending',
        planning_policy='65/70/75/80% sensitivity points, not hard adoption caps; spend area for physical closure',
        route_admission=False,bulk_jobs_launched=False,
        required_gates=['actual complete protected ingress mapping and bank occupancy/reservations',
                        'every PHY return accepted without backpressure at full workload',
                        'exactness and measured >=90% real HBM roof',
                        'real corridor, clock, SS setup/FF hold and DRC closure'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-control-um2-per-pc',type=float,default=1000)
    parser.add_argument('--out',type=Path)
    a=parser.parse_args()
    if a.out and a.out.exists():raise FileExistsError('Use a new immutable record path')
    j=sweep(a.native_control_um2_per_pc)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(j,indent=2)+'\n')
    summary={k:v for k,v in j.items() if k!='points'}
    summary['points']=[{k:v for k,v in p.items() if k!='tiles'} for p in j['points']]
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
