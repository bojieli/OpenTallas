#!/usr/bin/env python3
"""Opt-in source-bound native fragment emitter and continued-capture MODEL.

No numerical callback or installed hardware is implied. Native arithmetic and
rounding stay in the pinned leaf. A proposed continued-capture port transfers
an admission seat to retained child metadata; it never grants physical reverse.
"""
import argparse, ast, copy, functools, gzip, hashlib, json, math
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]/'results/uarch/h4_hbm_baseline_bridge_20261003/native_frame_r5'
PIN='f2b72ba6f4d1a8cc64b84877a4774a893c7e2e494da5f21e4eb955d177f0a8af'
REQUIRED={'model','family','source_PC','program_sha256','template_id','ordered_step_index','owner_tag','generation','rank','SM','opcode','source_bittypes','destination_bittype','source_version_home_refs','destination_version_home_ref','predicate','active_lanes','source_attrs_rounding','response_stall_bound'}
ALIASES={'I2F':'ITOF','FCMP_EQ':'CMP_EQ','FCMP_NE':'CMP_NE','FCMP_GT':'CMP_GT','FCMP_LT':'CMP_LT'}

def need(ok,message):
    if not ok:raise ValueError(message)
def uint(n,b,label):need(type(n)is int and 0<=n<2**b,label)
def canonical(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def protect(n):return math.ceil(n/64)*72
@functools.lru_cache(maxsize=1)
def inputs():
    raw=(BASE/'input_manifest.json').read_bytes();need(sha(raw)==PIN,'hard input manifest pin');out={}
    for row in json.loads(raw):
        p=(BASE/row['archive']).resolve();need(p.is_relative_to((BASE/'inputs').resolve()),'archive scope');raw=p.read_bytes()
        need(len(raw)==row['bytes'] and sha(raw)==row['sha256'],'exact origin input '+p.name);out[p.name]=raw
    return out

def address(byte):
    uint(byte,37,'actual byte aperture');need(byte<81000000000 and byte%32==0,'r17 aligned sector aperture')
    local=(byte//512)*128+byte%128;sector=local//32;uint(sector,31,'retained local sector31 in AW34')
    stack=(byte//128)%4;pc=((sector>>2)^(sector>>7)^(sector>>12))&31
    return dict(stack=stack,local_sector34=sector,physical_PC7=32*stack+pc)

def versions(obj):
    if isinstance(obj,str):return {obj} if obj.startswith(('Qwen.','DeepSeek.')) else set()
    if isinstance(obj,dict):return set().union(*(versions(v) for v in obj.values())) if obj else set()
    if isinstance(obj,list):return set().union(*(versions(v) for v in obj)) if obj else set()
    return set()

@functools.lru_cache(maxsize=1)
def catalog():
    """Compiler descriptions only; no model numerical tensor is materialized."""
    src=inputs();out={}
    for model,name,key in [('Qwen','Qwen_tiled.json.gz','operations'),('DeepSeek','program_final.json.gz','instructions')]:
        raw=src[name];d=json.loads(gzip.decompress(raw));rows=d[key];expected=1737 if model=='Qwen' else 2213
        need(len(rows)==expected and [r['pc'] for r in rows]==list(range(expected)),'complete source PC order')
        descriptions=[]
        for op in rows:
            if model=='Qwen':
                active=op['calendar_export']['physical_primitives']['kernel_invocations']
                leaves={k:d['microcode'][k] for k,n in active.items() if n and k in d['microcode']}
            else:
                leaves={b['template']:d['templates'][b['template']]['code'] for b in op['rank_bindings'] if 'template' in b}
            descriptions.append(dict(ranks={k:{b['rank'] for b in op.get('rank_bindings',[]) if b.get('template')==k} for k in leaves},family=op.get('opcode',op.get('family')),reads=versions(op['reads']),writes=versions(op['writes']),leaves=leaves))
        out[model]=dict(hash=sha(raw),PCs=len(rows),families=len({r['family'] for r in descriptions}),ops=descriptions)
    return out

class NativeCompiler:
    """Consumes the actual accepted native command plus explicit address binding.

    C0 clients0..4 are explicit bindings, not provider-class casts. Caller supplies
    source-bound home byte bases; this compiler never invents a home SM or DS die.
    Only full128lane32/64bit RF words are admitted here. Partial/FP8 joins refuse.
    """
    def compile(self,command,home_addresses,binding,client):
        need(REQUIRED<=set(command),'complete native C0 command');c=copy.deepcopy(command);s=catalog().get(c['model']);need(s is not None,'documented model')
        uint(c['source_PC'],12,'source program PC12');need(c['source_PC']<s['PCs'] and c['program_sha256']==s['hash'],'actual source program pin/PC')
        op=s['ops'][c['source_PC']];need(c['family']==op['family'],'actual source family')
        leaves=op['leaves'];need(c['template_id'] in leaves,'actual invoked source template')
        if c['model']=='DeepSeek':need(c['rank'] in op['ranks'][c['template_id']],'actual template rank binding')
        supported=None
        for assignment in ast.parse(inputs()['V1_source.py']).body:
            if isinstance(assignment,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='V1' for t in assignment.targets):supported=ast.literal_eval(assignment.value)
        need(c['opcode'] in supported,'documented exact V1 micro-operator only')
        code=leaves[c['template_id']];step=c['ordered_step_index'];need(type(step)is int and 0<=step<len(code),'ordered source microstep')
        node=code[step];need(len(c['source_bittypes'])==len(c['source_version_home_refs']),'native arity/home agreement')
        source_contract_module=ast.parse(inputs()['V1_source.py']);selected=[]
        for item in source_contract_module.body:
            if isinstance(item,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('V1','ALIASES') for t in item.targets):selected.append(item)
            if isinstance(item,ast.FunctionDef) and item.name=='contract':selected.append(item)
        env={};exec(compile(ast.Module(body=selected,type_ignores=[]),'source_pinned_V1_contract','exec'),env)
        contract=env['contract'](c['opcode']);need(len(c['source_bittypes'])==contract['arity'],'exact documented source arity')
        if c['opcode']=='SELECT':need(c['source_bittypes'][0]==32,'source U32 predicate, never64bit fabricated predicate')
        if c['opcode'].startswith('FCMP_'):need(c['destination_bittype']==32,'predicate output32')
        need(node['op']==ALIASES.get(c['opcode'],c['opcode']) and node.get('attrs',{})==c['source_attrs_rounding'],'literal source opcode/rounding')
        for k in ('owner_tag','generation'):uint(c[k],64,'retain native '+k+'64')
        need(type(client)is int and 0<=client<5,'explicit C0 client bank, never KV5')
        need(c['active_lanes']==128 and c['destination_bittype'] in (32,64) and all(b in (32,64) for b in c['source_bittypes']),'full128lane U32/F32/I64 RF words; partial and packed formats require separate join')
        need(binding.get('model')==c['model'] and binding.get('rank')==c['rank'] and binding.get('SM')==c['SM'] and binding.get('physical_RF_id'),'explicit caller rank/SM/RF binding')
        uint(binding.get('die'),1,'actual accepted provider DIE1');uint(c['SM'],5,'accepted requester SM5')
        need(binding.get('scope')=='software_reference' and binding.get('operand_view_scope')=='protocol_control',
             'production native SSA/tile/bittypes/home view admission pending; explicit protocol control only')
        need(len(c['source_version_home_refs'])==len(c['source_bittypes']),'source home/bittypes')
        homes=[(h,b,'source_refill') for h,b in zip(c['source_version_home_refs'],c['source_bittypes'])]+[(c['destination_version_home_ref'],c['destination_bittype'],'destination_writeback')]
        frames=[]
        for home,bits,kind in homes:
            need(home.get('version') in (op['reads'] if kind=='source_refill' else op['writes']),'actual source version')
            need(home.get('rank')==c['rank'] and home.get('SM')==c['SM'] and home.get('generation')==c['generation'] and home.get('physical_RF_id')==binding['physical_RF_id'] and home.get('lease'),'exact typed home/lease, no persistent-home SM fabrication')
            slots=home['RF_vectors'];need(len(slots)==bits//32,'exact I64 low/high RF words')
            for word,slot in enumerate(slots):
                uint(slot,9,'actual RFslot9');key=(home['version'],home['lease'],word);need(key in home_addresses,'explicit addressed provider word binding')
                base=home_addresses[key];need(type(base)is int and base%512==0,'full-frame addressed base; partial join not implemented')
                children=[dict(frame=len(frames),sector=i,byte=base+32*i,RFslot9=slot,version=home['version'],lease=home['lease'],direction=kind,R14_LEN6=1,R14_BEAT5=0,die=binding['die'],**address(base+32*i)) for i in range(16)]
                frames.append(dict(frame=len(frames),kind=kind,RFslot9=slot,version=home['version'],lease=home['lease'],byte_base=base,children=children))
        need(len(frames)<=8,'actual source max64fragments envelope, not a per-program cap')
        need(len({f['RFslot9'] for f in frames})==len(frames),'distinct frame RFslots; alias reuse requires a source lifetime join')
        return dict(schema='NATIVE_SOURCE_FRAME_PLAN_R5',native_command=c,binding=copy.deepcopy(binding),client=client,frames=frames,fragments=8*len(frames),children=16*len(frames),native_arithmetic_unchanged=True,source_leaf=dict(shape=node.get('shape'),operands=node.get('src'),destination=node.get('dst')),operand_views_production_admitted=False,hardware_admitted=False)

class SourceAllocator:
    """One global parent allocation/edge and one frozen C0 proposal per client.

    New opaque hardware counters preserve native64 privately. W2 acceptance alone
    advances each36bit tuple. A live parent retains all children through reverse.
    """
    def __init__(self,die=0):uint(die,1,'actual provider die');self.die=die;self.next=[0]*5;self.parent_next=0;self.parents={};self.held={};self.edge=-1
    def parent(self,plan,edge):
        need(type(edge)is int and edge>self.edge,'one actual parent allocation per die edge')
        need(plan['binding']['die']==self.die,'allocator die scope')
        need(not any(p['physical_RF_id']==plan['binding']['physical_RF_id'] for p in self.parents.values()),'physical RF owner alias exclusion')
        sm=plan['native_command']['SM'];need(sm not in self.parents,'one atomic C0 parent per physical SM')
        need(self.parent_next<2**32,'parentref wrap needs actual all-copy rearm')
        ref=self.parent_next;self.parent_next+=1;self.edge=edge;self.parents[sm]=dict(reference=ref,native=copy.deepcopy(plan['native_command']),accepted={},frame_owners={},frame_slots={f['frame']:f['RFslot9'] for f in plan['frames']},expected=plan['children'],physical_RF_id=plan['binding']['physical_RF_id']);return ref
    def propose(self,plan,frame,sector):
        sm=plan['native_command']['SM'];parent=self.parents.get(sm);need(parent is not None and parent['native']==plan['native_command'],'full native parent retained')
        client=plan['client'];need(client not in self.held,'one frozen proposal per client')
        need(type(frame)is int and 0<=frame<len(plan['frames']) and type(sector)is int and 0<=sector<16,'literal child extent')
        child=plan['frames'][frame]['children'][sector];n=self.next[client];need(n<2**36,'tuple wrap requires source all-copy fence')
        tag=n&0xffffffff;gen=n>>32;owner=(child['physical_PC7']<<39)|(client<<36)|(tag<<4)|gen
        request=dict(child=copy.deepcopy(child),tag32=tag,producer_gen4=gen,child_owner46=owner,parentref32=parent['reference'],SM=sm,
                     meta92=(owner<<46)|(sm<<41)|(child['RFslot9']<<32)|parent['reference'])
        if frame not in parent['frame_owners']:
            need(sector==0,'parent frame anchor bound before any child acceptance');parent['frame_owners'][frame]=owner
        self.held[client]=request;return copy.deepcopy(request)
    def accept(self,client,request):
        need(request['child']['frame'] in self.parents[request['SM']]['frame_owners'],'parent55 pre-bound before actual W2 accept')
        need(self.held.get(client)==request,'actual matched W2 accepted proposal');key=(request['child']['frame'],request['child']['sector']);need(key not in self.parents[request['SM']]['accepted'],'duplicate source sector accept')
        self.next[client]+=1;del self.held[client]
        self.parents[request['SM']]['accepted'][key]=copy.deepcopy(request);return copy.deepcopy(request)
    def retire(self,SM,reference,allcopy_receipt,completed):
        need(SM in self.parents and self.parents[SM]['reference']==reference,'exact native parent release')
        need(completed.parent_ready() and completed.parentref==reference and completed.plan['native_command']==self.parents[SM]['native'],'actual complete frame/consumer/child reverse before parent retirement')
        need(len(self.parents[SM]['accepted'])==self.parents[SM]['expected'],'all declared sector acceptances')
        need(allcopy_receipt.get('source')=='software_reference_allcopies' and allcopy_receipt.get('empty') is True,'no unproved physical rearm')
        need(not any(r['SM']==SM for r in self.held.values()),'unaccepted held proposal cannot vanish');del self.parents[SM]
    def rearm(self,receipt):
        need(not self.parents and not self.held,'all native parent/child debts before tuple reset')
        fields={'admission_stopped','provider_old_response_absent','assembler_empty','W2_empty','RF_ACK_empty','consumer_empty','child_reverse_empty','parent_reverse_empty','forward_CDC_empty','return_CDC_empty','reverse_CDC_matched','both_reset_domains_accepted'}
        need(set(receipt)==fields and all(v is True for v in receipt.values()),'source-owned complete all-copy fence required')
        self.next=[0]*5;self.parent_next=0

class ContinuedCapture:
    """One64B dispatch seat, one512B assembler; up to128 retained child rows.

    capture transfers the dispatch seat to retained child metadata. This proposed
    handshake is not the original provider reverse credit or RF commonACK.
    A source-refill frame can reuse data storage only after exact RF commonACK.
    Writeback requires actual RF frame capture first, then backing-visible returns.
    """
    def __init__(self,plan,parentref,allocator):
        p=allocator.parents.get(plan['native_command']['SM']);need(p is not None and p['reference']==parentref,'actual allocator-held parent')
        self.allocator=allocator
        self.plan=copy.deepcopy(plan);self.parentref=parentref;self.owners=p['frame_owners'];self.frame=0;self.fragment=0;self.seat=None;self.data=bytearray(512);self.children={};self.acked=set();self.consumer=False;self.reverse=set();self.capture_releases=0;self.writeback_captured=False;self.fault=False
    def check(self,ok,message):
        if self.fault or not ok:self.fault=True;raise ValueError('retained fault/debt: '+message)
    def admit(self,fragment,requests):
        self.check(self.frame<len(self.plan['frames']) and self.seat is None and fragment==self.fragment and fragment<8,'ordered one64B seat continued admission')
        self.check(len(requests)==2,'two actual sector children/fragment')
        self.check(self.plan['frames'][self.frame]['kind']!='destination_writeback' or self.writeback_captured,'source commonRFACK and exact frame snapshot before writeback')
        staged=[]
        for i,r in enumerate(requests):
            child=self.plan['frames'][self.frame]['children'][2*fragment+i]
            parent=self.allocator.parents[self.plan['native_command']['SM']]
            self.check(parent['accepted'].get((self.frame,child['sector']))==r,'actual W2 accepted opaque tuple, not labelled candidate')
            self.check(r['child']==child and r['parentref32']==self.parentref and r['SM']==self.plan['native_command']['SM'],'source-bound frame/sector/parent')
            self.check((self.frame,child['sector']) not in self.children,'duplicate child acceptance')
            staged.append(((self.frame,child['sector']),dict(request=copy.deepcopy(r),returned=False,physical=None,reverse=False)))
        for key,row in staged:self.children[key]=row
        self.seat=dict(fragment=fragment,rows=[(self.frame,2*fragment),(self.frame,2*fragment+1)])
    def returned(self,sector,owner46,meta92,backend16,payload,*,backing_visible=False):
        self.check(self.seat is not None and (self.frame,sector) in self.seat['rows'],'actual accepted fragment return')
        row=self.children[self.frame,sector];r=row['request'];self.check(not row['returned'] and owner46==r['child_owner46'] and meta92==r['meta92'],'exact fullwidth matched child return')
        self.check(type(backend16)is int and 0<=backend16<2**16,'full independent backendgen4/tag12');key=(r['child']['die'],r['child']['stack'],backend16&4095)
        self.check(not any(v['physical'] is not None and v['physical'][:3]==key for v in self.children.values()),'physical12 tag quarantined through parent reverse')
        kind=self.plan['frames'][self.frame]['kind']
        if kind=='source_refill':self.check(isinstance(payload,bytes) and len(payload)==32 and not backing_visible,'actual source32B capture, not visibility pulse');self.data[sector*32:(sector+1)*32]=payload
        else:self.check(backing_visible is True and payload is None,'matched backing-visible write return required, not command acceptance')
        row['physical']=key+(backend16>>12,);row['returned']=True
    def continue_capture(self):
        self.check(self.seat is not None and all(self.children[k]['returned'] for k in self.seat['rows']),'payload and both child identities committed before seat transfer')
        self.seat=None;self.fragment+=1;self.capture_releases+=1
        return dict(event='continued_fragment_capture_accept',physical_reverse=False,parent_release=False,RF_ACK=False,retained_children=len(self.children))
    def writeback_RF_capture(self,parent55,payload):
        self.check(self.frame<len(self.plan['frames']) and self.plan['frames'][self.frame]['kind']=='destination_writeback' and self.fragment==0 and self.seat is None and not self.writeback_captured,'ordered actual writeback source snapshot')
        self.check(self.frame in self.owners and parent55==(self.owners[self.frame]<<9)|self.plan['frames'][self.frame]['RFslot9'],'pre-bound source commonRFACK55')
        self.check(isinstance(payload,bytes) and len(payload)==512,'exact full source RF frame, no host arithmetic callback')
        self.data[:]=payload;self.writeback_captured=True
    def write_payload(self,sector):
        self.check(self.writeback_captured,'captured native RF snapshot before provider payload');return bytes(self.data[sector*32:(sector+1)*32])
    def assembled(self):
        self.check(self.fragment==8 and self.seat is None and self.plan['frames'][self.frame]['kind']=='source_refill','complete16-sector source frame, no partial zero fill');return bytes(self.data)
    def frame_ACK(self,parent55):
        self.check(self.frame<len(self.plan['frames']) and self.fragment==8 and self.seat is None,'all fragment captures before frame acknowledgment')
        frame=self.plan['frames'][self.frame];self.check(parent55==(self.owners[self.frame]<<9)|frame['RFslot9'],'exact pre-bound RF parent55/slot')
        self.acked.add(self.frame);self.frame+=1;self.fragment=0
        # Data scratch is reusable; retained child rows and frame records remain.
        self.data[:]=bytes(512);self.writeback_captured=False
    def consumer_accept(self):
        self.check(self.frame==len(self.plan['frames']) and self.seat is None and not self.consumer,'all frame/commonACK and write visibility before actual consumer');self.consumer=True
    def reverse_child(self,frame,sector,owner46,backend16,*,matched_CDC):
        self.check(self.consumer and matched_CDC is True,'actual consumer and matched reverseCDC, no local credit substitute')
        self.check((frame,sector) in self.children,'accepted child reverse extent')
        row=self.children[frame,sector];r=row['request'];self.check(not row['reverse'] and owner46==r['child_owner46'] and backend16==(row['physical'][3]<<12)|row['physical'][2],'exact held backend token and child reverse')
        row['reverse']=True;self.reverse.add((frame,sector))
    def parent_ready(self):return not self.fault and self.consumer and len(self.reverse)==self.plan['children']

COSTS=('allocator','W2_select','allocate_metadata','request_CDC','backend_read','backend_write_visible','R14_arb','R14_lookup','W2_read_hold','W2_write_hold','return_CDC','capture_data','capture_metadata','continuation','RF_common_ACK','writeback_RF_capture','native_compute','consumer','reverse_route','reverse_CDC','reverse_metadata','allcopy')
def calendar(plan,costs):
    """Positive serialized prospective DAG, clock domains supplied explicitly.

    Existing provider intervals may be substituted by eventID; no duplicate
    charge, no command-count/PHY or whole-program contender qualification.
    """
    need(set(costs)==set(COSTS),'complete selected positive stage profile')
    for v in costs.values():need(set(v)=={'ns','domain','source'} and type(v['ns']) in (int,float) and math.isfinite(v['ns']) and v['ns']>0 and v['domain'] and v['source'],'positive explicit clock-domain/source cost; no hidden zero')
    events=[];last=None;time=0;retained=0;peak=0
    def event(key,cost,**attrs):
        nonlocal last,time
        row=dict(eventID=key,cost_key=cost,dependency=[] if last is None else [last],start_ns_assumed=time,end_ns_assumed=time+costs[cost]['ns'],clock=costs[cost]['domain'],source=costs[cost]['source'],**attrs)
        events.append(row);time=row['end_ns_assumed'];last=key
    prefix=sha(canonical(plan['native_command']))
    event(prefix+'/parent','allocator',retains_full_native=True)
    computed=False
    for f in plan['frames']:
        fi=f['frame'];write=f['kind']=='destination_writeback'
        if write and not computed:event(prefix+'/compute','native_compute',arithmetic_callback=False,source_contract_unchanged=True);computed=True
        if write:
            event(prefix+f'/f{fi}/commonACK','RF_common_ACK',source_visible_write_before_provider=True,parent55_prebound=True)
            event(prefix+f'/f{fi}/RFcapture','writeback_RF_capture',mirrored_write_prerequisite=True)
        for fragment in range(8):
            for sector in (2*fragment,2*fragment+1):
                p=prefix+f'/f{fi}/s{sector}';retained+=1;peak=max(peak,retained)
                for cost in ('W2_select','allocate_metadata','request_CDC','backend_write_visible' if write else 'backend_read','R14_arb','R14_lookup','W2_write_hold' if write else 'W2_read_hold','return_CDC'):event(p+'/'+cost,cost,retained_child_rows=retained,sector_bytes=32)
            p=prefix+f'/f{fi}/frag{fragment}'
            # A single32B data port and single metadata update port require two
            # separately paid captures/updates for each64B fragment.
            for sector in (2*fragment,2*fragment+1):
                event(p+f'/s{sector}/capture_data','capture_data',bytes=32,physical_reverse=False)
                event(p+f'/s{sector}/capture_metadata','capture_metadata',child_updates=1,physical_reverse=False)
            event(p+'/continuation','continuation',physical_reverse=False,fragment_dispatch_seat_transfer=True)
        if not write:event(prefix+f'/f{fi}/commonACK','RF_common_ACK',parent55_prebound=True,RF_data_reuse_allowed=True,physical_reverse=False)
    event(prefix+'/consumer','consumer')
    for f in plan['frames']:
        for child in f['children']:
            p=prefix+f"/f{f['frame']}/s{child['sector']}/reverse"
            event(p+'/route','reverse_route');event(p+'/CDC','reverse_CDC',retained_child_rows=retained,matched_child_required=True)
            retained-=1;event(p+'/metadata','reverse_metadata',retained_child_rows_at_end=retained,matched_CDC_required=True)
    event(prefix+'/allcopy','allcopy',parent_release=True)
    return dict(events=events,peak_retained_children=peak,RF_data_bits_reserved_once=4096,total_ns_assumed=time,whole_program_calendar=False,hardware_qualified=False,eligibility_assumptions='single selected atomic parent, backend/consumer bounded by explicit positive profile',existing_provider_interval_reconcile='replace matching eventID only; never additionally charge an already paid interval')


def model():
    src=inputs();a=json.loads(src['allocator.json']);state=a['allocator_mapping_state_inputs'];cat=catalog()
    need(state['conservative_whole_command_hold_child_rows32SM']==4096 and state['conservative_whole_command_hold_frame_rows32SM']==256,'actual max64 source fragments envelope')
    return dict(schema='NATIVE_FRAME_CONTINUATION_EMITTER_MODEL_R5',programs={k:dict(PCs=v['PCs'],families=v['families'],program_sha256=v['hash']) for k,v in cat.items()},
      source_sha256={k:sha(v) for k,v in src.items()},source_fragment_credit=1,max_fragments_per_parent=64,max_frames_per_parent=8,max_sector_children_per_parent=128,
      frame_rows=256,child_rows=4096,raw_gross_bits=748500,protected_gross_bits=940464,
      FF_plus_planning_protection_only_mm2_ASSUMED=state['conservative_FF_plus_planning_protection_only50pct_mm2'],
      additional_RF_data_bits=0,existing_RF_data_bits_raw=131072,RF_data_reuse='one source-valid512B assembler perSM after exact commonACK; identity records held to parent reverse',
      once_only_ledger=dict(meta92_R14_overlap_debit=None,parent55_W4_overlap_debit=None,net_bits=None,net_area_mm2=None,
       reason='retained8frame metadata outlives reusable W4 ACK; same row/index/ports/lifetime not proved for R14 sidecar; no automatic overlap subtraction'),
      selected_new_ABI=dict(name='continued_fragment_capture_accept',dispatch_seat=1,physical_reverse=False,C0_owner_release=False,
       guard='both sector identities+payload durably captured in reserved frame/child storage',source_original_unchanged=True,source_successor_not_installed=True),
      ports=dict(parent_allocations_per_die_edge=1,parent_requesters=32,allocator_banks=5,counter_bits_each=36,
       child_allocate_updates_per_fragment=2,child_return_updates_per_fragment=2,child_reverse_updates_per_fragment=2,
       proposed_single_metadata_update_port_perSM=True,metadata_allocate_capture_reverse_serialized=True,
       assembler_data_write_bytes_per_fragment=64,assembler_data_write_bytes_per_edge=32,RF_write_bytes_per_frame=512,RF_copies=2),
      required_cost_keys=list(COSTS),required_clock_domains_explicit=True,whole_program_counts='PC inventory only; actual dynamic emitter inputs/home/client map required',
      unsupported=['partial RF word without source-valid preserved join','packed FP8 direct RF deposition','unbound native home byte address','missing actual client/rank/SM/die binding','provider command accepted as WRvisibility','runtime physical reset without allcopy rearm','production SSA/tile/bittypes/home operand view not joined (protocol-control emitter only)'],
      physical_model_gaps=['selector/update/fanout/protection pipeline cell price','source stop/drain CDC predicate implementation','actual source physical routing/slot/load clocks','all program emitted contender composition'],
      build_allowed=False,hardware_admitted=False,whole_token_ns=None)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--verify',action='store_true');args=p.parse_args();raw=canonical(model())
    if args.verify:need((BASE/'model.json').read_bytes()==raw,'exact native frame model replay')
    else:need(args.output is not None,'explicit output');args.output.mkdir(parents=True,exist_ok=True);(args.output/'model.json').write_bytes(raw)
    print('PASS source-pinned emitter/frame envelope; continued-capture successor ABI and physical/calendar admission pending')
if __name__=='__main__':main()
