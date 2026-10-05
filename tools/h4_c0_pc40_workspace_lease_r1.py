#!/usr/bin/env python3
"""Finite direct-RF source preparation and exact captured-frame lease join.

Source-sized software port seam, off by default. The real RF ACK has no tag;
one pending write binds it to the active owner. Installed hookup is separate.
"""
import argparse
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import h4_c0_source_operand_views_r1 as V

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/c0_pc40_payload_lease_20261003'

def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(ok,msg):
    if not ok:raise ValueError(msg)

def RF_source():
    row=json.loads((BASE/'RF_port_source_r1.json').read_text())
    raw=(ROOT/row['archive']).read_bytes();require(sha(raw)==row['sha256'],'RF source pin')
    for text in (b'input wire [8:0] rd_a, rd_b',b'output reg [4095:0] rsp_a, rsp_b',
                 b'input wire [8:0] wr_addr',b'input wire [4095:0] wr_data',
                 b'output reg ack_valid, input wire ack_ready',
                 b'if(write_go) begin ack_valid<=1',b'.w_ce_in(write_go && wr_addr[8:7]==p)'):
        require(text in raw,'actual RF port/control contract')
    require(b'parent55' not in raw,'untagged source ACK, no invented HBM parent')
    return row

def native_price():
    tree=ast.parse(V.sources()['V1_source.py'])
    names={'contract','latency_key','positive','command_cost'}
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names
              or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('DEFAULT','V1','ALIASES') for t in n.targets)]
    ns=dict(math=math);exec(compile(ast.Module(body=selected,type_ignores=[]),'frozen-V1-service','exec'),ns)
    return ns['command_cost']('FMAX',[32,32],32,elements=128,lanes=32)

def frame(raw,*,version,lease,slot,role):
    require(isinstance(raw,bytes) and len(raw)==512,'full direct-RF source frame512')
    require(type(slot) is int and 0<=slot<512 and version and lease,'exact slot/version/lease')
    banks=[dict(bank=b,page=slot>>7,row=slot&127,bit_offset=0,bits=256,
                source_byte_range=[32*b,32*(b+1)],sha256=sha(raw[32*b:32*(b+1)])) for b in range(16)]
    return dict(version=version,lease=lease,RFslot9=slot,role=role,bytes=512,sha256=sha(raw),
                lane_words=128,word_bits=32,packing='little-endian U32 lane i at wr_data[32*i+:32]',
                RF_banks=banks,physical_mirrors=2,HBM_byte_address=None,parent55=None)

def bind_capture(directory,*,generation,owner_tag,response_stall_bound):
    directory=Path(directory);capture=json.loads((directory/'native_capture.json').read_text())
    require(capture['source_commit']=='870c5fe581b768df28dd2998b2d0aecc24510c23'
            and capture['image_manifest_sha256']=='83491cd2487ec026e86b5943e0420a4efcb6830aaf35f761e20190a469fd69e7',
            'released executor/image identity')
    require((capture['native_PC'],capture['template'],capture['step'],capture['opcode'])==(40,'exp',0,'FMAX')
            and capture['producer_PC_hash_matches']==40 and capture['source_call_complete'] is True
            and capture['oracle_started'] is False,'actual one native capture, before oracle')
    owner=capture['actual_gate_owner']
    require(owner['source_key']==['RF',0,0,38] and owner['version']=='Qwen.39.L0.d0.gu_post.49'
            and owner['published'] is True and capture['source_gate_lease_released'] is False,'actual retained source gate lease')
    packet=V.OperandViews(enabled=True).bind_eligible(40,0,generation=generation,owner_tag=owner_tag,
                                                    response_stall_bound=response_stall_bound)
    command=packet['native_command'];homes=command['source_version_home_refs']+[command['destination_version_home_ref']]
    payloads={};frames={}
    for name,home in zip(('negative','constant','FMAX'),homes):
        record=capture['frames'][name];raw=(directory/record['file']).read_bytes()
        require(record['bytes']==512 and sha(raw)==record['sha256'],'actual captured frame '+name)
        payloads[name]=raw;frames[name]=frame(raw,version=home['version'],lease=home['lease'],slot=home['RF_vectors'][0],role=name)
    gate_record=capture['frames']['gate'];gate=(directory/gate_record['file']).read_bytes()
    require(sha(gate)==gate_record['sha256'] and sha(gate)==owner['mirror_word_sha256'],'actual gate RF mirror payload')
    payloads['gate']=gate;frames['gate']=frame(gate,version=owner['version'],lease=owner['lease'],slot=38,role='source_gate')
    require(frames['constant']['sha256']==sha((0xc2ae0000).to_bytes(4,'little')*128),'source -87 broadcast bits')
    return packet,frames,payloads

class WorkspaceLease:
    """Single outstanding RF transaction and frozen native owner, software only."""
    def __init__(self,packet,*,enabled=False,frame_bindings=None):
        require(enabled,'workspace preparation default off')
        require(packet==V.verification_adapter().bind_eligible(40,0,
                    generation=packet['native_command']['generation'],owner_tag=packet['native_command']['owner_tag'],
                    response_stall_bound=packet['native_command']['response_stall_bound']), 'exact source packet')
        self.packet=copy.deepcopy(packet);self.pending=None;self.pages={};self.consumer=False;self.reverse=False
        self.output_visible=False;self.read_captured=False;self.computed=False;self.log=[];self.sequence=0;self.released=False
        c=packet['native_command'];self.owner=(c['rank'],c['SM'],c['generation'],c['owner_tag'])
        self.slots=(17,18,19);RF_source()
        homes=c['source_version_home_refs']+[c['destination_version_home_ref']]
        self.leases={h['RF_vectors'][0]:h['lease'] for h in homes}
        self.frames={} if frame_bindings is None else copy.deepcopy(frame_bindings)
        if frame_bindings is not None:
            require(set(self.frames)==set(self.slots),'complete captured source workspace frames')
            require(all(self.frames[s]['RFslot9']==s and self.frames[s]['lease']==self.leases[s] for s in self.slots),
                    'source frame lease/slot agreement')

    def event(self,name,**data):
        self.sequence+=1;self.log.append(dict(sequence=self.sequence,event=name,owner=list(self.owner),**data))

    def write_offer(self,slot,raw,lease):
        require(not self.released and self.pending is None,'one pending RF transaction, hold through commonACK')
        require(slot in self.slots and isinstance(raw,bytes) and len(raw)==512 and lease==self.leases[slot],
                'bound workspace full write/lease')
        if self.frames:require(sha(raw)==self.frames[slot]['sha256'],'captured source workspace payload')
        require(not self.read_captured or slot==19,'inputs held through native consumer/reverse')
        require(slot!=19 or self.computed,'native source compute completion before result write')
        self.pending=dict(kind='write',slot=slot,data=raw,lease=lease,accepted=False)
        self.event('wr_offer',wr_valid=True,wr_addr=slot,payload_sha256=sha(raw),lease=lease)

    def write_accept(self,*,wr_ready,ack_valid_before):
        require(self.pending is not None and self.pending['kind']=='write' and not self.pending['accepted'], 'offered source write')
        require(wr_ready is True and ack_valid_before is False,'source write accepted only with idle ACK lane')
        self.pending['accepted']=True;self.event('wr_accept',write_go=True,both_mirrors_written=True)

    def common_ACK(self,owner,*,ack_valid,ack_ready):
        require(tuple(owner)==self.owner and self.pending is not None
                and self.pending['kind']=='write' and self.pending['accepted'],'untagged ACK must match sole active write/owner')
        require(ack_valid is True and ack_ready is True,'actual common ACK handshake')
        p=self.pending;self.pages[p['slot']]=dict(data=p['data'],lease=p['lease'],mirrors=2)
        if p['slot']==19:self.output_visible=True
        self.event('commonACK_accept',slot=p['slot'],both_mirrors_ACK=True,parent55=None)
        self.pending=None

    def read_offer(self,slots):
        require(not self.released and self.pending is None and not self.read_captured,'exclusive source read window')
        require(tuple(slots)==(17,18) and all(s in self.pages for s in slots),'exact two prepared operands')
        self.pending=dict(kind='read',accepted=False);self.event('rd_offer',rd_valid=True,rd_a=17,rd_b=18)

    def read_accept(self,*,rd_ready):
        require(self.pending is not None and self.pending['kind']=='read' and not self.pending['accepted']
                and rd_ready is True,'actual RF read acceptance')
        self.pending['accepted']=True;self.event('rd_accept',read_go=True)

    def response_capture(self,owner,*,rsp_valid,rsp_ready,payloads):
        require(tuple(owner)==self.owner and self.pending is not None and self.pending['kind']=='read'
                and self.pending['accepted'],'accepted read bound to native owner')
        require(rsp_valid is True and rsp_ready is True,'actual RF response consumed')
        require(list(payloads)==[self.pages[17]['data'],self.pages[18]['data']],'exact source RF response bytes/order')
        self.pending=None;self.read_captured=True;self.event('rsp_accept',response_bits=8192)

    def native_complete(self,owner,*,output_sha256):
        require(tuple(owner)==self.owner and self.read_captured and not self.computed and self.pending is None,
                'actual accepted source operands before native completion')
        require(isinstance(output_sha256,str) and len(output_sha256)==64,'exact native result frame identity')
        if self.frames:require(output_sha256==self.frames[19]['sha256'],'actual captured native result')
        self.computed=True;self.event('native_complete',opcode='FMAX',output_sha256=output_sha256)

    def consumer_accept(self,owner):
        require(tuple(owner)==self.owner and self.output_visible and self.pending is None and not self.consumer,
                'mirrored result commonACK before source exp-step1 consumer')
        self.consumer=True;self.event('source_consumer_accept',consumer='exp.step1.FMIN')

    def validated_reverse(self,owner,*,source_event,sequence):
        require(tuple(owner)==self.owner and self.consumer and not self.reverse and source_event=='validated_reverse_grant'
                and type(sequence) is int and sequence>self.sequence,'causal exact owner reverse receipt')
        self.sequence=sequence;self.reverse=True;self.event('validated_reverse')

    def retire(self):
        require(self.consumer and self.reverse and self.pending is None,'no workspace reuse before consumer and reverse')
        self.released=True;self.event('workspace_retire',source_gate_home_released=False)

def model():
    p=native_price()
    # Native V1's existing costs are provisional, not measured SS/FF timing.
    return dict(schema='C0_PC40_WORKSPACE_PORT_LEASE_MODEL_R1',default_enabled=False,
                RF_source=RF_source(),source_ports=dict(rd_a_bits=9,rd_b_bits=9,rsp_a_bits=4096,rsp_b_bits=4096,
                    wr_addr_bits=9,wr_data_bits=4096,rd_valid_ready=True,rsp_valid_ready=True,
                    wr_valid_ready=True,common_ACK_valid_ready=True,ACK_tag_bits=0),
                source_native_service=p,selected_slots=[17,18,19],workspace_bytes=1536,workspace_mirror_bytes=3072,
                new_RF_macros=0,alias_fence='RF read response consumed before write; constant slot18 reused only after XOR producer consumer/reverse',
                finite_resources=dict(native_owners=1,pending_RF_transactions=1,read_ports=2,write_ports=1,workspace_vectors=3),
                preparation='source gate read/copy; exact NEG BITCAST_U/XOR/BITCAST_F; explicit mask and -87 broadcast; all full vector writes require common mirrored ACK',
                release='FMAX output19 held to exp.step1 FMIN consumer and validated reverse; source gate38 lease remains until whole PC40 consumer done',
                source_frame_bytes=512,bank_payload_bytes=32,banks=16,pages=4,mirrors=2,
                domain_policy_GHz=dict(RF=1.2,serial_chain=0.9),
                clock_cost_scope='existing provisional V1 ticks; exact CDC/route/corner service must be owner-priced before build',
                missing_physical_inputs=['installed rank0/SM0 RF connector and source-owned dispatch/commonACK mux',
                    'actual preparation/CDC service delays, routing cuts, control protection and PG pricing',
                    'SS setup/FF hold in component context under unchanged uncertainty'],
                installed_call_admitted=False,physical_admitted=False,parent55=None)

def caller_preparation_model():
    """Additive complete caller preparation; preserve the leaf-only r1 row."""
    adapter=V.verification_adapter()
    op=adapter.native['operations'][40]
    size=adapter.native['source_program']['config']['intermediate_size']//2
    gate=adapter.view(op['reads'][0],0,128,0,'read',40)
    up=adapter.view(op['reads'][0],size,128,0,'read',40)
    require((gate['storage_SM'],gate['RFslot9'])==(0,38) and
            (up['storage_SM'],up['RFslot9'])==(24,32),'actual source first SILU gate/up homes')
    return dict(schema='C0_PC40_CALLER_PREPARATION_MODEL_R2',leaf_model=model(),
                source_order=['read gate[0:128]','read up[6144:6272]','neg(gate)','exp.step0 FMAX'],
                source_gate_home=gate,source_up_home=up,
                source_RF_read_services=2,source_read_payload_bytes=1024,
                NoC_up_payload_bits=4096,NoC_up_pages=1,
                retained_caller_vectors=2,primitive_workspace_vectors=3,
                caller_retained_slot_binding=None,
                caller_retained_slot_scope='source VM retains gate/up arrays; concrete owner emitter calendar placement still required',
                latency_expression='2*C_SOURCE_RF_READ + C_NoC_UP_PAGE + C_CDC_UP + C_NEG_CHAIN + 2*C_CONST_BROADCAST + C_FMAX_SOURCE_SERVICE',
                latency_ns=None,source_FMAX_service_provisional_ticks=14,
                clock_domains_GHz=dict(source_RF=1.2,native_serial=0.9),
                source_order_included=True,NoC_idealized=False,installed_call_admitted=False,
                physical_admitted=False,
                missing_inputs=['exact gate/up retained placement in Dewey calendar',
                                'source-sized SM24->SM0 NoC/CDC service and cuts',
                                'actual direct-RF commonACK/owner binding and component SS/FF'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--caller-preparation',action='store_true');a=p.parse_args()
    a.out.write_bytes(canonical(caller_preparation_model() if a.caller_preparation else model()))

if __name__=='__main__':main()
