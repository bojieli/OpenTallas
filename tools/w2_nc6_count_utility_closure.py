#!/usr/bin/env python3
"""Prospective finite count/utility closure; no protected NC6 runtime claim.

Encoded model objects are physical-state candidates. Python collections and
edge labels are test/reference bookkeeping, not implicit hardware registers.
"""
import argparse,hashlib,json,math
from pathlib import Path
import w2_nc6_mutable_protection_model as c
import w2_nc6_protection_reconciliation as r
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/w2_nc6_count_utility_closure_20261003'

class Refusal(Exception):pass

def layout():
    rows=[dict(x) for x in c.layout()]
    for x in rows:
        if x['record']=='outstanding_cache':x['payload_bits']=9 # count5/version4
    def add(name,bits,kind,count):
        for i in range(count):
            remaining=bits
            for j in range(math.ceil(bits/44)):
                n=min(44,remaining);remaining-=n
                rows.append(dict(index=len(rows),record=name,instance=i,chunk=j,payload_bits=n,kind=kind))
    # targetCW72/address10/expectedversion4/delta3/phase3/valid1/tablecount5=98
    add('count_worker',98,7,6)
    # signed pendingdelta3/valid1/overflowfault1=5
    add('count_pending_delta',5,4,6)
    add('offer_epoch',8,4,6) # reserved3/taken3/closed1/valid1
    assert len(rows)==219
    return rows

ROWS=layout()

def ids(name,instance):return [x['index'] for x in ROWS if x['record']==name and x['instance']==instance]

def record(memory,pc,name,instance):
    value=shift=0
    locations=ids(name,instance)
    if not locations:raise Refusal('record-bounds')
    for i in locations:
        x=ROWS[i];p,s,_=c.unseal(memory[i],pc,i,x['kind'],x['payload_bits'])
        if s!='CLEAN':raise Refusal(s)
        value|=p<<shift;shift+=x['payload_bits']
    return value

def write_record(memory,pc,name,instance,value):
    total=sum(ROWS[i]['payload_bits'] for i in ids(name,instance));c.check(value,total)
    for i in ids(name,instance):
        x=ROWS[i];p=value&((1<<x['payload_bits'])-1);value>>=x['payload_bits']
        memory[i]=c.seal(p,pc,i,x['kind'])

def zero_memory(pc):return [c.seal(0,pc,x['index'],x['kind']) for x in ROWS]

def signed3(v):return v-8 if v&4 else v

def table_before_qualifies(current,target,expected_version,role):
    """Compare current decoded44 against journal-derived semantic expectation.

    Target72 + expectedversion4 + static journal role suffice; no missing72-bit
    snapshot register. Old tags in FREE reservation are semantically dead,
    but the current codeword seal/CLEAN check is still required by caller.
    """
    def unpack(p):
        return dict(state=p&3,tag=(p>>2)&((1<<32)-1),gen=(p>>34)&15,
                    direction=(p>>38)&1,version=(p>>39)&15,lock=(p>>43)&1)
    x,y=unpack(current),unpack(target)
    if x['version']!=expected_version or y['lock']:return False
    if role=='issue':
        return x['state']==r.FREE and x['lock']==1 and y['state']==r.ISSUED and y['version']==expected_version
    if any(x[k]!=y[k] for k in ('tag','gen','direction')) or x['lock']:return False
    if role in ('read_held','write_held'):
        direction=int(role=='write_held')
        return x['state']==r.ISSUED and y['state']==(r.WR_HELD if direction else r.RD_HELD) and y['direction']==direction and y['version']==expected_version
    if role in ('read_retire','write_retire'):
        direction=int(role=='write_retire')
        return x['state']==(r.WR_HELD if direction else r.RD_HELD) and y['state']==r.FREE and y['direction']==direction and y['version']==((expected_version+1)&15)
    return False


class Counts:
    """Six independent count writes; no speculative credit from cached count.

    start() happens AFTER the associated table commits become current. New
    output offers for the bank stay suppressed while worker/pending/table debt
    exists. Previously offered outputs can still accept and accumulate delta.
    accepted() labels actual handshakes; table debt outside this class is
    caller-owned and must be supplied to admission_allowed/start.
    """
    def __init__(self,pc=0):
        c.check(pc,7);self.pc=pc;self.memory=zero_memory(pc);self.fault=False

    def normal_gate(self):
        if self.fault:raise Refusal('fault')
        for index,row in enumerate(ROWS):
            _,status,_=c.unseal(self.memory[index],self.pc,index,row['kind'],row['payload_bits'])
            if status!='CLEAN':
                if status!='CE':self.fault=True
                raise Refusal('quarantine' if status=='CE' else status)
        if record(self.memory,self.pc,'sticky_fault',0):
            self.fault=True;raise Refusal('sticky-fault')

    def count(self,client):
        v=record(self.memory,self.pc,'outstanding_cache',client)
        n=v&31
        if n>16:raise Refusal('count-bounds')
        return n,v>>5

    def pending(self,client):
        v=record(self.memory,self.pc,'count_pending_delta',client)
        if v&16:raise Refusal('overflow-latched')
        if not v&8:
            if v&7:raise Refusal('invalid-padding')
            return 0
        return signed3(v&7)

    def accepted(self,client,alloc=0,read_retire=0,write_retire=0):
        if not 0<=client<6 or self.fault:raise Refusal('client/fault')
        self.normal_gate()
        if any(v not in (0,1) for v in (alloc,read_retire,write_retire)) or not any((alloc,read_retire,write_retire)):raise Refusal('event-width')
        delta=alloc-read_retire-write_retire
        # Every previously offered source role is reserved once. No new offer
        # for this bank until old offers/count/table debts drain. Thus the total
        # over a closed offer epoch is [-2,+1], not an unbounded arrival stream.
        value=self.pending(client)+delta
        if not -2<=value<=1:
            self.fault=True;write_record(self.memory,self.pc,'count_pending_delta',client,16)
            raise Refusal('offer-budget-overflow')
        write_record(self.memory,self.pc,'count_pending_delta',client,(value&7)|8)

    def busy(self,client):return bool((record(self.memory,self.pc,'count_worker',client)>>92)&1)

    def start(self,client,table_pending=False):
        self.normal_gate()
        if self.fault or self.busy(client) or table_pending:raise Refusal('busy/table/fault')
        if not record(self.memory,self.pc,'count_pending_delta',client)&8:raise Refusal('no-pending-event')
        delta=self.pending(client);n,version=self.count(client);new=n+delta
        if not 0<=new<=16:
            self.fault=True;raise Refusal('count-over-underflow')
        actual=0
        for row in range(client*16,(client+1)*16):
            payload,status,_=c.unseal(self.memory[row],self.pc,row,0,44)
            if status!='CLEAN':raise Refusal(status)
            actual+=int((payload&3)!=r.FREE)
        if actual!=new:
            self.fault=True;raise Refusal('table-count-conservation')
        index=ids('outstanding_cache',client)[0]
        target=c.seal(new|(((version+1)&15)<<5),self.pc,index,4)
        value=target|(index<<72)|(version<<82)|((delta&7)<<86)|(1<<92)|(actual<<93)
        write_record(self.memory,self.pc,'count_worker',client,value)
        write_record(self.memory,self.pc,'count_pending_delta',client,0)

    def admission_allowed(self,client,table_pending=False,reservation_or_query_live=False):
        try:self.normal_gate()
        except Refusal:return False
        n,_=self.count(client)
        return (not self.fault and not self.busy(client) and self.pending(client)==0 and
                not (record(self.memory,self.pc,'count_pending_delta',client)&8) and
                not table_pending and not reservation_or_query_live and n<16)

    def tick(self):
        if self.fault:return
        try:self.normal_gate()
        except Refusal:return
        writes=[];phases=[]
        try:
            for client in range(6):
                value=record(self.memory,self.pc,'count_worker',client)
                if not ((value>>92)&1):continue
                phase=(value>>89)&7
                if phase>3:raise Refusal('phase-bounds')
                n,version=self.count(client)
                target=value&((1<<72)-1);index=(value>>72)&1023
                expected=(value>>82)&15;delta=signed3((value>>86)&7)
                if index!=ids('outstanding_cache',client)[0] or not -2<=delta<=1:raise Refusal('worker-address/delta')
                new,s,_=c.unseal(target,self.pc,index,4,9)
                if (new&31)!=((value>>93)&31) or s!='CLEAN' or version!=expected or (new>>5)!=((expected+1)&15) or (new&31)!=n+delta or (new&31)>16:
                    raise Refusal('stale-or-malformed-target')
                if phase==3:writes.append((client,index,target))
                else:phases.append((client,(value&~(7<<89))|((phase+1)<<89)))
        except Refusal as error:
            if str(error)!='CE':self.fault=True
            return
        # All six secondary cache targets are qualified before any write. Fault
        # on one member blocks this modeled batch. No primary table port stolen.
        for client,index,target in writes:
            self.memory[index]=target;write_record(self.memory,self.pc,'count_worker',client,0)
        for client,value in phases:write_record(self.memory,self.pc,'count_worker',client,value)



class Offers:
    """Six coded bounded offer epochs; role0=req,role1=read,role2=WR.

    RESERVED means actual output offered and required to hold. TAKEN means
    actual matching ready handshake. Only an unaccepted request can cancel.
    Neither consumer ready nor a dirty count can silently withdraw completion.
    """
    def __init__(self,counts):self.counts=counts;self.memory=counts.memory;self.pc=counts.pc

    def get(self,client):return record(self.memory,self.pc,'offer_epoch',client)

    def reserve(self,client,role,table_pending=False,source_row_eligible=True):
        self.counts.normal_gate()
        c.check(role,2)
        if role>2 or not source_row_eligible or table_pending:raise Refusal('role/table/row')
        n=self.get(client)
        if n&64:raise Refusal('epoch-closed')
        if self.counts.fault or self.counts.busy(client) or record(self.memory,self.pc,'count_pending_delta',client)&8:raise Refusal('count-busy')
        value,_=self.counts.count(client)
        if role==0 and value>=16:raise Refusal('full')
        if n&(1<<role):raise Refusal('duplicate-role')
        write_record(self.memory,self.pc,'offer_epoch',client,n|(1<<role)|128)

    def accept(self,client,roles):
        c.check(roles,3);n=self.get(client)
        if not roles or roles&~n or roles&((n>>3)&7):raise Refusal('unoffered/duplicate')
        self.counts.accepted(client,alloc=int(bool(roles&1)),read_retire=int(bool(roles&2)),write_retire=int(bool(roles&4)))
        write_record(self.memory,self.pc,'offer_epoch',client,n|(roles<<3)|64)

    def cancel_unaccepted_request(self,client):
        self.counts.normal_gate()
        n=self.get(client)
        if not n&1 or n&8:raise Refusal('not-unaccepted-request')
        write_record(self.memory,self.pc,'offer_epoch',client,n&~1)

    def reopen(self,client,table_pending=False,source_copies_drained=False):
        self.counts.normal_gate()
        n=self.get(client)
        if ((n>>3)&7)!=(n&7) or table_pending or not source_copies_drained:raise Refusal('offered/table/copies')
        if self.counts.busy(client) or record(self.memory,self.pc,'count_pending_delta',client)&8:raise Refusal('count-debt')
        self.counts.count(client) # CURRENT cache checked; n==16 can still rearm epoch but no new request admission.
        write_record(self.memory,self.pc,'offer_epoch',client,0)

class Repair:
    """Stateless rescue selection + eight protected 96-bit repair contexts.

    Phase is inside coded context, no unprotected phase/selector register.
    Fixed peer U0/U1 repairs an impaired engine/control context. If both utility
    contexts are nonclean, refuse normal progress and latch model fault; no
    recursive unpriced repair controller. fault is an oracle verdict here;
    actual sticky storage is the existing protected sticky_fault word.
    """
    def __init__(self,pc=0):
        self.pc=c.check(pc,7);self.memory=zero_memory(pc);self.fault=False

    def get(self,engine):return record(self.memory,self.pc,'correction_context',engine)

    def engine_clean(self,engine):
        try:self.get(engine);return True
        except Refusal:return False

    def idle(self,engine):return self.engine_clean(engine) and not self.get(engine)>>95

    def load(self,engine,index):
        if index in ids('correction_context',engine):raise Refusal('self-repair')
        if self.fault or not self.idle(engine):raise Refusal('engine-busy/fault')
        for other in range(8):
            if self.engine_clean(other):
                active=self.get(other)
                if active>>95 and ((active>>72)&1023)==index:raise Refusal('target-already-owned')
        row=ROWS[index];raw=self.memory[index]
        _,status,fixed=c.unseal(raw,self.pc,index,row['kind'],row['payload_bits'])
        if status!='CE':raise Refusal('not-correctable')
        syn,odd=c.syndrome(raw)
        # Candidate is rederived from original at commit; no unpriced72-bit
        # corrected-output register. Engine field: original72/address10/
        # syndrome7/overall1/phase3/status2/valid1.
        value=raw|(index<<72)|(syn<<82)|(odd<<89)|(1<<95)
        write_record(self.memory,self.pc,'correction_context',engine,value)

    def rescue(self):
        if self.fault:return False
        if not self.engine_clean(6) and not self.engine_clean(7):
            self.fault=True;return False
        # Actual current-codeword classification supplies this combinational
        # hard priority; no corrupt scheduler word or mutable selector consumed.
        impaired=[]
        for index,row in enumerate(ROWS):
            _,status,_=c.unseal(self.memory[index],self.pc,index,row['kind'],row['payload_bits'])
            if status in ('DUE','LOCATION_FAULT','PADDING_FAULT'):
                self.fault=True;return False
            if status=='CE':impaired.append(index)
        impaired.sort(key=lambda i:(ROWS[i]['record']!='correction_context',i))
        if any(ROWS[i]['record']=='correction_context' for i in impaired):
            impaired=[i for i in impaired if ROWS[i]['record']=='correction_context']
        for index in impaired:
            row=ROWS[index]
            if row['record']=='correction_context':
                owner=row['instance']
                peers=[7] if owner==6 else [6] if owner==7 else [6,7]
            elif row['record']=='table':peers=[index//16,6,7]
            else:peers=[6,7]
            for peer in peers:
                if self.idle(peer):
                    try:self.load(peer,index);return True
                    except Refusal:continue
        return False

    def tick(self):
        if self.fault:return
        for index,row in enumerate(ROWS):
            _,status,_=c.unseal(self.memory[index],self.pc,index,row['kind'],row['payload_bits'])
            if status in ('DUE','LOCATION_FAULT','PADDING_FAULT'):
                self.fault=True;return
        if not self.engine_clean(6) and not self.engine_clean(7):
            self.fault=True;return
        # Clean engines progress independently of an impaired global scheduler.
        # This rescue-only bypass uses fixed decode of their own coded phases.
        actions=[]
        for engine in range(8):
            if not self.engine_clean(engine):continue
            value=self.get(engine)
            if not value>>95:continue
            phase=(value>>90)&7;status=(value>>93)&3
            original=value&((1<<72)-1);index=(value>>72)&1023
            if index>=len(ROWS) or phase>3 or status!=0:
                self.fault=True;return
            syn,odd=c.syndrome(original)
            if ((value>>82)&127)!=syn or ((value>>89)&1)!=odd:
                self.fault=True;return
            row=ROWS[index];_,s,fixed=c.unseal(original,self.pc,index,row['kind'],row['payload_bits'])
            if s!='CE' or self.memory[index]!=original:
                self.fault=True;return
            # Context payload checked CURRENT on every progress edge. Dirty
            # utility contexts never drive target/address, including last edge.
            if phase==3:actions.append(('scrub',engine,index,fixed))
            else:actions.append(('phase',engine,0,(value&~(7<<90))|((phase+1)<<90)))
        # Two engines may not mutate the same target. Duplicate rescue must be
        # excluded before load; this final assertion is an independent check.
        targets=[a[2] for a in actions if a[0]=='scrub']
        if len(targets)!=len(set(targets)):self.fault=True;return
        for op,engine,index,v in actions:
            if op=='scrub':
                self.memory[index]=v
                if ROWS[index]['record']=='correction_context':
                    owner=ROWS[index]['instance']
                    try:restored=self.get(owner)
                    except Refusal:self.fault=True;return
                    # Restore corrupted stored inputs, then restart the four
                    # quiet-edge hold interval. No new restart flag/register.
                    restored&=~(7<<90)
                    write_record(self.memory,self.pc,'correction_context',owner,restored)
                if ROWS[index]['record'] in ('count_worker','outstanding_cache'):
                    client=ROWS[index]['instance']
                    try:worker=record(self.memory,self.pc,'count_worker',client)
                    except Refusal:self.fault=True;return
                    if (worker>>92)&1:
                        write_record(self.memory,self.pc,'count_worker',client,worker&~(7<<89))
                write_record(self.memory,self.pc,'correction_context',engine,0)
            else:write_record(self.memory,self.pc,'correction_context',engine,v)


def price(rows):
    old=c.model();facts=json.loads((c.D/'inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json').read_text())['facts']
    A=lambda n:facts[n]['SS']['area_um2'];N='NAND2x1_ASAP7_75t_R';B='BUFx4_ASAP7_75t_R';F='DFFASRHQNx1_ASAP7_75t_R';I='INVx1_ASAP7_75t_R'
    def counts(rs):
        enc=0
        for row in rs:
            ns=[sum(bool(p&(1<<i)) for p in c.POSITIONS[:row['payload_bits']]) for i in range(7)]
            enc+=sum(max(0,n-1) for n in ns)+max(0,row['payload_bits']+sum(n>0 for n in ns)-1)
        clean=len(rs)*(sum(m.bit_count()-1 for m in c.MASKS)+71)
        return enc,clean
    e,k=counts(rows);oe,ok=counts(c.layout());bits=len(rows)*72;added=bits-13608
    # Secondary6 count5-bit folded adders, address/version/target guards;
    # combin rescue priority over213 words and eight fixed contexts. Budgets
    # explicitly prospective, no mapped-area or SS/FF guarantee.
    adders=6*5*9;guards=6*(72*4+10*4+4*4+32);rescue=len(rows)*16+8*96+6*64
    # One-hot FF D-input router includes HOLD; ASR DFF has no native enable.
    # Each AND2=2NAND2, each OR2=3NAND2, explicit balanced construction.
    # Table destinations:3 global normal+1 local WR retire+1 bankrepair+2
    # utilityrepair. Other records budget3 normal+2 utility mutators.
    table_sources=8;other_sources=6
    def mux_nands(n):return 2*n+3*(n-1)
    router_nands=96*72*(mux_nands(table_sources)-3)+(len(rows)-96)*72*(mux_nands(other_sources)-3)
    # Static onehot destination/address enables, and buffered data/source selects.
    route_enable_nands=(3*96+6*16+6*16+2*len(rows))*10*4
    route_buffers=math.ceil((2*len(rows)*72+6*16*72)/8)
    logic_router_area=route_buffers*A(B)
    logic=adders+guards+rescue+router_nands+route_enable_nands
    tree=lambda n:sum(math.ceil(n/(8**i)) for i in range(1,1+math.ceil(math.log(max(2,n),8))))
    tree_extra=2*(tree(bits)-tree(13608))*A(B)
    per_bit=A(F)+2*A(I)+3*A(N)+2*A(B)+.04374
    body=old['cell_price']['gross_body_mm2_perPC_ASSUMED']+(added*per_bit+(4*(e+k-oe-ok)+logic)*A(N)+tree_extra+logic_router_area)/1e6
    return dict(protected_bits=bits,delta_bits=added,encoder_XOR2=e,clean_XOR2=k,
                extra_secondary_guard_rescue_NAND2_budget=logic,body_mm2_perPC_ASSUMED=body,
                gross128PC_50pct_mm2_ASSUMED=body*256,net_F0_replacement_unknown=True,
                loaded_and_mapped=False,
                extra_CLK_RESET_tree_area_um2_ASSUMED=tree_extra,
                clock_SS_fF=bits*facts[F]['SS']['pins']['CLK']['cap_fF'],
                FF_write_router=dict(table_input_sources_including_hold=table_sources,other_input_sources_including_hold=other_sources,
                    extra_NAND2=router_nands,enable_decode_NAND2_budget=route_enable_nands,
                    buffers_x4_budget=route_buffers,maximum_table_data_fanin=7,
                    table_dynamic_destinations=672,utility_word_destinations=2*len(rows),
                    corrector_to_target_boundary_bits=8*(72+10),no_arbitrary_extra_FIFO=True),
                reset_byPC={str(pc):dict(SETN_bits=sum(c.seal(0,pc,x['index'],x['kind']).bit_count() for x in rows),
                    physical_bits=bits) for pc in range(128)})


def model():
    antecedent=r.model();rows=layout();bits=len(rows)*72
    return dict(schema='w2.nc6.count-utility-prospective.v1',source_sha256=antecedent['source_sha256'],
        antecedent='22ec32816e4920307b222e93f4d91c3d049d5780',geometry=antecedent['selected_geometry'],
        storage=dict(words=len(rows),bits_perPC=bits,delta_vs13608=bits-13608,layout=rows,
            count_workers=6,count_worker_payload_bits=98,count_delta_words=6,
            count_cache_count5_version4=True,offer_epoch_words=6,offer_epoch_payload_bits=8,unprotected_mutable_registers_allowed=0),
        ports=dict(primary_table_writers=9,secondary_count_writers=6,
            maximum_primary_plus_count_writes=15,count_worker_load_words=18,
            table_writer_roles='1request,1read(held transition OR retirement),1WRmatch,6WRretire; old rdv makes read branches mutually exclusive',
            pending_delta_writers=6,offer_epoch_writers=6,correction_engines=8,correction_phase_writers=8,
            context_load_words_each=3,context_repair_extra_phase_write_max=1,rescue_selection='stateless current-check fixed priority; no unpriced FF selector',
            physical_implementation='independent FF record updates, not imaginary multiport SRAM',
            loaded_reset_clock_fanout_and_Wmux_SSFF_unknown=True),
        count=dict(fold='allocation1-readretire1-writeretire1 perclient; simultaneous fold, not last NBA assignment',
            offer_epoch='no new offers to bank until table/count debts and old offers drain; previously held outputs may accept',
            signed_pending_range=[-2,1],out_of_budget='stickyfault; no wrapping accumulator',
            start='table commits visible; count5+fold must equal CURRENT sealed16-row nonFREE census; capture tablecount5 in protected worker, no existing count worker',
            completion='four quiet/current-clean edges; cache target version and delta reconstructed old count match',
            table_journal_snapshot='target72+expectedversion4+static role reconstructs semantic before state; no hidden before72 register; FREE old tag is dead but current codeword integrity still checked',
            credit='derived cache + actual table/reservation/journal/held-copy checks; no count-only admission',
            popcount_path='six local16-row two-bit-state nonFREE reductions, integer5 count; current word check plus popcount plus encode/load is explicit prospective loaded path',
            offer_controller='six coded8bit epochs: reserved3/taken3/closed1/valid1; first handshake closes new offers, old reserved outputs stay held; reopen requires all roles taken/canceled and count/table/copies drained',
            local_count_version_wrap='old worker and pending dependencies drained before next worker; old sourcegen4 quiescence unchanged',
            return_early_clean=False),
        utility=dict(context='coded original72/address10/syndrome7/overall1/phase3/status2/valid1',
            no_corrected_candidate_register=True,phase_path='only own coded phase word updates; original remains stable',
            scheduler_CE='stateless rescue bypass; normal ownership interfaces quarantined',
            impaired_utility='other clean utility repairs context; busy peer drains its clean task first',
            both_utilities_impaired='failclosed; no universal multifault forward-progress guarantee',
            quiet_single_CE_scrub_edges=4,peer_busy_extra_edges_max=4,
            normal_admission_and_irreversible_release_during_CE=False,
            interrupted_context='repair targetword and coded phase reset before original task resumes; four fresh clean edges mandatory',
            duplicate_target='all clean active contexts exclude duplicate loads; dirty context rescue precedes new ordinary tasks',
            target_immutability='match original raw codeword and address at final edge or fault',
            hardware_current_clean_fanout_not_closed=True),
        price=price(rows),loaded_paths=dict(
            target_period_ps=833.333333,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
            current_clean_gate='219 codeword syndrome/seal/padding reductions, global quarantine tree and actual ready/valid/output enable loads; source check may not use cached syndrome',
            count_capture='six16row current-check/nonFREE/popcount paths plus signed fold, expectedtablecount and encoded worker capture; no claimed one-edge SS closure',
            pending_delta='CURRENT protected3bit accumulator, three accepted-role fold, encoded5bit update and held-output guard',
            secondary_commit='CURRENT target/version/cache/seal checks through six independent72bit FF update paths',
            utility='coded context phases, stateless priority, fixed peer rescue, original72bit stable hold and target/phase feedback; no unprotected selector',
            router='table7-source/other5-source onehot mutators plus hold; actual address and control fanout/load, fastest feedback FF hold',
            reset='all219 words retain static seal/padding FFs; encoded SETN/RESETN and CLK tree, no allzero-reset shortcut',
            sensitivity='each extra loaded count stage adds one edge to countdrain and sameclient eligibility; request-side retiming separately adds to next backend acceptance; not measured clock proof',
            qualified=False),calendar=dict(antecedent_min_request_read_write=[8,8,9],
            count_commit_edges=4,sameclient_backend_accept_II_min_quiet=18,global_lookup_II=8,
            reason='accept0/tablecommit4/countstart5/countcommit9/newcapture10/requestaccept18; no earlier sameclient source offer',
            quiet_single_closed_offer_count_drain_upper_edges=9,
            drain_bound_scope='all already offered consumers accepted by edge0; active count worker and last table journal finish<=4, successor starts5/commits9; quiet nofault edges, held ready refusal unbounded',
            consumer_retire_new_reservation_min_edges=10,
            minimum_clean_gate='all219 CURRENT codewords/seals/padding and sticky state; CE quarantines normal handshakes even if consumer ready',
            sourceclock_period_ps=833.333333,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
            measured_latency=False),
        readiness=dict(full_NC6_RTL=False,reason='count/utility/offer semantic model closed; actual ready-valid port enrollment and loaded cuts still required',
            component_control_semantics_closed=True,functional_RTL_preparation_ready=True,
            remaining=['actual protected NC6 enrollment binding of offer/table journal records to ready/valid ports',
                'exceptional held-valid quarantine enrollment and current clean loaded SS/FF cuts'],
            codec_runtime_owned_by_parent=True,no_physical_launch=True,
            next_action='prepare full defaultoff NC6 source binding using219 sealed records, count/table journal ports, fixed utility rescue and coded offer epochs; retain required p_wr_done_ready plus explicit repair_busy contract',
            forbidden='no reuse of9144/13608bit old cost, no free secondary ports, no use of parent codec runtime as fullNC6 or SSFF proof'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    t=json.dumps(model(),sort_keys=True,indent=2)+'\n'
    if a.output:a.output.write_text(t)
    else:print(t,end='')
