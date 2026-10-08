#!/usr/bin/env python3
"""Widened protected CDC candidate priced before its minimum component gate."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
    src=['rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv','rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_reset_entry.sv','rtl/dsrom_sys/s81_ph/su/ot_s81ph_su_xing.sv','rtl/dsrom_sys/c8/ot_chip_v41x_die_owner_safe_c8.sv']
    width=1024+16+7+3;words=(width+63)//64;depth=64
    bankbits=(2*(1+5)+(words+5))*72;rails=12*7;per=depth*words*72+bankbits+6+rails+4
    return dict(schema='opentallas.softmax_cdc_candidate.v1',adopted=False,route_admitted=False,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in src},
      packet=dict(bits=width,fields=dict(payload=1024,row_tag=16,row_address=7,beat=3),kind='implicit disjoint row regions; tag/address checked by SRAM join',words64=words,encoded_bits=words*72),
      storage=dict(depth=depth,encoded_FF_bits=depth*words*72,protected_bank_bits=bankbits,bank_fault_rails=6,Gray_rails_and_sync_bits=rails,reset_release_bits=4,total_state_bits_per_fifo=per,replicas=2,total_two_FIFO_state_bits=2*per,FF_body_floor_mm2=2*per*.2916/1e6,combinational_mapping_area=None),
      compute=dict(MAC_per_cycle=0,encode_slices_per_fifo=words,head_decode_slices_per_fifo=words),
      ports=dict(write_encoded_bits_per_source_edge=words*72,read_encoded_bits_per_destination_capture=words*72,read_initiation_interval=3,logical_payload_bytes_per_accept=128),
      domains=dict(stream_GHz=1.2,chain_GHz=.9,ratio='4 stream edges : 3 chain edges',setup_uncertainty_ps=60,hold_uncertainty_ps=25,physical_clock_budget=None),
      schedule=dict(fault_free_no_stall_empty_latency='first following destination edge captures Gray sync0; second sync1; third head capture; fourth validate; fifth accepts output',
        empty_latency_bound_destination_periods=5,read_II_destination_edges=3,
        ingress_max_beats_per_ns=.4,egress_max_beats_per_ns=.3,
        credit='pop changes protected read pointer and Gray at the same destination edge; next two source edges synchronize return; next source edge can accept against released credit',
        pop_to_reusable_credit_bound_source_periods=3,
        full_queue_fault_free_service_bound_destination_edges=64*3,
        bound_conditions='continuous out_r, healthy protected state and coherent rails; arbitrary consumer stalls/fault repair do not have a finite success bound',
        T640_ingress_beats=579,T640_egress_beats=448,
        T640_isolated_CDC_service_ns=dict(ingress=579*3/1.2,egress=448*3/.9),
        serializer='E/output serializer II4 stream edges ->0.3G beats/s equal to egress CDC steady rate; row request/launch overhead makes serializer slower. Full component calendar must account for row gaps.',
        core_prefill='Store complete40 score vectors (320 beats) or8 (64 beats), and complete32PV vectors (256 beats), in reserved SRAM regions before no-ready core replay. FIFO64 depth alone cannot absorb40vector core burst.',
        E_dependency='capture40 E vectors to row bank, drain to attention, await actual P.V, then fill32 PV vectors; never wait forPV beforeEdrain'),
      reset=dict(actual_parent='S81 SU crossing has one clk/rst_n; c8 parent one raw rst_n synchronized to rn for all engines',candidate='one coordinated cold abort asserted to both local reset entries; local two-edge release; no unilateral runtime reset',
        abort='external producer/consumer row reservations and tag ownership must also abort; FIFO reset alone does not certify parent drain or quarantine late service replies',warm='close admissions, retire accepted writes/output, exchange empty and epoch receipts before reuse; integration unimplemented'),
      routing=dict(encoded_cross_domain_payload_bits=words*72,Gray_complement_bits=28,available_tracks=None,slot=None),
      missing=['Production epoch/empty/retirement wiring','Full1050bit3:4 minimum component gate','Actual input/output budgets, mapped cells and placed channels','Composed parent token calendar including serializer gaps'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();s=json.dumps(build(),indent=2)+'\n'
    if a.output:a.output.write_text(s)
    else:print(s,end='')
