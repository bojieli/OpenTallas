#!/usr/bin/env python3
"""HC22 resource companion. R1 sources/receipt remain historical byte-identical."""
import argparse
import json
from pathlib import Path
import w16_gpu_hc_dot_schedule as D
import w16_gpu_hc_simt_contract as R


def build():
    costs,_=D.build()
    k=R.read(R.KERNEL);rf=k['register_file'];macro=R.read(R.MACRO)
    return dict(schema='opentallas.w16.HC22_resource_companion.v2',
        supersedes='results/uarch/w16_gpu_hc_simt_contract_20261001/contract_r1.json (historical5phase source pins retained)',
        costs=costs,shared=R.shared_layout(),
        RF=dict(logical_bytes_SM=rf['capacity_bytes_sm'],physical_bytes_SM=rf['physical_capacity_bytes_sm'],
            physical_bytes_die=rf['physical_capacity_bytes_die'],macro_count_die=2048,
            analytical_macro_outline_area_mm2=2048*macro['area']['macro_area_um2']/1e6,
            projection_allocation=costs['waves'][0]['projection']['allocation'],scalar_allocation=costs['scalar_RF']),
        ports=dict(RF_read_bits_cycle_SM=8192,RF_write_bits_cycle_SM=4096,shared_read_bytes_cycle=128,
            shared_write_bytes_cycle=128,shared_banks=32,RF_lane_read_ports=2,RF_lane_write_ports=1,
            mux_fanout={'RF_depth_select_bits_SM':8192,'RF_write_replica_fanout':2},
            logical_data_conductor_demand_SM=14336,physical_tracks=None,channel_capacity=None,slot_fit=None),
        preserved_transpose_cycles_operator=35248,
        pricing_role='All22 HC source phases explicitly priced under positive isolated assumptions. Not7007-cycle complete kernel; no free transpose, transport, credit, tree/barrier or publication.',
        bounded_operator_calendar_supplied=True,target_GPU_numerical_proof=False,
        physical_qualified=False,ready_to_build=False,headline_rate=None,
        pins={path:R.sha(path) for path in ('tools/w16_gpu_hc_simt_contract_r2.py','tests/test_w16_gpu_hc_dot_schedule.py')})


def check(r):
    for path,digest in r['pins'].items():R.require(R.sha(path)==digest,'r2 source drift '+path)
    D.check(r['costs'])
    fresh=build()
    # Cost source evidence remains its committed revision across parent cherry-pick.
    fresh['costs']=r['costs']
    R.require(fresh==r,'r2 resources drift')


def main():
    ap=argparse.ArgumentParser(description=__doc__);group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--out',type=Path);group.add_argument('--check',type=Path);a=ap.parse_args()
    if a.check:check(json.loads(a.check.read_text()))
    else:
        with a.out.open('x') as f:json.dump(build(),f,indent=2,sort_keys=True);f.write('\n')
    print('PASS HC22 r2 resource replay; R1 historical, physical qualification pending')


if __name__=='__main__':main()
