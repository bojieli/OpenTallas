#!/usr/bin/env python3
"""Actual sector-addressed eight-lane WB PHY-boundary staging budget."""
import json

def model():
 return dict(schema='opentallas.hbm-svc-wb-block-cdc.v1',lanes=8,banks=2,
  sectors_per_bank=2048,rows_per_lane_per_bank=256,macros_per_lane=4,
  macros=32,macro='ot_sram_1r1w_128x256_m1_r2c2',macro_area_um2=32*3893.853,
  fifo_width=288,fifo_aw=2,fifo_payload_ff=8*288*4,
  metadata_fifo_ff=2*29*4,pc_payload_capture_ff=0,
  reset_sync_ff=4,fault_sync_ff=4,
  reset_contract='either external reset asserts both domains; two local edges synchronously release each domain',
  stream_fixed_sectors_per_cycle=8,stream_mhz=1200,hbm_mhz=976.5625,
  stream_period_ps=833.3333333333,hbm_period_ps=1024,
  copy_read_enqueue_min_cycles_per_row=2,
  address_units='full native sector30, no byte conversion or PC-bit stripping',
  pc_hash='s[6:2] XOR s[11:7] XOR s[16:12]',
  admission='one bank-free reservation before fixed fill pulse train',
  completion='all actual per-PC k_wr_done then asynchronous block ACK',
  done_sectors_bits=12,done_sectors_source='matching ACK FIFO total, qualified by done_v',
  variable_wait_location='HBM PHY boundary only',physical_qualified=False,adopted=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
