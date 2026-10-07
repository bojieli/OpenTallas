#!/usr/bin/env python3
"""Atomic exact softmax configuration, sized before minimum component RTL."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
 sources=['rtl/hdc/v41x/ot_dsrom_su_softmax.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv']
 return dict(schema='opentallas.softmax_config_snapshot.v1',adopted=False,route_admitted=False,
 source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
 payload=dict(bits=2602,low_to_high=['nv7','lt3','scale32','sink512','cos1024','sin1024'],beats1024=3,last_beat_used_bits=554,last_beat_zero_padding_bits=470,epoch_bits=32,tag_bits=16),
 protection=dict(SECDED_words64=41,staging_encoded_bits=2952,protected_bank_bits=(41+5)*72+2,wrapper_complemented_fields=dict(phase=3,beat_count=2,epoch=32,tag=16),wrapper_bits=106,total_state_bits=6372,encode_slices=16,decode_check_slices=41,
 semantics='Only nv8/lt3 and nv40/lt6 qualify current T128/T640 H16/LPH16 shapes. Other config words preserve exact bits; finite/numerical coefficient validity remains compiler-owned.',
 repair='Staging remains encoded. Protected bank corrects single errors before launch. Any loss of normal after lock aborts the row; core has no ready and cannot transparently pause for five-edge repair.'),
 memory=dict(SRAM_instances=0,write_bytes_per_accept=128,staging_to_bank_encoded_bits=2952,output_bits_per_cycle=2602),
 compute=dict(MAC_per_cycle=0,configurations_per_three_accepted_input_beats=1),
 area=dict(FF_body_floor_mm2=6372*.2916/1e6,encoder_decoder_mux_control_area=None,replicas=1,physical_slot=None),
 routing=dict(input_bits=1024+2+32+16+1,output_bits=2602+32+16+1,internal_stage_to_bank_tracks=2952,channel_capacity=None),
 timing=dict(clock_GHz=1.2,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
 fault_free='Final beat edgeN writes staging; N+1 loads immutable protected bank; N+2 validates nv/lt; N+3 earliest consumer lock. With ingressCDC II3 and3beats, firstbeat to lock9streamedges absentstalls.',
 config_must_precede_first_score=True,configuration_kept_until='matching epoch/tag consumer-retired release',parent_added_token_cost_ns_without_overlap=9/1.2),
 missing=['Integration of three configuration packets into epoch owner','Actual numerical core fault/output-abort binding','Mapped area/slot and native SS/FF boundary qualification'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();s=json.dumps(build(),indent=2)+'\n'
 if a.output:a.output.write_text(s)
 else:print(s,end='')
