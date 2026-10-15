#!/usr/bin/env python3
"""Cost/throughput contract for real five-bank SM row staging; no adoption claim."""
import json

def model():
    return dict(schema='opentallas.hbm-svc-static-sm-rows.v1',
        macro='ot_sram_1r1w_128x256_m1_r2c2',macros_per_sm=5,sms_per_stack=8,
        macros_per_stack=40,macro_area_per_sm_um2=5*3893.853,
        macro_area_per_stack_um2=40*3893.853,
        banks=2,rows_per_bank=64,physical_payload_bits_per_row=1280,
        useful_payload_bits_per_row=1088,tag_bits_per_row=10,
        tag_storage_bits=1280,part_seen_storage_bits=640,
        scheduled_fill_sectors_per_cycle=1,fill_sectors_per_row=5,
        scheduled_read_rows_per_cycle=1,read_latency_edges=1,
        hbm_period_ps=1024,stream_period_ps=2500/3,
        phy_max_rows_per_hbm_cycle_at_four_pcs=0.8,
        phy_max_rows_per_stream_cycle_at_four_pcs=0.8*(2500/3)/1024,
        packet_bits=1099,packet_layout='{valid,tag10,scale64,weights1024}',
        scale_source='low64 of fifth real SRAM',
        compiler_fill_vs_read_calendar_bound=False,physical_qualified=False,adopted=False)

if __name__=='__main__':print(json.dumps(model(),indent=2))
