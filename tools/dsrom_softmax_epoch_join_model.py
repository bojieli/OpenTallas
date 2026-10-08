#!/usr/bin/env python3
"""Protected epoch/phase/SRAM integration admission for a minimum component."""
import argparse,hashlib,json
from pathlib import Path
from dsrom_softmax_bank_census import build as bank_census
ROOT=Path(__file__).resolve().parents[1]
def build():
    b=bank_census();w=b['macro']['width_um'];h=b['macro']['height_um'];width=9*w+8*30;height=4*h+3*32
    fields=dict(active=1,epoch=32,last_epoch=32,have_epoch=1,tag=16,failed=1)
    fifo=lambda words:64*words*72+(2*(1+5)+(words+5))*72+6+84
    sources=['tools/dsrom_softmax_cdc_model.py','tools/dsrom_softmax_sram_join_model.py','tools/dsrom_softmax_bank_census.py','rtl/experimental/dsrom_softmax_transport_20261007/ot_dsrom_softmax_phase.sv','rtl/experimental/dsrom_softmax_transport_20261007/ot_dsrom_softmax_sram_join.sv']
    return dict(schema='opentallas.softmax_epoch_join_prebuild.v1',adopted=False,route_admitted=False,
      scope='Actual score/PV SRAM and no-ready replay, protected phase events and bidirectional epoch CDC; E/BF16 payload endpoint retirement is an explicit external receipt contract',
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
      packet=dict(ingress_bits=1084,fields=dict(opcode=2,epoch=32,row_tag=16,row_address=7,beat=3,payload=1024),ingress_SECDED_words=17,completion_bits=64,completion_fields=dict(epoch=32,tag=16,reserved_zero=16),completion_SECDED_words=1,opcodes={'0':'begin; payload[0] short','1':'score/PV data; row region implies kind','2,3':'illegal'}),
      state=dict(wrapper_protected_fields=fields,wrapper_FF_bits=2*sum(fields.values()),ingress_FIFO_bits=fifo(17),completion_FIFO_bits=fifo(1),reset_bits=4,total_incremental_FF_bits=2*sum(fields.values())+fifo(17)+fifo(1)+4,area_FF_body_floor_mm2=(2*sum(fields.values())+fifo(17)+fifo(1)+4)*.2916/1e6,combinational_area=None,existing_SRAM_phase_replay='Existing priced components retained without duplication credit'),
      schedule=dict(ingress_destination_II=3,completion_destination_II=3,clock_GHz=dict(stream=1.2,chain=.9),score_prefill_beats=dict(T640=320,T128=64),PV_prefill_beats=256,score_replay_II=1,PV_replay_II=1,command_to_first_replay_beat_edges=5,phase_write_visibility_barriers=2,completion='Only after phase IDLE, both actual bank replay bursts done, ingress FIFO empty, and completion FIFO ready. E and BF16 drain phase events must mean destination-visible accepted payload, not source send.',denominator='Actual tagged den_v gates PV replay; E drain must complete before PV fill.',service_bound='Continuous ready and healthy state only. Ingress FIFO64 finite seats; input stalls while phase cannot accept. No unconditional bounded external attention wait.'),
      epoch=dict(width=32,within_reset='Strictly increasing begin epoch; no wrap accepted. Every data and external event must match active epoch/tag. Mismatch faults and suppresses forwarding/completion.',cold_reset='One raw cold-abort net to both reset entries. Both local queues, bank ownership and phase abort; externally outstanding owners must also abort. No unilateral reset.',external_monotonicity='Cold reset loses last-epoch register. External owner must supply fresh epoch and quarantine old producer replies; global nonreuse not proved by this component.'),
      config=dict(snapshot_bits=2602,SECDED_words64=41,encoded_storage_bits=2952,raw_command_transport_beats1024=3,implemented=False,area_or_latency_credit=0,requirement='Full config must be protected and bound before production start; minimum component uses short/tag only and cannot launch numerical engine'),
      nine_by_four=dict(width_um=width,height_um=height,area_mm2=width*height/1e6,macro_area_mm2=36*w*h/1e6,gaps_um=[30,32],macros_per_row=9,rows=4,protected_bits_per_row=9*256,complete_SECDED_words_per_row=32,row_boundary_split_codewords=0,within_row_bank_split_codewords=32,read_pins_face='left for R0; codec/station access remains required',pin_census_reference='bank_pin_census.json',assigned_slot=False,PG_clock_via_capacity=None,mapped_codec_area=None),
      missing=['Actual E/BF16 payload transport linked to visible endpoint receipts','Config snapshot and numerical core connection','Production epoch-owner drain/abort binding','Mapped area, nine-by-four placement, pin/PG/codec routing and SS/FF budgets'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();s=json.dumps(build(),indent=2)+'\n'
 if a.output:a.output.write_text(s)
 else:print(s,end='')
