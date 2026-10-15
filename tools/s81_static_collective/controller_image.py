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
 ('hc_expect_seq',16),('hc_expect_last',1),('hc_emit_slot',1),('hc_emit_tag',32),
 ('commit_gather',1),('raw_capture_payload_slot',1),('raw_capture_meta_slot',1),
 ('raw_rx_write_slot',1),('raw_rx_payload_row',14),('raw_rx_meta_row',14),('raw_rx_tag',8),
 ('hc_assemble_slot',1)]
CONTROL_BITS=sum(w for _,w in FIELDS)
# control, expected command pulse84, done pulse9, final cycle, validity marker.
ROM_BITS=CONTROL_BITS+85+9+2
ABI='opentallas.s81.collective-fixed-edge-rom.v2'
LATENCIES=dict(control_rom_synchronous_read_edges=1,control_rom_idle_prefetch_edges=1,controller_command_register_edges=1,controller_output_register_edges=1,vm_request_to_issue_edges=14,issue_to_gather_edges=11,
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
    # The owner supplies actual source allocation, clock phase, VM service and
    # boundary prices; the control compiler never infers a physical allocation.
    for name in ('native_source_binding','vm_reservations','physical_phase_binding','timing_price_binding'):
        if not request.get(name): raise ValueError('missing '+name)
    cycles=request['cycles']
    if len(cycles)>4096: raise ValueError('actual control ROM has one4096cycle page; larger calendars require real page implementation')
    if not cycles or not cycles[0]['cmd_valid']: raise ValueError('first edge must name start command')
    controls=[]
    for edge,c in enumerate(cycles):
        if c['edge']!=edge: raise ValueError('calendar must be contiguous')
        controls.append(pack_controls(c['controls']))
    read_edges={edge for edge,c in enumerate(cycles) if c['controls']['read_slot']}
    reservations={}
    for reservation in request['read_reservations']:
        edge=reservation['edge']
        if type(edge)is not int or edge not in read_edges or edge in reservations:
            raise ValueError('duplicate/extra read reservation')
        if reservation['row']!=cycles[edge]['controls']['read_row']:
            raise ValueError('read reservation row differs from actual request')
        if reservation['consumer'] not in ('tp4','raw_payload','raw_meta'):
            raise ValueError('unowned read consumer')
        reservations[edge]=reservation
    if set(reservations)!=read_edges: raise ValueError('read reservation profile must cover every actual request')
    consumer_fields={'tp4':'issue_slot','raw_payload':'raw_capture_payload_slot','raw_meta':'raw_capture_meta_slot'}
    for edge,c in enumerate(cycles):
        actual=[kind for kind,field in consumer_fields.items() if c['controls'][field]]
        if actual:
            if len(actual)!=1 or edge<14 or edge-14 not in reservations:
                raise ValueError('VM return must have exactly one owner14edges after request')
            if actual[0]!=reservations[edge-14]['consumer']:
                raise ValueError('VM return owner differs from read reservation')
        if edge in reservations:
            target=edge+14
            if target>=len(cycles) or not cycles[target]['controls'][consumer_fields[reservations[edge]['consumer']]]:
                raise ValueError('unconsumed VM source read')
    pending={};words=[];source_queue=[];issues={};commits={};hc_inputs={};hc_writes={}
    assembly_owner=None;assembly_bits=0;assembly_last_write=None
    raw_payload_loaded=False;raw_meta_loaded=False
    for edge,c in enumerate(cycles):
        control=controls[edge];v=c['cmd_valid'];d=c['done_valid'];ctrl=c['controls']
        if type(v)is not int or v not in (0,1) or type(d)is not int or d not in (0,1): raise ValueError('pulse')
        if v:
            tag,count,mode=command(c['cmd84'])
            consumer=c['consumer']
            if consumer not in ('gather_vm','reduce_vm','reduce_vm_hc') or bool(mode)!=(consumer=='gather_vm'):
                raise ValueError('command mode does not match explicit consumer')
            transport_tag=c['transport_tag']
            if type(transport_tag)is not int or not 0<=transport_tag<1<<32:
                raise ValueError('transport tag32')
            if tag in pending or any(p['tag']==transport_tag for p in pending.values()):
                raise ValueError('duplicate pending command/transport tag')
            pending[tag]=dict(start=edge,tag=transport_tag,count=count,mode=mode,consumer=consumer,
                issued=0,committed=0,reduced_written=0,last_commit=None,last_reduce_write=None,last_emit=None,emits=0)
            source_queue.append(pending[tag])
        elif c['cmd84']!=0: raise ValueError('nonzero idle command')
        if ctrl['issue_slot']:
            if not source_queue: raise ValueError('source slot without descriptor')
            job=source_queue[0]
            if ctrl['tag']!=job['tag'] or ctrl['seq']!=job['issued']: raise ValueError('source tag/sequence')
            if ctrl['seq']>=1024 or ctrl['rankmask']!=15: raise ValueError('TP4 source sequence/rankmask')
            issues[edge]=job;job['issued']+=1
            if bool(ctrl['last'])!=(job['issued']==job['count']): raise ValueError('message count/last mismatch')
            if ctrl['last']: source_queue.pop(0)
        if ctrl['commit_slot']:
            owner=issues.get(edge-11)
            if owner is None: raise ValueError('gather without source11edgesearlier')
            if ctrl['commit_tag']!=owner['tag'] or ctrl['commit_seq']!=owner['committed'] or ctrl['commit_rankmask']!=15:
                raise ValueError('gather identity/sequence')
            if ctrl['commit_gather']!=owner['mode']: raise ValueError('commit gather flag differs from command mode')
            for rank in range(4):
                if ((ctrl['commit_rows']>>(15*rank))&32767)>=16384: raise ValueError('VM landing row14')
            owner['committed']+=1
            if bool(ctrl['commit_last'])!=(owner['committed']==owner['count']): raise ValueError('gather last/count')
            commits[edge]=owner
            if ctrl['commit_last']: owner['last_commit']=edge
        elif ctrl['commit_gather']: raise ValueError('gather mode flag outside commit slot')
        # Reduce samples gather registers one edge later, then the reduced VM
        # word is sampled18edges later. Optional HC assembly is a separate use.
        if ctrl['hc_reduce_slot']:
            owner=commits.get(edge-1)
            if owner is None or owner['mode']!=0: raise ValueError('HC source not a preceding reduce gather')
            hc_inputs[edge]=(cycles[edge-1]['controls']['commit_seq'],cycles[edge-1]['controls']['commit_last'],owner)
        if ctrl['hc_write_slot']:
            expected=hc_inputs.get(edge-18)
            if expected is None: raise ValueError('HC write has no reducer source')
            seq,last,owner=expected
            if ctrl['hc_expect_seq']!=seq or ctrl['hc_expect_last']!=last:
                raise ValueError('HC write latency/sequence/last')
            owner['reduced_written']+=1;hc_writes[edge]=(seq,last,owner)
            if last: owner['last_reduce_write']=edge
        if ctrl['hc_assemble_slot']:
            if not ctrl['hc_write_slot']: raise ValueError('HC assembly lacks actual reduced-word write')
            owner=hc_writes[edge][2]
            if owner['consumer']!='reduce_vm_hc': raise ValueError('HC assembly is not a declared command consumer')
            if assembly_owner is not None and assembly_owner is not owner: raise ValueError('interleaved HC assembly owners')
            bit=1<<ctrl['hc_word_index']
            if assembly_bits&bit: raise ValueError('duplicate HC assembly word index')
            assembly_owner=owner;assembly_bits|=bit;assembly_last_write=edge
        if ctrl['hc_emit_slot']:
            if assembly_owner is None or assembly_bits!=65535 or assembly_last_write>=edge:
                raise ValueError('HC row emitted before16distinct actual assembly writes')
            if ctrl['hc_emit_tag']!=assembly_owner['tag']: raise ValueError('HC emit identity')
            assembly_owner['last_emit']=edge;assembly_owner['emits']+=1
            assembly_owner=None;assembly_bits=0;assembly_last_write=None
        # Channel kind0 sends the actual pair of captured VM rows. The metadata
        # row carries41meaningful bits including an independent outer-last bit.
        raw_sends=0;raw_receives=0
        for direction in ('tx','rx'):
            kinds=[]
            for channel in range(5):
                if (ctrl['channel_'+direction+'_slot']>>channel)&1:
                    kind=(ctrl['channel_'+direction+'_kind']>>(2*channel))&3
                    if kind==3 or kind in kinds: raise ValueError('illegal/duplicate channel source kind')
                    kinds.append(kind)
            if direction=='tx': raw_sends=kinds.count(0)
            else: raw_receives=kinds.count(0)
        previous_raw_rx=0
        if edge:
            prior=cycles[edge-1]['controls']
            previous_raw_rx=sum(1 for channel in range(5) if (prior['channel_rx_slot']>>channel)&1 and ((prior['channel_rx_kind']>>(2*channel))&3)==0)
        if ctrl['raw_rx_write_slot']!=previous_raw_rx: raise ValueError('raw RX writer must capture prior channel raw output')
        if raw_receives and edge==len(cycles)-1: raise ValueError('raw RX output lacks nextedge writer')
        if raw_sends:
            if not raw_payload_loaded or not raw_meta_loaded: raise ValueError('raw send lacks two actual VM row captures')
            if ctrl['raw_capture_payload_slot'] or ctrl['raw_capture_meta_slot']:
                raise ValueError('raw capture/send register ownership collision')
            raw_payload_loaded=False;raw_meta_loaded=False
        if ctrl['raw_capture_payload_slot']:
            if raw_payload_loaded: raise ValueError('raw payload recaptured before prior send')
            raw_payload_loaded=True
        if ctrl['raw_capture_meta_slot']:
            if raw_meta_loaded: raise ValueError('raw metadata recaptured before prior send')
            raw_meta_loaded=True
        if ctrl['raw_rx_write_slot'] and ctrl['raw_rx_payload_row']==ctrl['raw_rx_meta_row']:
            raise ValueError('raw receive payload/metadata rows alias')
        if d:
            tag=c['done_tag']
            if tag not in pending or pending[tag]['start']>=edge: raise ValueError('unowned/early completion')
            owner=pending[tag]
            boundary={'gather_vm':'last_commit','reduce_vm':'last_reduce_write','reduce_vm_hc':'last_emit'}[owner['consumer']]
            finished=owner[boundary]
            if finished is None or edge<=finished or owner['committed']!=owner['count']:
                raise ValueError('completion precedes actual final scheduled output')
            if not owner['mode'] and (owner['reduced_written']!=owner['count'] or owner['last_reduce_write']>=edge):
                raise ValueError('completion precedes final reduced VM word')
            if assembly_owner is owner: raise ValueError('completion leaves partial HC assembly')
            del pending[tag]
        elif c['done_tag']!=0: raise ValueError('nonzero idle completion tag')
        if type(c['done_tag'])is not int or not 0<=c['done_tag']<256: raise ValueError('done tag')
        cmd=(v<<84)|c['cmd84'];done=(d<<8)|c['done_tag']
        words.append(control|(cmd<<CONTROL_BITS)|(done<<(CONTROL_BITS+85))|
                     (int(edge==len(cycles)-1)<<(CONTROL_BITS+94))|(1<<(ROM_BITS-1)))
    if source_queue or pending: raise ValueError('unfinished message/completion')
    if assembly_owner is not None or raw_payload_loaded or raw_meta_loaded: raise ValueError('unfinished finite operand capture')
    for edge,owner in commits.items():
        if owner['mode']==0 and edge+1 not in hc_inputs: raise ValueError('reduce gather lacks HC reservation')
    for edge in hc_inputs:
        if edge+18 not in hc_writes: raise ValueError('HC reducer result lacks reduced VM write reservation')
    return words

def pack_macro_banks(words,path):
    """Map three266-bit word slices into actual MUX8 via-mask cells.

    Physical model cell for logical wordaddress a/bit b is row=a//8,
    column=8*b+a%8. All4096words are present; unused rows have marker0.
    No DUT logical array or data loader replaces these physical macro masks.
    """
    if not 1<=len(words)<=4096: raise ValueError('one actual ROMpage only')
    files=[]
    for bank in range(3):
        rows=[0]*512
        for addr,word in enumerate(words):
            if type(word)is not int or not 0<=word<1<<ROM_BITS: raise ValueError('ROM word width')
            value=(word>>(266*bank))&((1<<266)-1)
            while value:
                bit=(value&-value).bit_length()-1
                rows[addr//8]|=1<<(8*bit+addr%8)
                value&=value-1
        filename=Path(str(path)+f'.b{bank}.viamap.hex')
        filename.write_text(''.join(f'{row:0532x}\n'for row in rows))
        files.append(dict(path=str(filename),sha256=hashlib.sha256(filename.read_bytes()).hexdigest(),bank=bank))
    return files


def emit(request,root,path):
    words=compile_image(request,root)
    path.write_text(''.join(f'{w:0{(ROM_BITS+3)//4}x}\n' for w in words))
    banks=pack_macro_banks(words,path)
    return dict(abi=ABI,control_bits=CONTROL_BITS,rom_bits=ROM_BITS,cycles=len(words),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),latencies=LATENCIES,
                macro='ot_rom_4096x266_m8',macro_count=3,macro_depth=4096,macro_bank_files=banks,
                integration_ready=False,qualification='actual ROM-backed controller component; native production source/phase/price acceptance is separate')
