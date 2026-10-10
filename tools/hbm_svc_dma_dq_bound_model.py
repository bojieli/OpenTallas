"""Price the physical 32GiB region check before the default-off wrapper RTL."""
import argparse,json
from pathlib import Path

def legal(addr,count):
    return 1<=count<=256 and addr%32==0 and (addr&((1<<35)-1))+count*32<=1<<35

def planned_region_check(addr,count):
    sector=(addr>>5)&((1<<30)-1)
    return (sector>>9)!=(1<<21)-1 or (sector&511)+count<=512

def model():
    cases=0
    for region in range(4):
        for low in range(512):
            for count in range(1,257):
                a=(region<<35)+((1<<35)-512*32)+low*32
                assert planned_region_check(a,count)==legal(a,count)
                cases+=1
    return dict(schema=1,status='SIZED_BEFORE_BOUND_RTL',
        region_bytes=1<<35,full_address_bits=37,sector_address_bits=30,
        count_contract='1..256 sectors,32B-aligned; endexclusive may equal regionend',
        exact_identity='retain address37 bits including region[36:35]; reject crossregion, do not truncate/split',
        required_per_stack_replica_count=1,die_replica_count=4,
        arithmetic_bits=10,upper_region_and_bits=21,
        combinational_implementation='ifupper21sectorbits allones, low9sector+count9 <=512; earlier starts cannot cross withcount<=256',
        planned_pipeline_cycles=0,measured_SS_FF_timing=False,
        estimated_logic_reservation_um2_per_stack=30,
        estimated_logic_area_qualification='prospective10bitadder+upperAND+comparison; actualmapping/timing required',
        added_payload_boundary_bits=0,added_memory_port_B_per_cycle=0,
        legal_corner_exhaustive_cases=cases,
        MACs_per_cycle=0,compute_intensity=0,
        source_endpoint_first_DD_budget_cycles=320,
        physical_gate='HOLD fullwrapper SS/FF timing; existingclockuncertaintyunchanged')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    with args.output.open('x') as f:json.dump(model(),f,indent=2);f.write('\n')
