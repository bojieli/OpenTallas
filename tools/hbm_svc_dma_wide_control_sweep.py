#!/usr/bin/env python3
"""Immutable successor sensitivity for source-mapped wide DMA tile area.

The historical combined2000um2/PC reserve is disproved by protected cache
metadata alone. This revision sweeps CACHE reserves separately from native
control and does not treat any planning utilization as an adoption limit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import hbm_svc_dma_wide_plan as W

ROOT=Path(__file__).resolve().parents[1]


def sweep(native_control_um2_per_pc=1000.0):
    assert native_control_um2_per_pc>=0
    historical=W.plan()
    native_path=ROOT/'results/uarch/hbm_svc_dma_physical_20261010/native32_reference_mappedshape.json'
    native=json.loads(native_path.read_text())
    assert native['verdict']=='PASS_mapped_shape' and not native['unmapped_cells']
    seq=ROOT/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib'
    # Inventory supplied by the minimum protected cache design: three
    # metadata flags per1024 records, paired; context payload remains separate.
    metadata_ff=3*1024*2
    metadata_area=metadata_ff*.37908
    context_ff=4096
    context_area=context_ff*.2916
    points=[]
    for cache in (5000,7000,10000):
        tiles=[]
        for t in historical['tiles']:
            pcs=len(t['pc_ids']);slot=t['w_um']*t['h_um']
            fixed=t['total_macro_ctrl_relay_area_budget_um2']-t['cache_native_controller_extra_budget_um2']
            cache_area=cache*pcs;native_area=native_control_um2_per_pc*pcs
            total=fixed+cache_area+native_area
            threshold={str(int(u*100)):dict(capacity_um2=slot*u,remaining_um2=slot*u-total,
                        reservation_fit=total<=slot*u) for u in (.60,.65,.70,.75)}
            tiles.append(dict(master=t['master'],pc_ids=t['pc_ids'],slot_um2=slot,
                actual_mapped_bank_and_macro_plus_relay_floor_um2=fixed,
                cache_control_reservation_um2=cache_area,native_control_reservation_um2=native_area,
                prospective_total_area_um2=total,prospective_utilization=total/slot,
                planning_thresholds=threshold,
                area_status='RESERVATION ONLY: actual cache/native mapping, CTS, hold, wires pending'))
        points.append(dict(cache_control_reserve_um2_per_pc=cache,native_control_reserve_um2_per_pc=native_control_um2_per_pc,
            tiles=tiles,maximum_prospective_utilization=max(t['prospective_utilization'] for t in tiles),
            fits_all_tiles_at_percent={str(p):all(t['planning_thresholds'][str(p)]['reservation_fit'] for t in tiles)
                for p in (60,65,70,75)},
            failures_by_percent={str(p):[t['master'] for t in tiles if not t['planning_thresholds'][str(p)]['reservation_fit']]
                for p in (60,65,70,75)}))
    source_files=[native_path,Path(__file__),ROOT/'tools/hbm_svc_dma_wide_plan.py',
                  ROOT/'results/uarch/hbm_svc_dma_physical_20261010/bank_wide_mappedshape.json',seq]
    return dict(schema=1,status='CURRENT_CONTROL_RESERVATION_SENSITIVITY_NOT_HARDENED_TOTAL',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        supersedes_current_fit_claim=dict(historical_commit='86cb03748',
            historical_evidence='results/uarch/hbm_svc_dma_physical_20261010/wide32_height480_sizing.json',
            historical_combined_reserve_um2_per_pc=2000,
            reason='paired protected metadata reset FF floor exceeds combined reserve even before context payload and native CAM',
            historical_record_preserved=True,current_adopted_total_fit=False),
        protected_cache_minimum=dict(metadata_records=1024,metadata_flags_per_record=3,paired=True,
            metadata_ff_count=metadata_ff,metadata_ff_cell='DFFASRHQNx1_ASAP7_75t_R',
            metadata_cell_area_um2=.37908,metadata_ff_area_floor_um2=metadata_area,
            context_payload_ff_count=context_ff,context_ff_cell='DFFHQNx1_ASAP7_75t_R',
            context_cell_area_um2=.2916,context_ff_area_floor_um2=context_area,
            combined_cache_ff_area_floor_um2=metadata_area+context_area,
            excludes=['cache address/selection logic','native CAM','CTS and hold repair','cell routing'],
            qualification='minimum proposed protected cache inventory, not mapped cache RTL area'),
        native_control=dict(reserve_um2_per_pc=native_control_um2_per_pc,
            reference_mapped_area_um2_per_pc=native['mapped_logic_area_um2_per_PC'],
            reference_mapping_commit='12f583320',reference_metadata_ff_count=native['metadata_bits'],
            reference_metadata_protected=native['mutable_metadata_protected'],
            reference_RTL_sha256=native['RTL_source_sha256'],
            protected_uplift_um2_per_pc=None,
            protected_uplift_allowance_um2_per_pc=native_control_um2_per_pc-native['mapped_logic_area_um2_per_PC'],
            status='unprotected native32 reference mapped; protected uplift UNKNOWN, separate1000 reservation provisional; no timing claim'),
        die=historical['die'],geometry_fit=historical['geometry_fit'],
        planning_policy='60/65/70/75% are sensitivity points; owner permits added area and closure cost, not arbitrary hard utilization caps',
        current_total_area_qualification='UNKNOWN: actual full cache/native mapping and physical obligations pending',
        points=points,route_admission=False,
        required_gates=['actual full cache and protected native-control mapping',
                        'real pin/corridor and hierarchy binding','measured resource admission',
                        'transaction exactness and actual>=90% HBM bandwidth',
                        'in-context SS setup/FF hold and DRC closure'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-control-um2-per-pc',type=float,default=1000)
    parser.add_argument('--out',type=Path)
    a=parser.parse_args();j=sweep(a.native_control_um2_per_pc)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        if a.out.exists():raise FileExistsError('Use a new immutable sensitivity record path')
        a.out.write_text(json.dumps(j,indent=2)+'\n')
    summary={k:v for k,v in j.items() if k!='points'}
    summary['points']=[{k:v for k,v in p.items() if k!='tiles'} for p in j['points']]
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
