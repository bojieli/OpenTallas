#!/usr/bin/env python3
"""Source-bound controller extension sizing; no controller RTL admission."""
import argparse
import hashlib
import json
from fractions import Fraction
from math import ceil
from pathlib import Path
import subprocess

REV='4535be1001d69bc43669e0fdf0401896be4034a6'
SOURCE='rtl/hdc/kv/ot_hdc_hbm_model.sv'
EPOCH_REV='e5d9ad00a'
EPOCH_SOURCE='tools/deepseek_hbm_complete_packed_index_provider.py'

def model(repo,qd=64,rqd=32,write_depth=4):
    if min(qd,rqd,write_depth)<1 or qd<32:
        raise ValueError('finite queues must admit LENMAX32')
    raw=subprocess.check_output(['git','show',REV+':'+SOURCE],cwd=repo)
    for needle in (b'parameter integer TAGW     = 16',b'parameter integer LENW     = 5',
                   b'parameter integer BEATW    = 4',b'parameter integer QD       = 64',
                   b'parameter integer RQD      = 32',b'parameter integer CLK_PS   = 1000',b'last_col[p] + BURST_PS',b'for (p = 0; p < NPC; p = p + 1)',b'mem[q_addr[p][slot] % MEM_WORDS] = q_data[p][slot];'):
        if needle not in raw:raise ValueError('pinned controller source audit changed')
    epoch_commit=subprocess.check_output(['git','rev-parse',EPOCH_REV],cwd=repo,text=True).strip()
    epoch_raw=subprocess.check_output(['git','show',epoch_commit+':'+EPOCH_SOURCE],cwd=repo)
    for needle in (b"struct.pack('<4sBBHQ'",b"struct.unpack('<4sBBHQ'",b'0<=epoch<2**64'):
        if needle not in epoch_raw:raise ValueError('immutable producer epoch format changed')
    instances=2*4;pcs=32
    # Conservative explicit epoch storage at every queue entry. A global
    # session epoch alternative needs a separately proved drain and is not
    # credited here. WR pending payload lives independently until visibility.
    transport_epoch_bits=instances*pcs*(qd+rqd)*32
    producer_epoch_bits=instances*pcs*(qd+rqd)*64
    epoch_bits=transport_epoch_bits+producer_epoch_bits
    write_fields={'tag':16,'transport_epoch':32,'producer_epoch':64,'sector':34,'data':256,'simulation_due_ps':64,'valid':1}
    write_bits=instances*write_depth*sum(write_fields.values())
    write_pointer_bits=instances*(2*(write_depth-1).bit_length()+(write_depth+1).bit_length())
    total=epoch_bits+write_bits+write_pointer_bits
    visibility=6250+1024
    column_bounds={name:dict(spacing_ps=str(spacing),minimum_pending_before_visibility=ceil(Fraction(visibility)/spacing),minimum_pending_through_RSP=ceil(Fraction(visibility+10000)/spacing))
        for name,spacing in [('single_shared_1024ps',Fraction(1024)),('hypothetical_shared_fast',Fraction(2500,3))]}
    per_pc=ceil(Fraction(visibility,1024))
    quantized={}
    for name,clock in [('source_1000ps',Fraction(1000)),('target_fast_2500over3ps',Fraction(2500,3))]:
        interval=ceil(Fraction(1024)/clock)*clock
        observed_visibility=ceil(Fraction(visibility)/clock)*clock
        floor=ceil(observed_visibility/interval)
        quantized[name]=dict(clock_ps=str(clock),minimum_per_PC_issue_interval_ps=str(interval),observed_visibility_latency_ps=str(observed_visibility),pending_per_PC=floor,pending_all32_PC_per_stack=32*floor,first_simultaneous_wave_entries_per_stack=32,scope='best legal rotating-bankgroup open-row writes, no refresh/turnaround; reclaim-before-new-column at same edge required')
    service=dict(quantized_per_PC_calendar=quantized,CWL_ps=6250,burst_ps=1024,column_to_backing_visibility_ps=visibility,
        request_path_ps=10000,response_path_ps=10000,
        ideal_row_hit_request_to_visible_ps=10000+visibility,
        ideal_row_hit_request_to_completion_ps=10000+visibility+10000,
        source_column_constraint='last_col[p] and last_col_bg[p][bg] are per-PC; no stack-global last_col/shared bus reservation exists',
        source_aggregate_column_bound_per_stack_writes_per_second=pcs*1e12/1024,
        source_per_PC_pending_floor=per_pc,source_unquantized_envelope_pending_per_stack=pcs*per_pc,
        ingress_bound='one WR request per stack fastcycle limits sustained offered WR rate, but queued-PC backlog may issue simultaneous columns; ingress is not column serialization',
        hypothetical_shared_column_bounds=column_bounds,
        depth_selected=False,candidate_depth=write_depth,first_wave_fits=write_depth>=32,
        target_fast_visibility_window_fits=write_depth>=quantized['target_fast_2500over3ps']['pending_all32_PC_per_stack'],
        depth_candidate_visible_only_ceiling_writes_per_second=write_depth*1e12/visibility,
        depth_candidate_visible_only_ceiling_bytes_per_second=32*write_depth*1e12/visibility,
        depth_candidate_through_RSP_ceiling_writes_per_second=write_depth*1e12/(visibility+10000),
        admission='Depth4 only exact with precolumn capacity reservation and stalls. No unhurt bandwidth credit. Ready stalls can extend residence without bound; no finite depth removes arbitrary backpressure.',
        pending_release='Backing-visible storage may release only after transferring to separately finite held completion storage; otherwise include RSP and consumer ready residence.')
    return dict(schema='Qwen_controller_source_extension_prerequisites_r3',
        source_pin=dict(commit=REV,path=SOURCE,sha256=hashlib.sha256(raw).hexdigest()),
        producer_epoch_format_source_pin=dict(commit=epoch_commit,path=EPOCH_SOURCE,sha256=hashlib.sha256(epoch_raw).hexdigest()),
        source_defaults=dict(NPC=2,AW=24,TAGW=16,LENW=5,BEATW=4,QD=64,RQD=32),
        proposed_geometry=dict(dies=2,stacks_per_die=4,NPC=pcs,AW=34,TAGW=16,LENW=6,BEATW=5,QD=qd,RQD=rqd,write_pending_depth_per_stack=write_depth),
        controller_extension_state=dict(queue_epoch_bits=epoch_bits,queue_transport_epoch_bits=transport_epoch_bits,queue_producer_epoch_bits=producer_epoch_bits,write_pending_fields=write_fields,write_pending_bits=write_bits,write_pointer_bits=write_pointer_bits,total_bits=total,storage_only_area_mm2=total*.2916/.5/1e6),
        source_epoch_contract=dict(producer_epoch_bits=64,transport_epoch_bits=32,highhalf_reconstruction_proved=False,source_epoch_narrowing_allowed=False,actual_binding=None),
        additional_common36_held_epoch_bits=dict(ACK_capture_and_CDC=2*2*4*64,reverse_credit=2*4*64,active_mapping=2*4*64,client_request_holds=2*36*64,total=6656,scope='Producer64 alongside existing transport32/logical32; conservative additional, no free field overlap. Outside controller storage totals; drain mailbox mapping remains unbound.'),
        pending_write_service=service,
        timestamp_scope=dict(simulation_due_ps_bits=64,hardware_timer_bits=None,wrap_or_counter_credit=False,storage_area_is_simulation_field_proxy_not_hardware_fit=True,requirement='derive bounded hardware age/countdown, resolution and maximum residence including refresh/ready; prove wrap comparison or failstop before choosing width'),
        missing_composed_costs=['queue widening macros and ports','32-PC held return arbitration','write pending service ordering and refresh/turnaround','WR-visible capture and epoch mux/comparison','drain tree across all controllers/CDC/consumers','NoC routing tracks and full floorplan slot fit','1737 issue/RF/shared ports and token latency'],
        required_source_semantics=['capture full producer epoch64 alongside transport epoch32 at request acceptance; move both with every reorder swap; no highhalf truncation','retain epoch through read return queue; never receiver-stamp','schedule real backing write visibility after column+CWL+burst, hold full identity/payload until ready','reserve pending-write capacity before issuing WR column; stall rather than drop completion','read-after-write forwarding or wait until backing visibility, preserving address order','full AW34 backing address with no modulo alias','drain observes queued reads/writes, delayed backing writes, all held returns, CDC, RMW and consumer leases','only both-die four-phase return-zero allows tag reuse'],
        baseline_unchanged=True,queue_depth_authority='explicit proposal; source defaults are not whole-system admission',
        area_scope='additional storage only; excludes existing queues and common36 r2 state; no free overlap. Not total element area.',
        actual_provider_credit=False,hardware_build_ready=False,total_token_cycles=None,headline_rate=None)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(model(a.repo),indent=2,sort_keys=True)+'\n')
