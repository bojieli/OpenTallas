"""Source-pinned fixed collective controller ROM ABI; no inferred job prices.

This emits the control image only. Production eligibility requires a compiler
owner's complete actual calendar with physical timing and VM reservations.
Commands use the existing cmd84.v1 engine3 ABI, including its completion tag.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

# Least significant field first, mirrored by generated RTL slicing.
FIELDS = [('read_slot',1),('read_row',14),('issue_slot',1),('tag',32),
 ('seq',16),('last',1),('rankmask',4),('commit_slot',1),('commit_tag',32),
 ('commit_seq',16),('commit_last',1),('commit_rankmask',4),('commit_rows',60),
 ('tx_beat_slot',1),('tx_phase',2),('tx_frame_slot',1),
 ('rx_beat_slot',1),('rx_phase',2),('rx_frame_slot',1),
 ('channel_tx_slot',5),('channel_tx_kind',10),('channel_tx_seq',50),('channel_tx_last',5),
 ('channel_rx_slot',5),('channel_rx_kind',10),('channel_rx_seq',50),('channel_rx_last',5),
 ('channel_tx_beat_slot',5),('channel_tx_frame_slot',5),('channel_tx_phase',10),
 ('channel_rx_beat_slot',5),('channel_rx_frame_slot',5),('channel_rx_phase',10),
 ('hc_reduce_slot',1),('hc_write_slot',1),('hc_word_index',4),
 ('hc_expect_seq',16),('hc_expect_last',1),('hc_emit_slot',1),('hc_emit_tag',32)]
CONTROL_BITS=sum(w for _,w in FIELDS)
# control, expected command pulse84, done pulse9, final cycle, validity marker.
ROM_BITS=CONTROL_BITS+85+9+2
ABI='opentallas.s81.collective-fixed-edge-rom.v1'
LATENCIES=dict(controller_command_register_edges=1,controller_output_register_edges=1,vm_request_to_issue_edges=14,issue_to_gather_edges=11,
               gather_to_vm_source_edges=1,hc_reduce_to_write_edges=18,
               hc_final_write_to_earliest_emit_edges=1,
               done_rom_to_c_done_edges=1)

def pack_controls(values):
    if set(values)!={n for n,_ in FIELDS}: raise ValueError('every cycle must explicitly name every control field')
    result=0; offset=0
    for name,width in FIELDS:
        value=values[name]
        if type(value)is not int or not 0<=value<1<<width: raise ValueError(name+' out of range')
        result|=value<<offset;offset+=width
    return result

def command(word):
    if type(word)is not int or not 0<=word<1<<84: raise ValueError('cmd84')
    arg=(word>>7)&0xffffff
    if arg>>17 or not 1 <= (arg&0xffff) <= 1024: raise ValueError('invalid engine3 coll_message count/reserved bits')
    return ((word>>83)<<7)|(word&127),arg&65535,(arg>>16)&1

def compile_image(request,root):
    if request['abi']!=ABI or request['latencies']!=LATENCIES: raise ValueError('unbound physical latency profile')
    if request['command_abi']!='opentallas.s81.cmd84.v1': raise ValueError('command ABI')
    evidence=request['evidence']
    if not evidence: raise ValueError('missing source evidence')
    for item in evidence:
        p=(root/item['path']).resolve()
        if not p.is_relative_to(root.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('stale/outside source evidence')
    # An explicit approved owner profile supplies exact source allocation,
    # clock phase, service reservations and boundary prices. Never infer them.
    for name in ('native_source_binding','vm_reservations','physical_phase_binding','timing_price_binding'):
        if not request.get(name): raise ValueError('missing '+name)
    cycles=request['cycles']
    if not cycles or not cycles[0]['cmd_valid']: raise ValueError('first edge must name start command')
    pending={};words=[];source_queue=[];issues={};commits={};hc_inputs={};hc_writes={}
    for edge,c in enumerate(cycles):
        if c['edge']!=edge: raise ValueError('calendar must be contiguous')
        control=pack_controls(c['controls']);v=c['cmd_valid'];d=c['done_valid']
        if type(v)is not int or v not in (0,1) or type(d)is not int or d not in (0,1): raise ValueError('pulse')
        if v:
            tag,count,mode=command(c['cmd84'])
            if tag in pending: raise ValueError('duplicate pending command tag')
            pending[tag]=dict(start=edge,tag=c['transport_tag'],count=count,mode=mode,issued=0,committed=0,last_commit=None,last_emit=None);source_queue.append(pending[tag])
        elif c['cmd84']!=0: raise ValueError('nonzero idle command')
        ctrl=c['controls']
        if ctrl['issue_slot']:
            if not source_queue: raise ValueError('source slot without descriptor')
            job=source_queue[0]
            if ctrl['tag']!=job['tag'] or ctrl['seq']!=job['issued']: raise ValueError('source tag/sequence')
            if ctrl['seq']>=1024 or ctrl['rankmask']!=15: raise ValueError('TP4 source sequence/rankmask')
            if edge<14 or not cycles[edge-14]['controls']['read_slot']: raise ValueError('VM read must precede issue by14edges')
            issues[edge]=job
            job['issued']+=1
            if bool(ctrl['last'])!=(job['issued']==job['count']): raise ValueError('message count/last mismatch')
            if ctrl['last']: source_queue.pop(0)
        if ctrl['read_slot'] and (edge+14>=len(cycles) or not cycles[edge+14]['controls']['issue_slot']):
            raise ValueError('unconsumed VM source read')
        if ctrl['commit_slot']:
            owner=issues.get(edge-11)
            if owner is None: raise ValueError('gather without source11edgesearlier')
            if ctrl['commit_tag']!=owner['tag'] or ctrl['commit_seq']!=owner['committed'] or ctrl['commit_rankmask']!=15:
                raise ValueError('gather identity/sequence')
            owner['committed']+=1
            if bool(ctrl['commit_last'])!=(owner['committed']==owner['count']): raise ValueError('gather last/count')
            commits[edge]=owner
            if ctrl['commit_last']: owner['last_commit']=edge
        # HC samples gathered outputs on the next edge. Its eighteen-stage
        # reduction is sampled by the assembler18edges later, never by valid.
        if ctrl['hc_reduce_slot']:
            owner=commits.get(edge-1)
            if owner is None or owner['mode']!=0: raise ValueError('HC source not a preceding reduce gather')
            hc_inputs[edge]=(cycles[edge-1]['controls']['commit_seq'],cycles[edge-1]['controls']['commit_last'])
        if ctrl['hc_write_slot']:
            expected=hc_inputs.get(edge-18)
            if expected is None: raise ValueError('HC write has no reducer source')
            seq,last=expected
            if ctrl['hc_expect_seq']!=seq or ctrl['hc_word_index']!=seq%16 or ctrl['hc_expect_last']!=last:
                raise ValueError('HC write latency/sequence/index')
            hc_writes[edge]=seq
        if ctrl['hc_emit_slot']:
            if edge-1 not in hc_writes or hc_writes[edge-1]%16!=15: raise ValueError('HC row emitted before final assembly write')
            matches=[p for p in pending.values() if p['mode']==0 and p['tag']==ctrl['hc_emit_tag']]
            if len(matches)!=1: raise ValueError('HC emit identity')
            matches[0]['last_emit']=edge
        if d:
            tag=c['done_tag']
            if tag not in pending or pending[tag]['start']>=edge: raise ValueError('unowned/early completion')
            owner=pending[tag]
            finished=owner['last_commit'] if owner['mode'] else owner['last_emit']
            if finished is None or edge<=finished or owner['committed']!=owner['count']:
                raise ValueError('completion precedes actual final scheduled output')
            del pending[tag]
        elif c['done_tag']!=0: raise ValueError('nonzero idle completion tag')
        if type(c['done_tag'])is not int or not 0<=c['done_tag']<256: raise ValueError('done tag')
        # Done records describe the ROM consumption edge; c_done is visible
        # one edge later. The owner price must include that pin register.
        cmd=(v<<84)|c['cmd84'];done=(d<<8)|c['done_tag']
        words.append(control|(cmd<<CONTROL_BITS)|(done<<(CONTROL_BITS+85))|
                     (int(edge==len(cycles)-1)<<(CONTROL_BITS+94))|(1<<(ROM_BITS-1)))
    if source_queue or pending: raise ValueError('unfinished message/completion')
    for edge,owner in commits.items():
        if owner['mode']==0 and edge+1 not in hc_inputs: raise ValueError('reduce gather lacks HC reservation')
    for edge in hc_inputs:
        if edge+18 not in hc_writes: raise ValueError('HC reducer result lacks assembly reservation')
    return words

def emit(request,root,path):
    words=compile_image(request,root)
    path.write_text(''.join(f'{w:0{(ROM_BITS+3)//4}x}\n' for w in words))
    return dict(abi=ABI,control_bits=CONTROL_BITS,rom_bits=ROM_BITS,cycles=len(words),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),latencies=LATENCIES,
                integration_ready=False,qualification='controller component only; native production source/phase/price acceptance is separate')
