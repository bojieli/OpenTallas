#!/usr/bin/env python3
"""Finite all-client tag/held-return/drain model. No actual hardware provider.

Reuse is gated by internally tracked callbacks and a source-shaped four-phase
mailbox, never a caller's 'drained' Boolean. Current controller RTL lacks the
epoch-bearing visible/drain ports required here; hardware admission stays false.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
from common_wrack_completion_calendar import FAST, SLOW, crossing
from qwen_hbm_complete_program import compile_program
from qwen_hbm_complete_service_provider import sector_descriptors

ROOT=Path(__file__).resolve().parents[1]
CONTROL_TAG=65535
SOURCE_PINS={
 'controller':('4535be1001d69bc43669e0fdf0401896be4034a6','rtl/hdc/kv/ot_hdc_hbm_model.sv'),
 'PC_service':('bb51403bff27fc648be92a8b183199f7f8f2ba5e','rtl/hdc/hbm/ot_hdc_qwen_pc_service.sv'),
 'mailbox':('9c1a1ca96fa367996ed94156a4fa58b2b85a1fc5','rtl/lib/ot_cdc_mailbox.sv'),
 'FIFO':('9c1c2aa9357ff2b569e661c1d591cc0a563364d5','rtl/lib/ot_async_fifo.sv'),
 'event_reference':('67c597f1a9a7aa6cfffa80af05745983200ecbf6','rtl/abi3/ot_a3_event_scoreboard.sv'),
 'program':('defc45332','tools/qwen_hbm_complete_program.py'),
 'stage_adapter':('156c3dd0e','tools/qwen_hbm_complete_service_provider.py'),
 'canonical_cost':('2a648d7e2','results/physical_abi3/asap7/gpu/w13_calendar_v2_and_row_placement_20261001/failed_history_and_canonical_basis.json'),
}

def pc_of(sector):
    return ((sector>>2)^(sector>>7)^(sector>>12))&31

class Common36:
    """Supplied-callback ledger; data/arithmetics and physical costs unqualified."""
    def __init__(self,graph=None):
        self.graph=compile_program() if graph is None else graph
        self.epoch=0;self.next_tag=[0,0];self.entries={};self.waiting={}
        self.rr=[0,0];self.client_outstanding=Counter()
        self.q_n=Counter();self.r_n=Counter();self.backend_pending=set()
        self.capture=[[],[]];self.CDC=[[],[]];self.return_CDC=[[],[]]
        self.RMW_locks={}
        self.port={};self.scoreboard_ports=set()
        self.position=None;self.issued={};self.visible={};self.retired={}
        self.completed_positions=[];self.phase='OPEN';self.control=None;self.nonce=0
        self.request_level=0;self.acknowledge_level=0;self.control_waiting=False
        self.control_phases={}
        self.descriptor_masks={};self.writer_completed={}
        self.stats=Counter();self.last_ps=Fraction(0)

    @staticmethod
    def time(value):
        value=Fraction(value)
        if value<0:raise ValueError('negative callback timestamp')
        return value

    def begin_program(self,position):
        if self.phase!='OPEN' or self.position is not None or position!=len(self.completed_positions):
            raise ValueError('program boundary/session phase')
        if not 0<=position<self.graph['context_capacity']:raise ValueError('context aperture')
        self.position=position;self.issued={};self.visible={};self.retired={}
        self.descriptor_masks={};self.writer_completed={}

    def instruction_issue(self,instruction,opcode,issue_ps):
        if self.position is None:raise ValueError('no encoded program active')
        op=self.graph['instructions'][instruction];now=self.time(issue_ps)
        if opcode!=op['opcode'] or instruction in self.issued:raise ValueError('encoded opcode/duplicate issue')
        if any(d not in self.retired or self.retired[d]>now for d in op['dependencies']):
            raise ValueError('encoded dependency/result retirement missing')
        self.issued[instruction]=now

    def instruction_result_retire(self,instruction,result_visible_ps,dut_retire_ps):
        result,retire=self.time(result_visible_ps),self.time(dut_retire_ps)
        if instruction not in self.issued or instruction in self.retired or result<self.issued[instruction] or retire<result:
            raise ValueError('actual encoded result visibility/DUT retirement order')
        if any(e['owner']['instruction']==instruction for e in self.entries.values()) or any(o['instruction']==instruction for o in self.waiting.values()):
            raise ValueError('instruction still owns finite service/consumer callbacks')
        if any(lock['owner'][4]==instruction for lock in self.RMW_locks.values()):
            raise ValueError('instruction still owns persistent RMW lock')
        op=self.graph['instructions'][instruction]
        if op['opcode']=='KV_WRITE':
            expected={(r['stack'],r['sector']) for r in sector_descriptors(self.graph,op,self.position)}
            if set(self.writer_completed.get(instruction,{}))!=expected:
                raise ValueError('addressed KV writer publication obligations incomplete')
            if result<max(self.writer_completed[instruction].values()):
                raise ValueError('writer result predates addressed completion callbacks')
        self.visible[instruction]=result;self.retired[instruction]=retire

    def finish_program(self):
        if self.position is None or len(self.retired)!=len(self.graph['instructions']):
            raise ValueError('full1737 encoded retirement boundary required')
        if self.waiting or self.entries or self.capture[0] or self.capture[1] or self.CDC[0] or self.CDC[1] or self.return_CDC[0] or self.return_CDC[1] or self.RMW_locks:
            raise ValueError('program boundary with live service state')
        self.last_ps=max(self.retired.values());self.completed_positions.append(self.position)
        self.stats['encoded_instructions_retired']+=len(self.retired);self.position=None

    def hold_request(self,owner):
        required={'die','stack','client','logical_tag','logical_epoch','instruction','position','sector','kind','length'}
        if set(owner)!=required:raise ValueError('complete all-client request identity required')
        if self.phase!='OPEN' or owner['position']!=self.position:raise ValueError('request blocked at drain/program boundary')
        for key,bits in [('logical_tag',64),('logical_epoch',32),('sector',34)]:
            if not isinstance(owner[key],int) or not 0<=owner[key]<1<<bits:raise ValueError('request field aperture')
        die,client,stack=owner['die'],owner['client'],owner['stack']
        if die not in (0,1) or not 0<=client<36 or not 0<=stack<4:raise ValueError('36client/die/stack aperture')
        op=self.graph['instructions'][owner['instruction']]
        if owner['instruction'] not in self.issued or owner['instruction'] in self.retired or die not in op['participants']:raise ValueError('request instruction/participant not issued')
        if owner['kind'] not in ('read','write') or not 1<=owner['length']<=32 or owner['kind']=='write' and owner['length']!=1:
            raise ValueError('LENW6/BEATW5/read32/write1 contract')
        if owner['sector']+owner['length']>1<<34:raise ValueError('fulladdress read extent would wrap')
        lock=self.RMW_locks.get((die,stack,owner['sector']))
        if lock is not None:
            if self.RMW_owner(owner)!=lock['owner']:
                raise ValueError('conflicting all-client request to locked RMW sector')
            if owner['kind']=='write' and lock['merge_visible'] is None:
                raise ValueError('full sector WR before XOR AND XOR merge result')
        if op['opcode']=='KV_WRITE' and owner['kind']=='write':
            descriptors=self.descriptor_masks.setdefault(op['id'],{})
            if not descriptors:
                descriptors.update({(r['stack'],r['sector']):r for r in sector_descriptors(self.graph,op,self.position)})
            descriptor=descriptors.get((stack,owner['sector']))
            if descriptor is None or die!=op['attributes']['die']:
                raise ValueError('addressed KV write descriptor required')
            if (stack,owner['sector']) in self.writer_completed.get(op['id'],set()):
                raise ValueError('duplicate completed KV sector write')
            if descriptor['partial'] and lock is None:
                raise ValueError('partial KV sector requires persistent RMW lock')
        key=die,client
        if key in self.waiting:
            if self.waiting[key]!=owner:raise ValueError('finite held client request must remain stable')
            return False
        self.waiting[key]=dict(owner)
        return True

    @staticmethod
    def RMW_owner(owner):
        return tuple(owner[k] for k in ('die','stack','client','logical_epoch','instruction','position','sector'))

    def acquire_RMW(self,owner,mask):
        op=self.graph['instructions'][owner['instruction']]
        if op['opcode']!='KV_WRITE' or op['id'] not in self.issued or op['id'] in self.retired or owner['position']!=self.position or owner['die']!=op['attributes']['die']:
            raise ValueError('actual encoded KV writer RMW required')
        if op['id'] not in self.descriptor_masks:
            self.descriptor_masks[op['id']]={(r['stack'],r['sector']):r for r in sector_descriptors(self.graph,op,owner['position'])}
        matching=self.descriptor_masks[op['id']].get((owner['stack'],owner['sector']))
        if matching is None or matching['mask']!=mask or not matching['partial']:
            raise ValueError('actual addressed partial mask required')
        key=owner['die'],owner['stack'],owner['sector']
        if key in self.RMW_locks or sum(k[0]==owner['die'] for k in self.RMW_locks)>=4:
            raise ValueError('finite RMW lock contexts unavailable')
        self.RMW_locks[key]=dict(owner=self.RMW_owner(owner),mask=mask,read_import_retired=None,merge_visible=None)

    def RMW_merge_result(self,owner,opcodes,issue_ps,result_visible_ps):
        lock=self.RMW_locks[owner['die'],owner['stack'],owner['sector']]
        issue,result=self.time(issue_ps),self.time(result_visible_ps)
        if self.RMW_owner(owner)!=lock['owner'] or opcodes!=['XOR','AND','XOR'] or lock['read_import_retired'] is None or lock['merge_visible'] is not None:
            raise ValueError('RMW owner/read-import/two-source opcodes required')
        if issue<lock['read_import_retired'] or result<issue+27*SLOW:
            raise ValueError('three serial9cycle merge instructions must finish')
        lock['merge_visible']=result;self.stats['RMW_merges']+=1

    def admit_next(self,die,accept_ps):
        if self.phase!='OPEN':return None
        if sum(d==die for d,_ in self.entries)>=4 or self.next_tag[die]>=CONTROL_TAG:return None
        candidates=[(self.rr[die]+offset)%36 for offset in range(36)]
        client=next((c for c in candidates if (die,c) in self.waiting),None)
        if client is None:return None
        owner=self.waiting[die,client];now=self.time(accept_ps);stack=owner['stack']
        lock=self.RMW_locks.get((die,stack,owner['sector']))
        if lock and owner['kind']=='write' and now<lock['merge_visible']+FAST:
            raise ValueError('merged RMW result not ready for write ingress')
        if now%FAST:raise ValueError('controller ingress fast edge')
        last,credit=self.port.get((die,stack),(Fraction(-1),0))
        cycle=now/FAST
        if cycle==last:raise ValueError('one shared read OR write request per stack cycle')
        if cycle<last:raise ValueError('controller command timeline reversed')
        credit=min(1024,credit+750*(cycle-last));size=32*owner['length']
        if credit<size:raise ValueError('finite750B combined ingress budget')
        tag=self.next_tag[die];self.next_tag[die]+=1
        self.port[die,stack]=(cycle,credit-size);del self.waiting[die,client]
        self.rr[die]=(client+1)%36;self.client_outstanding[die,client]+=1
        self.entries[die,tag]=dict(owner=owner,transport_epoch=self.epoch,accept=now,
            column={},generated={},captured=set(),delivered=set(),consumer_retired=None)
        for beat in range(owner['length']):self.q_n[die,stack,pc_of(owner['sector']+beat)]+=1
        self.stats['requests']+=1;self.stats['requests_'+owner['kind']]+=1
        return tag

    def entry(self,die,tag,transport_epoch):
        if not 0<=tag<CONTROL_TAG:raise ValueError('data tag16/control tag aperture')
        if transport_epoch!=self.epoch:raise ValueError('stale transport epoch')
        e=self.entries.get((die,tag))
        if e is None or e['transport_epoch']!=transport_epoch:raise ValueError('unknown/retired physical tag')
        return e

    def controller_column(self,die,tag,transport_epoch,beat,column_ps):
        e=self.entry(die,tag,transport_epoch);o=e['owner'];now=self.time(column_ps)
        if not 0<=beat<o['length'] or beat in e['column'] or now<e['accept']:raise ValueError('actual column beat/identity/time')
        key=die,o['stack'],pc_of(o['sector']+beat)
        self.q_n[key]-=1;e['column'][beat]=now
        if o['kind']=='read':self.r_n[key]+=1
        else:self.backend_pending.add((die,tag,beat))

    def controller_return(self,die,tag,transport_epoch,beat,visible_ps):
        e=self.entry(die,tag,transport_epoch);o=e['owner'];now=self.time(visible_ps)
        if beat not in e['column'] or beat in e['generated']:raise ValueError('unknown/duplicate controller return')
        if now<e['column'][beat]+(7274 if o['kind']=='write' else 0):raise ValueError('WR backing visibility is not acceptance/column')
        e['generated'][beat]=now
        # Epoch originates at controller callback capture, not relabelled at
        # receiver lookup. Current RTL lacks this port and cannot pass intake.
        return dict(die=die,tag=tag,transport_epoch=transport_epoch,beat=beat,
            stack=o['stack'],sector=o['sector']+beat,client=o['client'],
            logical_epoch=o['logical_epoch'],instruction=o['instruction'],position=o['position'],
            kind=o['kind'],visible_ps=str(now))

    def capture_ready(self,die):return len(self.capture[die])<4

    def capture_offer(self,packet):
        e=self.entry(packet['die'],packet['tag'],packet['transport_epoch']);o=e['owner'];beat=packet['beat']
        expected=dict(die=packet['die'],tag=packet['tag'],transport_epoch=e['transport_epoch'],beat=beat,
            stack=o['stack'],sector=o['sector']+beat,client=o['client'],logical_epoch=o['logical_epoch'],
            instruction=o['instruction'],position=o['position'],kind=o['kind'],visible_ps=str(e['generated'].get(beat)))
        if packet!=expected or beat not in e['generated'] or beat in e['captured']:
            raise ValueError('ACK capture identity/visibility/duplicate mutation')
        if not self.capture_ready(packet['die']):return False
        self.capture[packet['die']].append(dict(packet));e['captured'].add(beat)
        key=packet['die'],o['stack'],pc_of(o['sector']+beat)
        if o['kind']=='read':self.r_n[key]-=1
        else:self.backend_pending.remove((packet['die'],packet['tag'],beat))
        return True

    def capture_head(self,die):
        return dict(self.capture[die][0]) if self.capture[die] else None

    def ACK_FIFO_push(self,die,ready=True):
        if not ready or not self.capture[die] or len(self.CDC[die])>=4:return False
        self.CDC[die].append(self.capture[die].pop(0));return True

    def ACK_store(self,die,packet,accept_ps,scoreboard_visible_ps,sector_dut_retire_ps):
        if not self.CDC[die] or packet!=self.CDC[die][0]:raise ValueError('held FIFO packet must match source head')
        e=self.entry(die,packet['tag'],packet['transport_epoch']);o=e['owner']
        accepted,stored,retire=map(self.time,(accept_ps,scoreboard_visible_ps,sector_dut_retire_ps))
        visible=self.time(packet['visible_ps']);registered=(visible//FAST+1)*FAST
        if accepted<crossing(registered,SLOW) or stored<accepted or retire<stored or stored%SLOW:
            raise ValueError('ACK CDC/store/DUT retirement ordering')
        if (die,stored) in self.scoreboard_ports:raise ValueError('finite scoreboard one update per serial edge')
        self.scoreboard_ports.add((die,stored));self.CDC[die].pop(0);e['delivered'].add(packet['beat'])
        e['last_ACK_retire']=max(e.get('last_ACK_retire',0),retire)

    def consumer_result_retire(self,die,tag,epoch,result_visible_ps,dut_retire_ps):
        e=self.entry(die,tag,epoch);o=e['owner'];result,retire=map(self.time,(result_visible_ps,dut_retire_ps))
        if len(e['delivered'])!=o['length'] or result<e['last_ACK_retire'] or retire<result or e['consumer_retired'] is not None:
            raise ValueError('final finite consumer result/retirement missing')
        e['consumer_retired']=retire
        lock=self.RMW_locks.get((die,o['stack'],o['sector']))
        if lock and o['kind']=='read':lock['read_import_retired']=retire
        if len(self.return_CDC[die])>=4:raise ValueError('finite reverse-credit CDC full')
        self.return_CDC[die].append(dict(tag=tag,transport_epoch=epoch,client=o['client'],retired_ps=str(retire)))

    def credit_return(self,die,packet,return_ps):
        if not self.return_CDC[die] or packet!=self.return_CDC[die][0]:raise ValueError('credit held head identity/control mutation')
        e=self.entry(die,packet['tag'],packet['transport_epoch']);now=self.time(return_ps)
        if now<crossing(e['consumer_retired'],FAST):raise ValueError('actual retirement/reverse credit CDC required')
        self.return_CDC[die].pop(0);self.client_outstanding[die,e['owner']['client']]-=1
        owner=e['owner'];lock=(die,owner['stack'],owner['sector'])
        if owner['kind']=='write':
            if self.graph['instructions'][owner['instruction']]['opcode']=='KV_WRITE':
                self.writer_completed.setdefault(owner['instruction'],{})[(owner['stack'],owner['sector'])]=now
            if lock in self.RMW_locks:del self.RMW_locks[lock]
        del self.entries[die,packet['tag']];self.stats['credit_returns']+=1

    def quiescent(self):
        return not (self.waiting or self.entries or any(self.q_n.values()) or any(self.r_n.values()) or
                    self.backend_pending or any(self.client_outstanding.values()) or
                    any(self.capture) or any(self.CDC) or any(self.return_CDC) or self.RMW_locks)

    def begin_drain(self):
        if self.phase!='OPEN' or self.position is not None or not self.completed_positions or not self.quiescent():
            raise ValueError('drain requires full encoded boundary and zero tracked source resources')
        if self.epoch==(1<<32)-1 or self.nonce==(1<<32)-1:raise ValueError('transport/control epoch exhausted; no wrap')
        self.nonce+=1
        common=dict(control_tag=CONTROL_TAG,epoch=self.epoch,next_epoch=self.epoch+1,
            nonce=self.nonce,position=self.completed_positions[-1],
            final_instruction=len(self.graph['instructions'])-1,opcode='ARGMAX_REDUCE')
        self.control={die:dict(common,die=die) for die in (0,1)}
        self.control_phases={die:'REQUEST_HIGH' for die in (0,1)}
        self.phase='REQUEST_HIGH';self.request_level=1;self.control_waiting=True
        return [dict(self.control[d]) for d in (0,1)]

    def control_destination_accept(self,die,packet):
        if self.phase=='OPEN' or self.control_phases.get(die)!='REQUEST_HIGH' or packet!=self.control.get(die) or not self.quiescent():
            raise ValueError('control destination identity/drain resource mutation')
        self.acknowledge_level=1;self.control_phases[die]='ACK_HIGH';return dict(packet)

    def control_source_done(self,die,response):
        if self.phase=='OPEN' or self.control_phases.get(die)!='ACK_HIGH' or response!=self.control.get(die) or not self.acknowledge_level:
            raise ValueError('mailbox source response/control identity mutation')
        self.control_phases[die]='RETURN_ZERO'
        if all(p not in ('REQUEST_HIGH','ACK_HIGH') for p in self.control_phases.values()):
            self.request_level=0;self.control_waiting=False

    def control_destination_return_zero(self,die):
        if self.control_phases.get(die)!='RETURN_ZERO' or self.request_level or self.control_waiting:
            raise ValueError('source request must return zero first')
        self.control_phases[die]='ZERO_OBSERVED'
        if all(p=='ZERO_OBSERVED' for p in self.control_phases.values()):self.acknowledge_level=0

    def control_source_ready(self):
        # Source ot_cdc_mailbox src_ready requires no waiting/request/ack;
        # this is a model phase transition, not an externally supplied Boolean.
        if not all(self.control_phases.get(d)=='ZERO_OBSERVED' for d in (0,1)) or self.request_level or self.acknowledge_level or self.control_waiting or not self.quiescent():
            raise ValueError('mailbox return-zero/quiescence required before tag reuse')
        self.epoch=self.control[0]['next_epoch'];self.next_tag=[0,0]
        self.control=None;self.phase='OPEN';self.stats['completed_drains']+=1

def contract(repo=ROOT):
    pins={};sources={}
    for name,(revision,path) in SOURCE_PINS.items():
        commit=subprocess.check_output(['git','rev-parse',revision],cwd=repo,text=True).strip()
        raw=subprocess.check_output(['git','show',commit+':'+path],cwd=repo)
        pins[name]=dict(commit=commit,path=path,sha256=hashlib.sha256(raw).hexdigest());sources[name]=raw
    if b'rsp_tag' not in sources['controller'] or b'wr_done' in sources['controller']:
        raise ValueError('controller source port audit changed')
    graph=compile_program()
    # Additional candidate state, not free replacement of prior r3 resources.
    request_fields=dict(die=1,stack=2,client=6,logical_tag=64,logical_epoch=32,
        instruction=11,position=21,sector=34,kind=1,length=6,data=256,valid=1)
    map_fields=dict(owner=sum(request_fields.values())-256,transport_epoch=32,
        physical_tag=16,column_mask=32,generated_mask=32,captured_mask=32,
        delivered_mask=32,consumer_done=1)
    event_fields=dict(tag=16,transport_epoch=32,beat=5,stack=2,sector=34,client=6,
        logical_epoch=32,instruction=11,position=21,kind=1,visible_ps=64,data=256,valid=1)
    control_fields=dict(control_tag=16,epoch=32,next_epoch=32,nonce=32,position=21,die=1,
        final_instruction=11,opcode=5)
    req_bits=2*36*sum(request_fields.values());map_bits=2*4*sum(map_fields.values())
    event_bits=2*4*sum(event_fields.values())
    reverse_bits=2*4*(16+32+6+64+1)
    mailbox_bits=2*(4*sum(control_fields.values())+15)
    event_scoreboard_bits=2*3*len(graph['instructions'])
    allocator_bits=2*(17+32+6+3)+2*36*3
    counters_bits=2*4*32*2*10
    # Conservative independent bitmap and completion high-watermark for every
    # writer; no overlap with previously priced publication bitmap assumed.
    writer_completion_bits=sum(272+64 for op in graph['instructions'] if op['opcode']=='KV_WRITE')
    FF_bits=writer_completion_bits+req_bits+map_bits+2*event_bits+reverse_bits+mailbox_bits+event_scoreboard_bits+allocator_bits+counters_bits
    mux_bits=2*35*sum(request_fields.values())+2*3*sum(map_fields.values())+2*3*sum(event_fields.values())
    compare_bits=2*4*(16+32+6+34)+2*2*sum(control_fields.values())
    return dict(schema='Qwen_common36_tag16_held_ACK_drain_candidate_r2',source_pins=pins,
        source_audit={'controller':'TAGW16 valid/ready reads; q_n/r_n internal; original column-write modulo backing is not WRvisible. No visible/epoch/drain output.',
            'PC_service':'Wider prefixed owner tags; write-done externally supplied and pulse has no ready. Not directly wired to16bit controller.',
            'mailbox':'One outstanding closed-loop four-phase; src_done precedes full return-zero/src_ready; reset replay requires idempotence or fail-stop.',
            'FIFO':'Four-entry Gray-pointer ready/valid; resets flush and online rendezvous. Reset is not drain and cannot establish safe reuse.',
            'scoreboard':'ABI3 pending/signalled/published semantic reference only; not GPU organisation/physical reuse proof.'},
        graph_instruction_count=len(graph['instructions']),graph_opcodes=dict(Counter(o['opcode'] for o in graph['instructions'])),
        downstream_stage_binding='Retained source156c adapter requires addressed272sector publication, persistent prefix generation and exactly3reader flags. Common tag ledger only does not independently execute producer/scaled commit or attention; real join remains a hardware gate.',
        RMW_binding='All-client same-sector locks persist through old-sector RF import, exact XOR/AND/XOR three9serialcycle candidate callbacks, fullWRvisible/ACK-store/retire/reversecredit. Existing64x675bit lock contexts remain charged; use at most4/die, no free replacement.',
        encoded_callback_contract=[dict(id=o['id'],opcode=o['opcode'],participants=o['participants'],dependencies=o['dependencies'],
            inputs=o['inputs'],outputs=o['outputs'],issue='matching graphID/opcode and retired dependencies',
            result='source-produced result-visible callback',retire='after result-visible, no owned service callbacks or RMW locks; KV_WRITE all272 addressed WR visibility/ACK/consumer/reversecredit complete',
            actual_issue_RF_cycles=None,actual_consumer_service_cycles=None) for o in graph['instructions']],
        geometry=dict(dies=2,clients_per_die=36,request_holds_per_client=1,active_mappings_per_die=4,
            stacks=4,PCs_per_stack=32,controller_queued_beats=512,controller_return_beats=512,
            ACK_capture_depth_per_die=4,ACK_CDC_depth_per_die=4,reverse_credit_depth_per_die=4,
            shared_ingress_commands_per_stack_fast_cycle=1,combined_read_write_bytes_per_stack_fast_cycle=750),
        proposed_actual_source_port_extensions={'controller_request':'req_tag16,req_len6,req_addr34,req_we,req_wdata256 valid/ready; constant transport_epoch32 until proved drained',
            'WR_column':'held valid/ready: tag16,epoch32,sector34,column_ps64',
            'WR_visible':'held valid/ready only after backing commit: tag16,epoch32,sector34,visible_ps64',
            'read_return':'rsp_v/rdy/tag16/beat5/data256 plus producer-captured epoch32; receiver cannot stamp current epoch on late events',
            'drain_control':'Exact controltag65535/epoch/next_epoch/nonce/position/finalencodedID packet in four-phase source/dest mailbox. All source queues/holds/readers/CDC ledgers zero before reuse.'},
        allocator='One common36client namespace per die; data0..65534,65535 reserved control. Four retained owner mappings, round-robin36request holds. Reuse only full1737retirement + tracked drain + fourphase return-zero. No counter wrap/reset shortcut.',
        limitation='Bare old tag16 callback after reuse cannot be distinguished from a current identicaltag callback. Proposed producer-epoch field and verified no-old-callback-after-drain property are missing from current controller; hardware admission remains false.',
        candidate_additional_state=dict(request_fields=request_fields,map_fields=map_fields,event_fields=event_fields,
            control_fields=control_fields,request_hold_bits=req_bits,map_bits=map_bits,
            capture_plus_CDC_bits=2*event_bits,reverse_credit_bits=reverse_bits,mailbox_bits=mailbox_bits,
            all1737_event_bits=event_scoreboard_bits,allocator_bits=allocator_bits,
            addressed_writer_completion_bits=writer_completion_bits,
            source_queue_count_observer_bits=counters_bits,total_FF_bits=FF_bits,
            mux_bit_equivalents=mux_bits,comparator_bit_equivalents=compare_bits,
            conservative_additive_area_mm2=(FF_bits*.2916+(mux_bits+compare_bits)*.2)/.5/1e6,
            scope='Conservative additional model state beyondr3; no free overlap/subtraction. Exact FF/macro/logic/CDC/routing/RF sharing needs admission.'),
        finite_resource_latency={'ACK_ready_stalls':'held capture/FIFO credits, no accepted-write retirement',
            'scoreboard':'one store per die serial edge; actual engine callback stays unbound',
            'drain':'No timer; explicit request/ACK/return-zero phase callbacks. Actual mailbox/domain/NoC costs unbound.',
            'full1737_issue_RF_shared':None,'alltraffic_DRAM_column_refresh_turnaround':None,'total_token_cycles':None},
        producer_uses_actual_encoded_KV=False,actual_provider_credit=False,
        model_hardware_build_ready=False,whole_program_admission=False,headline_rate=None,
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    a.output.write_text(json.dumps(contract(a.repo),indent=2,sort_keys=True)+'\n')
