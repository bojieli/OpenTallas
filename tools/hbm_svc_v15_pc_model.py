#!/usr/bin/env python3
"""Pre-build sizing for distributed PHY-only variable-latency service leaves."""
from hbm_svc_static_landing_model import model
import json

def pc_model():
    m=model();return dict(schema='opentallas.hbm-svc-v15-pc.v1',macro=m['macro'],macros_per_pc=1,
        pcs_per_stack=32,stacks=4,macro_area_per_stack_um2=m['array_area_um2'],
        sectors_per_bank=64,banks=2,capacity_bytes_per_stack=m['capacity_bytes'],
        phy_outstanding_per_pc=1,read_request_ii='PHY request and response latency plus one capture edge',
        write_request_ii='one SRAM read edge plus capture and PHY acceptance/completion',
        scheduled_output_bytes_per_pc_cycle=32,scheduled_pc_parallelism=8,
        scheduled_block_cycles=256,scheduled_block_bytes=65536,
        fill_bytes_per_pc_cycle=32,phy_bits_per_pc=622,
        scheduled_payload_boundary_bits_per_pc=256,valid_bits_per_pc=128,
        controller_state_bits_per_pc_upper_bound=300,macs_per_cycle=0,
        mux_cost='one 1R1W SRAM; static drain vs PHY-writeback read exclusion; HBM fill vs scheduledfill exclusion',
        routing_tracks_needed_per_pc=622+256,routing_capacity=None,
        slot_fit=None,timing_closed=False,compiler_calendar_bound=False,adopted=False,
        composition='prefetch64sectors then one blockready check; 256 fixed8PCgroup drain slots; no production perlane ready')
if __name__=='__main__':print(json.dumps(pc_model(),indent=2))
