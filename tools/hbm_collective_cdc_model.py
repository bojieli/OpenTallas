#!/usr/bin/env python3
"""Full-depth protected link CDC candidate; independent of packetSRAM adoption."""
import json

def model(width=545,aw=6,replicas=16):
 words=(width+63)//64;depth=1<<aw
 return dict(status='CANDIDATE_NOT_ADOPTED',width=width,depth=depth,replicas=replicas,
  implementation='Encoded dual-clock flop storage, protected local pointers/head reused from W2; registered Gray/complement rails through2sync stages',
  payload_bits=replicas*depth*width,encoded_storage_bits=replicas*depth*words*72,
  protected_banks_bits_per_fifo=(2*(1+5)+(words+5))*72,
  protected_banks_failure_rails_per_fifo=6,
  gray_rails_bits_per_fifo=4*(aw+1)+4*2*(aw+1),
  ports=dict(write_bits_per_wclk=words*72,read_capture_bits_per_rclk=words*72,read=1,write=1),
  compute=dict(macs_per_cycle=0,encode_slices=words,head_check_slices=words),
  normal_timing=dict(read_initiation_interval=3,head_capture_plus_validate_cycles=2,gray_sync_stages=2,credit_return='read pointer advances only upon consumer acceptance, then2write sync stages'),
  fault_timing='singleerror repair holds bank for fivephase sequence per faultyword; no guessed finite latency on incoherent CDC rails',
  boundary=dict(core_period_ps=833.333333,link_period_ps=833.333333,relationship='asynchronous',reset='coordinated coldPOR, independent asyncassert/syncrelease from actual die entry; no unilateral runtime reset'),
  area='flopcount sized above; SS/FFcell mapping/area/floorplan pending, no2mm²fit claim',
  composed_cost='Additional2read cycles and readII3 must be included per CDC queue in matched endpoint calendar before adoption',
  routing='545payload bits +Gray/complement28bits across two clockregions per FIFO; physicalroute length/track capacity pending',
  predecessor='rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_cdc.sv AW3 implementation preserved',
  adoption_gates=['independentclock full64depth exactness','storage/pointer/rail corruption','coordinatedreset/drain','fullnativeTU creditcapacity/latency','contextualmacro/cell SS/FF physical closure'])
if __name__=='__main__': print(json.dumps(model(),indent=2))
