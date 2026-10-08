#!/usr/bin/env python3
"""Pre-build conservative output endpoint inventory; no timing/area adoption."""
import argparse,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def build():
 stem='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2'
 m=json.loads((R/(stem+'.json')).read_text())
 return dict(schema='opentallas.softmax_egress_payload.v1',adopted=False,route_admitted=False,
 scope='Minimum source capture/store -> protected CDC -> actual destination store -> protected visibility receipt; separate conservative banks, no numerical attention engine',
 source_sha256={stem+s:hashlib.sha256((R/(stem+s)).read_bytes()).hexdigest() for s in ('.v','.json','_ss.lib','_ff.lib')},
 capture=dict(E_bits=8192,E_vectors=[8,40],BF16_bits=4096,BF16_vectors=32,initiation_interval=1,
 E_region=[72,111],BF16_packed_region=[112,127],BF16_vectors_per_row=2,
 encoder_lanes=128,encoded_full_row_register_bits=9216,encoded_half_row_register_bits=4608,
 capture_to_actual_macro_write_edges=1,half_pack_first_to_write_edges=2),
 banks=dict(source_instances=36,destination_instances=36,macro_bits=128*256,protected_row_bits=9216,
 source_data_bytes_used_T640=57344,destination_data_bytes_used_T640=57344,
 raw_macro_area_mm2=72*m['area']['macro_area_um2']/1e6,macro_width_um=94.824,macro_height_um=41.04,
 clkq_SS_ps=m['timing']['ss']['clk_to_q_ps'],separate_banks=True,
 shared_bank_arbitration_implemented=False,placement_capacity_qualified=False,
 parent_9x4_bank_slot_mm2=0.28446310656,conservative_two_slot_mm2=2*0.28446310656),
 transport=dict(data_packet_bits=1083,fields=dict(kind=1,epoch=32,tag=16,row=7,beat=3,payload=1024),
 receipt_packet_bits=56,receipt_fields=dict(kind=1,epoch=32,tag=16,row=7),depth=64,
 data_codewords=17,data_FIFO_array_bits=64*17*72,receipt_FIFO_array_bits=64*72,
 read_service_initiation_interval=3,source_serial_service_interval=4,
 T640_data_beats=448,T128_data_beats=192,T640_receipts=56,T128_receipts=24,
 finite_full_row_prefill=True,unilateral_reset_supported=False,reset='coordinated cold abort in both domains',
 stream_GHz=1.2,chain_GHz=0.9,source_serial_service_ns=4/1.2,destination_CDC_service_ns=3/.9),
 storage=dict(serial_row_components=2,conservative_component_FF_bits_each=23260,
 encoded_capture_FF_bits=13824,CDC_array_only_bits=64*18*72,control_FF_bits='record exact implemented inventory after elaboration',
 total_known_FF_floor_bits=2*23260+13824+64*18*72,
 excludes=['CDC protected pointers/head','endpoint controls','mapped combinational area','clock buffers']),
 order=['capture all E to actual source SRAM','drain typed E packets','destination commits complete rows in actual SRAM',
 'return protected epoch/tag/row visibility receipts','allow BF16 capture only after all E destination commits (actual attention P.V engine remains external)',
 'pack paired BF16 vectors','drain and commit BF16 rows','complete only after all destination receipts'],
 timing=dict(SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,physical_closure=False,
 serial_read_request_to_first_beat_edges=6,serial_read_request_to_eighth_beat_edges=34,
 macro_write_latency_edges_after_last_CDC_beat=2,receipt_after_actual_write_only=True,
 composed_single_user_latency='measured component edges will be reported; destination stalls are unbounded without parent service contract'),
 omissions=['numeric exp and BF16 normalization','attention P.V computation and FP32 E -> BF16 adapter','configuration snapshot',
 'production owner join','shared bank arbitration','SS/FF path closure and routing track capacity'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();s=json.dumps(build(),indent=2)+'\n'
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(s)
 else:print(s,end='')
