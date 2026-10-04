#!/usr/bin/env python3
"""Read-only replay of captured native leaf bytes and source port preparation.

No checkpoint reconstruction, oracle injection, or numerical prefix. Planned
RF handshake events are labelled separately from observed source payloads.
"""
import argparse
import json
from pathlib import Path
import struct
import h4_c0_pc40_workspace_lease_r1 as W

def verify_bits(payloads):
    words={k:struct.unpack('<128I',v) for k,v in payloads.items()}
    W.require(all((v>>23)&255!=255 for v in words['gate']),'finite released gate for bounded replay')
    W.require(words['negative']==tuple(v^0x80000000 for v in words['gate']),'exact source negation chain bits')
    W.require(words['constant']==(0xc2ae0000,)*128,'exact source F32 minus87 broadcast')
    expected=tuple(v if struct.unpack('<f',struct.pack('<I',v))[0]>=-87 else 0xc2ae0000 for v in words['negative'])
    W.require(words['FMAX']==expected,'source actual FMAX output bits')
    return dict(words=128,negative_bit_mismatches=0,constant_bit_mismatches=0,FMAX_bit_mismatches=0)

def replay(directory):
    directory=Path(directory);terminal=json.loads((directory/'terminal.json').read_text())
    W.require(terminal['verdict']=='PASS' and terminal['oracle_only_after_capture'] is True
              and terminal['oracle_input_injection'] is False and terminal['independent_checkpoint_gate_compare'] is True,
              'actual released-checkpoint comparison PASS')
    W.require(set(terminal['comparisons'])=={'gate','negative','constant','FMAX'} and
              all(v['words']==128 and v['bit_mismatches']==0 and v['actual_nonfinite']==0
                  for v in terminal['comparisons'].values()),'all actual checkpoint comparison counts')
    packet,frames,payloads=W.bind_capture(directory,generation=1,owner_tag=1,response_stall_bound=1)
    W.require(all(terminal['comparisons'][name]['expected_sha256']==W.sha(raw)
                  for name,raw in payloads.items()),'actual and expected payload identity')
    bitcheck=verify_bits(payloads)
    byslot={frames[k]['RFslot9']:frames[k] for k in ('negative','constant','FMAX')}
    lease=W.WorkspaceLease(packet,enabled=True,frame_bindings=byslot)
    # These planned port transactions exercise the data/lease seam only. They
    # are NOT labelled as actual installed RF ready/response/commonACK events.
    for name in ('negative','constant'):
        f=frames[name];lease.write_offer(f['RFslot9'],payloads[name],f['lease'])
        lease.write_accept(wr_ready=True,ack_valid_before=False)
        lease.common_ACK(lease.owner,ack_valid=True,ack_ready=True)
    lease.read_offer((17,18));lease.read_accept(rd_ready=True)
    lease.response_capture(lease.owner,rsp_valid=True,rsp_ready=True,payloads=[payloads['negative'],payloads['constant']])
    lease.native_complete(lease.owner,output_sha256=frames['FMAX']['sha256'])
    lease.write_offer(19,payloads['FMAX'],frames['FMAX']['lease'])
    lease.write_accept(wr_ready=True,ack_valid_before=False);lease.common_ACK(lease.owner,ack_valid=True,ack_ready=True)
    # FMAX result is retained for the actual next source FMIN. No consumer or
    # reverse is invented to free the last workspace slot.
    return dict(schema='C0_PC40_CAPTURE_TO_SOURCE_RF_PREPARATION_R1',verdict='PASS_SOURCE_PAYLOAD_AND_PLANNED_LEASE',
                source_metadata=packet,source_frames=frames,bitcheck=bitcheck,
                source_native_payload_observed=True,independent_checkpoint_compare=True,
                planned_port_events=lease.log,actual_installed_port_events_observed=False,
                workspace_owner_retained=not lease.released,pending_RF_transactions=0,
                output19_visible_in_software_preparation_model=True,
                missing_retirement='source exp.step1 FMIN consumer and validated reverse; no inferred release',
                source_gate_RF38_released=False,installed_call_admitted=False,hardware_admitted=False,
                finite_model=W.model())

def main():
    p=argparse.ArgumentParser();p.add_argument('--capture',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.write_bytes(W.canonical(replay(a.capture)))

if __name__=='__main__':main()
