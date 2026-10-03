#!/usr/bin/env python3
"""One finite full-shape component construction before default-off parent RTL.
Pure source/boolean/metadata; no golden payload, RTL compiler or P&R launcher.
Old models/failures remain immutable. All timing is a bounded construction screen.
"""
import argparse,collections,hashlib,json,math,gzip,random,re
from pathlib import Path
from fractions import Fraction
import dsrom_field_bridge_parent as P
import dsrom_field_bridge_queue_bounds as Q
import dsrom_capture_home as H
import dsrom_I66_capture_cells as C
import dsrom_I66_capture_timing as T
ROOT=P.ROOT;OUT=ROOT/'results/uarch/dsrom_field_parent_component_20261003'
POLY=0x82f63b78

def crc_step(state,data,bits=256):
    for j in range(bits):
        fb=(state^(data>>j))&1;state>>=1
        if fb:state^=POLY
    return state

def crc_matrix():
    # Exact GF(2) linear map:32 input state bits then256 data bits.
    cols=[crc_step(1<<j,0) for j in range(32)]+[crc_step(0,1<<j) for j in range(256)]
    return [sum(((v>>o)&1)<<i for i,v in enumerate(cols)) for o in range(32)]

def parity_balanced(x):
    bits=[(x>>i)&1 for i in range(x.bit_length())]
    if not bits:return 0
    while len(bits)>1:bits=[bits[i]^(bits[i+1] if i+1<len(bits) else 0) for i in range(0,len(bits),2)]
    return bits[0]

def crc_linear(state,data,matrix):
    packed=state|(data<<32)
    return sum(parity_balanced(packed&r)<<o for o,r in enumerate(matrix))

def crc_proof(matrix):
    receipts=[]
    for basename in ('ot_stage_link_tx.sv','ot_stage_link_rx.sv'):
        path=ROOT/'rtl'/basename;text=path.read_text()
        for fn,last,init in [('crc32c_flit',"c^32'hffffffff", "c=32'hffffffff"),('crc32c_extend','c','c=state_in')]:
            body=re.search(r'function automatic \[31:0\] '+fn+r';(.*?)endfunction',text,re.S)
            if not body:raise ValueError('native CRC function missing')
            compact=re.sub(r'\s+','',body[1])
            for token in (init+';', 'by<FLIT_W/8','bi<8','fb=c[0]^d[by*8+bi];','c=c>>1;',"if(fb)c=c^32'h82f63b78;",fn+'='+last+';'):
                if token not in compact:raise ValueError('native CRC operation changed '+token)
        receipts.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    tests=[(0,0),(0xffffffff,0),(0xffffffff,(1<<256)-1)]
    tests += [(1<<i,0) for i in range(32)]+[(0,1<<i) for i in range(256)]
    rng=random.Random(4096)
    tests += [(rng.getrandbits(32),rng.getrandbits(256)) for _ in range(512)]
    for state,data in tests:
        if crc_step(state,data)!=crc_linear(state,data,matrix):raise ValueError('source CRC linear proof')
    return {'linear_basis_vectors':288,'additional_directed_random_vectors':515,'PASS':True,'native_function_receipts':receipts,
            'source_initial_and_final_XOR':'ffffffff as in native flit function; packetextend uses previous unfinalized state',
            'no_FP_rounding_or_golden_payload_changed':True}

def crc_construction(matrix):
    lengths=[r.bit_count() for r in matrix];levels=[]
    while max(lengths)>1:
        levels.append({'registered_outputs':sum((n+1)//2 for n in lengths),'XOR2':sum(n//2 for n in lengths),'maximum_terms_next':max((n+1)//2 for n in lengths)})
        lengths=[(n+1)//2 for n in lengths]
    fanouts=[sum(bool(r&(1<<i)) for r in matrix) for i in range(288)]
    clones=sum((n+7)//8 for n in fanouts)
    # Four full engines PER DIE:TXflit/TXextend/RXflit/RXextend. Both
    #duplexdirections carry generation-qualified control, not just ACK8. Independent and state
    # engines run in parallel; packet state depends on prior terminal =>II11.
    nreg=clones+sum(l['registered_outputs'] for l in levels)+32
    return {'engines':8,'matrix_hex':[hex(r) for r in matrix], 'balanced_registered_levels':levels,
            'leaf_capture_edge':1,'XOR_levels':len(levels),'terminal_capture_edge':1,
            'accepted_to_terminal_cycles':len(levels)+2,'ordered_packet_extend_II':len(levels)+3,
            'total_data_FF':8*nreg,'total_valid_ASR':8*(len(levels)+2),
            'total_XOR2':8*sum(l['XOR2'] for l in levels),'NAND2_per_XOR2':4,
            'leaf_clone_FF_total':8*clones,'input_use_max_fanout':max(fanouts),
            'leaf_clone_output_fanout_ceiling':8,'extra_BUF_for_leaf_clones':8*clones*12,
            'TXstored_flitCRC32_bits':256*32,'RXstored_expected_flitCRC32_bits':256*32,
            'RX_quarantine':'Capture full reserved256-flit packet at wire rate; validate stored flit+packet CRC before delivery. Original packetbuffer charged. No speculative VM write.',
            'wrong_seq_duplicate_generation':'reject without publishing or freeing matching immutable phase/packet debt',
            'packet_state_feedback_not_II1':True}

class Sequencer:
    STATES=('RESET','IDLE','RESERVE','CFG','GO','DRAIN','RETIRE','FAULT')
    def __init__(self):self.state='RESET';self.ctx=None;self.count=0;self.credits=set();self.visible=set();self.era=-1;self.versions={}
    def reset_release(self,era,peer_era,quiescent):
        if self.ctx is not None or self.versions or self.state not in ('RESET','IDLE') or not quiescent or era!=peer_era or era<=self.era or not 0<=era<2**32:raise ValueError('reset cannot erase old accepted debt or alias era')
        self.era=era;self.state='IDLE'
    def reserve(self,ctx,nrow,shard_acks,writer_drains,tree_empty,version_slot):
        if self.state!='IDLE' or self.ctx is not None:raise ValueError('source phase overlap forbidden')
        widths=(6,2,9,10,32,32,32,32,14)
        if not 1<=nrow<=8192 or len(ctx)!=9 or any(type(x)is not int or not 0<=x<2**w for x,w in zip(ctx,widths)):raise ValueError('full169 context/range')
        if ctx[0]>=58 or ctx[2]>=384:raise ValueError('S58 and384 expert owner bounds')
        if shard_acks!=[(tuple(ctx),self.era,0),(tuple(ctx),self.era,1)]:raise ValueError('matched two-shard reservations')
        if len(writer_drains)!=12 or not all(writer_drains) or not tree_empty:raise ValueError('ready is not native drain')
        if version_slot in self.versions or len(self.versions)>=32:raise ValueError('finite VMversion registry')
        self.ctx=tuple(ctx);self.count=nrow;self.credits=set();self.visible=set();self.state='RESERVE';self.versions[version_slot]={'ctx':self.ctx,'visible':False,'last_read':None}
    def cfg_accept(self,ctx,last25_captured):
        if self.state!='RESERVE' or tuple(ctx)!=self.ctx or not last25_captured:raise ValueError('matched accepted config fence')
        self.state='CFG'
    def launch(self,ctx,stream_loader_owner):
        if self.state!='CFG' or tuple(ctx)!=self.ctx or stream_loader_owner!=self.ctx:raise ValueError('GO requires immutable cfg/activation owner')
        self.state='GO'
    def publish(self,ctx,row,postNBA,exclusive,crc_good):
        if self.state not in ('GO','DRAIN') or tuple(ctx)!=self.ctx or row in self.visible or not 0<=row<self.count or not postNBA or not exclusive or not crc_good:raise ValueError('no accept-as-visible/duplicate/unchecked publication')
        self.state='DRAIN';self.visible.add(row)
    def credit(self,ctx,row,visible_edge,return_edge):
        if tuple(ctx)!=self.ctx or row not in self.visible or row in self.credits or return_edge<=visible_edge:raise ValueError('matched positive credit')
        self.credits.add(row)
    def retire(self,ctx,quiet_gen,all_pair_node_root_empty,read_tokens,packets,cdc_debts):
        if self.state!='DRAIN' or tuple(ctx)!=self.ctx or quiet_gen!=self.ctx[5] or not all_pair_node_root_empty or read_tokens or packets or cdc_debts or len(self.visible)!=self.count or len(self.credits)!=self.count:raise ValueError('matched credit AND actual drain required')
        for v in self.versions.values():
            if v['ctx']==self.ctx:v['visible']=True
        self.ctx=None;self.state='IDLE'
    def su_read(self,slot,ctx,edge):
        v=self.versions[slot]
        if v['ctx']!=tuple(ctx) or not v['visible']:raise ValueError('no old/hidden VMversion read')
        v['last_read']=edge
    def su_tag_retire(self,slot,ctx,read_edge,tag_edge,drain):
        v=self.versions[slot]
        if v['ctx']!=tuple(ctx) or v['last_read']!=read_edge or tag_edge!=read_edge+2 or not drain:raise ValueError('VM lease release only matching native R+2 and drain')
        del self.versions[slot]

class VMGrantBatch:
    """Prospective finite backend, preserving the literal native batch order.

    Inputs are EXPANDED scalar addresses after mask/bank expansion. Source
    request ordering is supplied by Arch's literal family and lane census.
    This is not a physical SRAM or an existing granted port.
    """
    def __init__(self, image, reads, writes, ctx, era, publication_ids=(),
                 compiler_exclusions=False, response_cycles=None, grant_interval=None):
        if not compiler_exclusions:raise ValueError('compiler bank/mask/address exclusions required')
        if response_cycles is None or grant_interval is None or response_cycles<1 or grant_interval<1:raise ValueError('positive finite native provider service required')
        self.ctx=tuple(ctx);self.era=era;self.response=response_cycles;self.interval=grant_interval
        self.reads=list(reads);self.writes=list(writes);self.initial=dict(image);self.image=dict(image)
        self.read_values={};self.committed=set();self.visible={};self.superseded=set();self.events=[]
        self.publication=set(publication_ids);self.pending_reads=collections.defaultdict(list);self.pending_writes=collections.defaultdict(list)
        ids=set()
        for rid,addr in self.reads:
            if rid in ids or not 0<=addr<2**19 or addr not in self.initial:raise ValueError('read duplicate, expanded AW19 alias or missing source image')
            ids.add(rid);self.pending_reads[addr%32].append((rid,addr))
        ids=set();winner={};last_order=(-1,-1)
        for wid,family,lane,addr,value in self.writes:
            if wid in ids or not 0<=family<12 or lane<0 or not 0<=addr<2**19 or not 0<=value<2**32:raise ValueError('write identity/mask expansion bounds')
            ids.add(wid)
            key=(family,lane)
            if key<last_order:raise ValueError('literal global family and lane order required')
            last_order=key
            if addr in winner and winner[addr][0]>=key:raise ValueError('literal family then lane order required')
            winner[addr]=(key,wid)
        winners={v[1] for v in winner.values()}
        self.superseded=ids-winners
        if self.publication & self.superseded:raise ValueError('superseded publication cannot get visible ACK, even equal data')
        for w in self.writes:
            if w[0] in winners:self.pending_writes[w[3]%32].append(w)
        self.read_debt=len(self.reads);self.write_debt=len(winners);self.phase='READ_SNAPSHOT'
        self.ready_responses=[];self.ready_visible=[];self.last_edge=-1;self.closed=False
    def step(self,edge,ctx,era):
        if self.closed or edge!=self.last_edge+1 or tuple(ctx)!=self.ctx or era!=self.era:raise ValueError('same owner, era and consecutive provider edges required')
        self.last_edge=edge
        # Receipts are captured on a later edge, never on the write grant.
        for due,rid,val in list(self.ready_responses):
            if due==edge:self.read_values[rid]=val;self.read_debt-=1;self.ready_responses.remove((due,rid,val));self.events.append((edge,'read_response',rid))
        for due,wid,addr,val in list(self.ready_visible):
            if due==edge:
                if self.image.get(addr)!=val:raise ValueError('winner post-edge image mismatch')
                self.visible[wid]=edge;self.write_debt-=1;self.ready_visible.remove((due,wid,addr,val));self.events.append((edge,'visible',wid))
        if self.phase=='READ_SNAPSHOT' and not self.read_debt:self.phase='WINNER_WRITES'
        if edge%self.interval==0:
            if self.phase=='READ_SNAPSHOT':
                for bank,q in self.pending_reads.items():
                    if q:
                        rid,addr=q.pop(0);self.ready_responses.append((edge+self.response,rid,self.initial.get(addr,0)));self.events.append((edge,'read_grant',rid))
            elif self.phase=='WINNER_WRITES':
                for bank,q in self.pending_writes.items():
                    if q:
                        wid,f,l,addr,val=q.pop(0);self.image[addr]=val;self.committed.add(wid);self.ready_visible.append((edge+1,wid,addr,val));self.events.append((edge,'write_grant',wid))
        if self.phase=='WINNER_WRITES' and not self.write_debt:self.closed=True
        return self.closed

def vm_contract():
    raw=(OUT/'inputs/split_VM_6b8f3affa.json').read_bytes();src=json.loads(raw)
    return {'source_receipt':json.loads((OUT/'inputs/split_VM_origin.json').read_text()),
      'read_image':src['source_semantics']['read_image'],'write_image':src['source_semantics']['write_image'],
      'five_unit_mask_not_barrier':True,'source_port_envelope':src['demand_envelope'],
      'native_source_VM_capacity_bits':src['capacity']['bits'],
      'proposed_backend':{'banks':32,'words_per_bank':16384,'word_bits':32,'bank':'expanded_address[4:0]','bank_row':'expanded_address[18:5]',
       'read_grants_per_bank_per_service_edge':1,'write_grants_per_bank_per_service_edge':1,
       'batch':'Snapshot ALL accepted logical-batch reads before any batch winner write. Per-bank serial service; literal last writer/lane wins. Do not coalesce separate accepted batches.',
       'request_response_cycles':None,'maximum_grant_interval':None,'actual_macro_abstract':None,'physical_home':None,
       'publication':'Only surviving native source winner, post-NBA image and same full owner/era. Superseded writes have semantic retirement but ZERO visible ACK.',
       'compiler_required':'Expanded AW19 bounds, full byte/lane masks, exact intended-alias and read-version/batch exclusions, finite nonstall preload/result reservations BEFORE dispatch.',
       'SRAM_protection':'Existing SRAM reliability contract retained; no ROM-ECC removal applied to VM.',
       'fixed_capacity_not_extra_payload_credit':True},
      'finite_service_inequalities':{'worst_unproved_single_bank_read_demand':1520,'worst_unproved_single_bank_write_demand':593,
       'source_envelope_not_actual_concurrency':True,
       'batch_upper_if_G_and_L_proved':'1520*G + L + 593*G + 1 positive visible receipt edge, plus launch/CDC/queue; compiler census may lower only with bank/mask exclusion proof',
       'single_publication_lower':'one actual bank write grant, then strictly later post-NBA visible receipt, then positive captured full-owner credit'},
      'backend_model_reference_tests_not_physical_grants':True,'native_VM_grant_admission':False}

def electrical_screen():
    # One registered local mux / CRC XOR level; no old global selector path.
    # All cell-load/slew values remain conditional LUT bounds, not extracted nets.
    data={}; ss=T.library()['SS'];rc=T.RC()
    def path(nands, fork=False):
        elapsed=0.;slew=320.;trace=[]
        def cell(master,cap,sink,role):
            nonlocal elapsed,slew
            if cap<=sink or cap>ss[master]['pins']['QN' if master in (C.HQ,C.ASR) else 'Y']['max_cap_fF']:raise ValueError('nonpositive wire or maxcap')
            arc=ss[master]['tables']
            delay=max(T.upper(t,slew,cap) for k,t in arc if k.startswith('cell_'))
            trans=max(T.upper(t,slew,cap) for k,t in arc if k.endswith('transition'))
            length=(cap-sink)/rc['C_fF_per_um'];wire=(length*rc['R_kohm_per_um']+rc['two_via_R_kohm'])*cap
            elapsed+=delay+wire;out=trans+2.2*wire
            trace.append({'master':master,'role':role,'input_slew_ps':slew,'load_fF':cap,'sink_fF':sink,'positive_wire_ceiling_um':length,'wire_delay_upper_ps':wire,'cell_delay_upper_ps':delay,'output_slew_upper_ps':out})
            if out>320:raise ValueError('slew ceiling')
            slew=max(5.,out)
        inv=ss[C.INV]['pins']['A']['cap_fF'];buf=ss[C.BUF]['pins']['A']['cap_fF']
        nand=max(ss[C.NAND]['pins'][p]['cap_fF'] for p in ('A','B'))
        dest=max(ss[n]['pins']['D']['cap_fF'] for n in (C.HQ,C.ASR))
        cell(C.HQ,1.44,inv,'QN capture')
        cell(C.INV,1.44,buf,'polarity restore')
        for j in range(3):cell(C.BUF,2.88,nand if j==2 else buf,'typed forward hold repair '+str(j))
        for j in range(nands):cell(C.NAND,2.88 if fork and j==0 else 1.44,dest if j==nands-1 else nand*(2 if fork and j==0 else 1),'registered cone and feedback mux '+str(j))
        setup=max(T.upper(t,slew,320) for n in (C.HQ,C.ASR) for _,t in ss[n]['setup'])
        total=elapsed+setup+60+25
        return {'steps':trace,'path_and_constraints_ps':total,'period_ps':1000/1.2,'remaining_ps':1000/1.2-total,'conditional_setup_screen_PASS':total<=1000/1.2,'physical_routes_proven':False}
    for name,n in [('reader_mux_and_hold_mux',4),('CRC_XOR_and_hold_mux',5)]:data[name]=path(n,name.startswith('CRC'))
    lib=T.library()['FF']
    def minimum_delay(master):return min(T.minimum(t) for k,t in lib[master]['tables'] if k.startswith('cell_'))
    holds={}
    for ff in (C.HQ,C.ASR):
        hold=max(max(v for r in t['values'] for v in r) for _,t in lib[ff]['hold'])
        base=minimum_delay(ff)+minimum_delay(C.INV)
        holds[ff]={'same_flop_feedback_two_BUF_margin_ps':base+2*minimum_delay(C.NAND)+2*minimum_delay(C.BUF)-hold-50,
         'direct_forward_three_BUF_margin_ps':base+3*minimum_delay(C.BUF)-hold-50,'only_characterized_minimum_screen':True}
    facts,_=C.facts();rc=T.RC();clkcap=max(facts[n]['FF']['pins']['CLK']['cap_fF'] for n in (C.HQ,C.ASR))
    bufcap=facts[C.BUF]['FF']['pins']['A']['cap_fF']
    return {'registered_local_data_paths':data,'typed_minimum_hold':holds,
      'three_forward_BUF_SS_delay_included':True,
      'local_branch_clock':{'four_sink_pin_load_fF':4*clkcap,'raw_bit_pitch_with_forward_BUFFERS_um':4.104,
       'four_sink_span_um':18.36,'conservative_wire_cap_fF':18.36*rc['C_fF_per_um'],
       'upper_eight_BUF_pin_load_fF':8*bufcap,'declared_total_load_ceiling_fF':5.76,
       'upper_branch_wire_length_ceiling_um':(5.76-8*bufcap)/rc['C_fF_per_um'],
       'parent_roots_relays_vias_reset_release_and_skew_not_constructed':True},
      'SS_setup_closed':False,'FF_hold_closed':False,'registered13_edge_reader_admitted':False}

def sections(crc):
    # Same counts on both physical shard dies; each receives full own source rows.
    f,_=C.facts();out={}
    def add(sec,master,n):out.setdefault(sec,collections.Counter())[master]+=int(n)
    HQ,ASR,NAND,INV,BUF=C.HQ,C.ASR,C.NAND,C.INV,C.BUF
    def storage(sec,data,ctrl,forward=True):
        add(sec,HQ,data);add(sec,ASR,ctrl);bits=data+ctrl
        add(sec,INV,bits);add(sec,NAND,bits*3);add(sec,BUF,bits*(2+(3 if forward else 0)))
        add(sec,'TIEHIx1_ASAP7_75t_R',ctrl)
    #4096raw69/64banks per shard; sourcevalid is part of raw record, seatvalid separate.
    storage('raw4096',4096*69,4096)
    #All4095mux-tree nodes registered, raw69+row16+seq16+valid1=102.
    storage('reader12levels',4095*101,4095);add('reader12levels',NAND,4095*69*3);add('reader12levels',BUF,4095*12)
    storage('read_token16_and_fifo',16*101,16);add('read_token16_and_fifo',NAND,16*16*6)
    #32finite interval versions:169ctx +base30+length19+state3+seq16+readdebt20=257.
    storage('VMversion_guard32',0,32*257);add('VMversion_guard32',NAND,32*(2*19*6+169*5+20*9))
    #12writers fenced at admission; all sourcewe suppressed exceptownedslot0.
    storage('VMformatter_guard',32+30,128);add('VMformatter_guard',NAND,32*3+12*30+32*2+30*2+30*19*5)
    add('VMformatter_guard',BUF,(12*32+128)*12)
    storage('codec_header',512+263+64,128);add('codec_header',NAND,201*5+263*3)
    storage('CRC4engines',crc['total_data_FF']//2,crc['total_valid_ASR']//2)
    add('CRC4engines',NAND,crc['total_XOR2']*4//2);add('CRC4engines',BUF,crc['extra_BUF_for_leaf_clones']//2)
    storage('CRC_metadata_memory',2*256*32,0)
    #Existing full data packet memories conservatively retained once; do not use
    #prior unspecified provider debit as proof of contained native memory.
    storage('packet_memory_existing_provider_obligation',2*256*256,0)
    #Two16-entry full-identity mailboxes:owner169+era32+row16+nonce16+shard1+op4=238.
    storage('CDC16x2',16*2*238,16*2*2+4*32+2*3+16*2*6)
    add('CDC16x2',NAND,32*238*4+32*16*9+169*5)
    #Actual drain monitor:32pair busy +63node quiet +root quiet perroot.
    #Quiet equality includes node28bits; everyrawfieldtree internal remainsexisting.
    storage('drain_and_phase_sequencer',0,64*32+169+32+16*4+64*7*3+16)
    add('drain_and_phase_sequencer',NAND,4032*28*2+64*128*2+2048*2+12288*2//2)
    add('drain_and_phase_sequencer',INV,4032*28+64*128+2048)
    #Read selectoraddress12bits travels withrequest through12levels; register local
    #selects; no1559ps oldglobal selector combinational path inherited.
    storage('registered_selector',0,4095+12*12+169+32);add('registered_selector',BUF,4095*12)
    totals=sum(out.values(),collections.Counter())
    FF=totals[HQ]+totals[ASR]
    #Everypacked bitcell hasmax4.104um span; FO4leaf then FO8upper clock tree.
    leaves=(FF+3)//4;clk=leaves;n=leaves
    while n>1:n=(n+7)//8;clk+=n
    ctrl=totals[ASR];rst=(ctrl+3)//4;n=rst
    while n>1:n=(n+7)//8;rst+=n
    add('clock_reset_FO4leaf_FO8upper',BUF,clk+rst)
    areas={s:sum(k*(.04374 if m=='TIEHIx1_ASAP7_75t_R' else f[m]['SS']['area_um2']) for m,k in cnt.items()) for s,cnt in out.items()}
    return out,areas,{'FF':FF,'reset_FF':ctrl,'clock_BUF':clk,'reset_BUF':rst,'clock_leaf_FO':4,'upper_FO':8}

def control_packet(crc):
    #Twoheaderflits263bits(full169ctx+era32+shard1+nrow16+np3+op4+base30+seq8),
    #one238bitimmutablecontrolpayload. CRCfullduplexengineateachendpoint.
    N=3;ii=crc['ordered_packet_extend_II']
    return N*ii+N+1337+N*ii+1

def packet(rows,crc):
    n=rows;packets=[];CRCII=crc['ordered_packet_extend_II'];ctrl=control_packet(crc)
    while n:
        r=min(n,762);N=2+(r+2)//3
        tx=13+r+N*CRCII;send=N;rx=N*CRCII
        payload_ACK_wait=1337+rx+r+1+1337+1
        #TransportACK8 doesnotfreephase. Reversefullctx+eraqualifiedcreditpacket
        #mustarrive/capture; itsownsmallACK debtalsodrainsbeforeF.
        credit_and_own_ACK=ctrl+1337+1
        packets.append({'rows':r,'flits':N,'header_bits':263,'header_flits':2,'CRC_II':CRCII,
         'TXcollect_and_CRC':tx,'RXquarantine_verify':rx,
         'successful_cycles':tx+send+1337+rx+r+1+credit_and_own_ACK,
         'reverse_full_owner_credit_service':credit_and_own_ACK,
         'ACK_wait_bound_after_last_send':payload_ACK_wait,'timeout1024_PASS':payload_ACK_wait<1024,
         'previous4096_PASS':payload_ACK_wait<4096})
        n-=r
    bound=max((p['ACK_wait_bound_after_last_send'] for p in packets),default=0)
    return {'packets':packets,'cycles':sum(p['successful_cycles'] for p in packets),'ACK_wait_bound':bound,
            'minimum_timeout_for_this_packet_profile':bound+1,'timeout8192_PASS':bound<8192}

def placement(cellsections,areas):
    d,receipts=H.inputs();fields=H.current_fields(d['field.json'],d['frames.json'])
    dy=max(x['bbox_DBU'][3] for x in fields)-max(x['bbox_DBU'][3] for x in d['field.json'])
    oldhome=H.build()['model_selected_home_DBU'];site=54;pitch=540
    width=H.snap_up(8*(69*4104+4320),site)
    #Sourcecell literal master dimensions, packed bywhole section at50% rowpitch.
    f,_=C.facts();layouts=[];cursor=0
    #Common section run-layouts exclude no cell, and are deterministic not density proof.
    for name,counts in cellsections.items():
        x=0;row=0;runs=[];remaining=counts.copy();groups=[]
        # SAME-FLOP feedback, polarity and forward hold cells stay together.
        for ff in (C.HQ,C.ASR):
            count=remaining[ff]
            if not count:continue
            template=[ff,C.INV]+[C.NAND]*3+[C.BUF]*5
            if ff==C.ASR:template+=['TIEHIx1_ASAP7_75t_R']
            members=[];offset=0
            for master in template:
                remaining[master]-=count
                if remaining[master]<0:raise ValueError('unpriced storage cluster')
                w=162 if master=='TIEHIx1_ASAP7_75t_R' else round(f[master]['SS']['size_um'][0]*1000)
                members.append({'master':master,'x_offset_DBU':offset,'width_DBU':w});offset+=w
            groups.append((ff+'_hold_restore_forward_cluster',count,offset,members))
        for master,count in sorted(remaining.items()):
            if not count:continue
            w=162 if master=='TIEHIx1_ASAP7_75t_R' else round(f[master]['SS']['size_um'][0]*1000)
            groups.append((master,count,w,[{'master':master,'x_offset_DBU':0,'width_DBU':w}]))
        for group,count,w,members in groups:
            perrow=max(1,width//w);nrows=(count+perrow-1)//perrow
            runs.append({'group':group,'members':members,'count':count,'cell_width_DBU':w,'site_grid_DBU':54,
             'per_row':perrow,'rows':nrows,'last_row_cells':count-(nrows-1)*perrow,
             'first_row_offset_DBU':cursor+row*pitch,'row_pitch_DBU':pitch,'orientation':'R0'})
            row+=nrows
        height=row*pitch;layouts.append({'section':name,'bbox_relative_DBU':[0,cursor,width,cursor+height],'rows':row,'runs':runs})
        cursor+=height+4320
    halo=12960;outer_w=width+2*halo;outer_h=cursor+2*halo
    top=oldhome[3];home=[oldhome[0],top-outer_h,oldhome[0]+outer_w,top]
    retained=[]
    for kind,items in [('field',fields),('cfg',d['cfg.json']),('bands',d['bands.json']),('services',d['services.json'])]:
        for item in items:
            b=item['bbox_DBU'];b=[v+(dy if kind in ('cfg','bands') and j%2 else 0) for j,v in enumerate(b)]
            retained.append({'kind':kind,'name':item.get('name',str(item.get('local_pair'))),'bbox_DBU':b})
    lefs=json.loads((C.OUT/'inputs/cell_LEF.json').read_text());rails={}
    for master in set(m for counts in cellsections.values() for m in counts):
        rails[master]={}
        for supply,expected in [('VSS',[-9,9]),('VDD',[261,279])]:
            pin=re.search(r'PIN '+supply+r'\b(.*?)END '+supply,lefs[master],re.S)
            rect=re.search(r'RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',pin[1])
            y=[round(float(rect[k])*1000) for k in (2,4)]
            if y!=expected:raise ValueError('literal master R0 rail mismatch')
            rails[master][supply]=y
    #Thecurrent oldcapture/clock is NOTdeleted. Its overlap withreplacementhome
    #is declared; replacementrequiresuniqueinstance containment, notfree credit.
    conflicts=[r for r in retained if H.overlap(home,r['bbox_DBU'])]
    return {'new_identical_home_per_shard_DBU':home,'site_row_grid_DBU':[54,270], 'allocated_row_pitch_DBU':pitch,
      'width_um':outer_w/1000,'height_um':outer_h/1000,'gross_mm2_each_die':outer_w*outer_h/1e12,
      'sections':layouts,'named_cell_count':sum(sum(c.values()) for c in cellsections.values()),
      'known_retained_rectangle_conflicts':conflicts,'known_inventory_nonoverlap_PASS':not conflicts,
      'reticle33000x26000_um_rotated26x33_PASS':0<=home[0]<home[2]<=33000000 and 0<=home[1]<home[3]<=26000000,
      'old_capture_overlay_bbox_DBU':oldhome,'old_capture_overlay_overlap_expected':H.overlap(home,oldhome),
      'old_capture_credit_taken':0,'no_other_retained_instance_removed':True,
      'halo_DBU':halo,'actual_local_PG_M1':'EveryoccupiedR0row VSS[y-9,y+9],VDD[y+261,y+279];0.54rowpitch; source allmasters checked in cellLEF. M2/VIA12/M8upfeed bounds required.',
      'literal_PG_rail_y_DBU_by_master':rails,'interlevel_reader_mux_XOR_wires_not_constructed':True,
      'parent_inventory_receipts':receipts,'all_cell_runs_sitepacked_not_DRT_or_signoff':True,
      'new_global_clock_and_parent_PG_routes_not_installed':True}


def generate():
    matrix=crc_matrix();proof=crc_proof(matrix);crc=crc_construction(matrix);ss,areas,clock=sections(crc);layout=placement(ss,areas)
    a=Q.actual_certificate();events=[(x['edge'],x['a'],x['b']) for x in Q.rows(Q.ACTUAL) if x['kind']=='root_row_accept']
    remote=[e for e,g,r in events if g>=64];svc=packet(len(remote),crc);reserve=2*control_packet(crc)+7+1
    #Bothshard matched reserve ACK BEFOREGO; native accepted events shift by this
    #one successful-service cost. Original actualjournal remainsunchanged.
    F=max(remote)+reserve+svc['cycles']+7+8+1
    worst=packet(4096,crc)
    leases=json.loads((OUT/'inputs/dsrom_selected_context_lifetimes_20261003.json').read_text())
    fences=json.loads((OUT/'inputs/SU_fence_model.json').read_text())['constructive_deadline']
    return {'candidate':'DS4096-TP4-S58-PAR2-NP2048','component':'FULL4096_ROW_SHARD_PARENT_V1','default_off':True,
      'ROM_ECC':False,'arithmetic_golden_payload_unchanged':True,'CRC_source_exactness':proof,'CRC':crc,
      'construction_cell_counts_per_shard':{s:dict(v) for s,v in ss.items()},'cell_body_area_per_section_um2_per_shard':areas,
      'cell_body_mm2_each_shard':sum(areas.values())/1e6,'clock_reset':clock,'new_home':layout,
      'native_VM_order_and_finite_grant_join':vm_contract(),'registered_cell_screen':electrical_screen(),
      'reticle_accounting':{'inherited_selected_caller_r7_screen_mm2':json.loads((OUT/'inputs/selected_caller_r7.json').read_text())['whole_reticle_join']['screen_mm2'],
        'new_component_home_per_die_mm2':layout['gross_mm2_each_die'],'old_capture_or_packet_memory_containment_credit_mm2':0,
        'old_selector_WAKE_field_or_return_state_recharged':False,'no_existing_field_cfg_or_service_instance_removed':True,
        'known_rectangle_screen_not_current_global_site_fit':True,'new_VM_macro_body_and_parent_route_area_unbound':True,
        'new_clock_union_is_successor_to_existing_live_graph_not_mutation_or_claim_of_same_endpoint_set':True},
      'fixed_capacity':{'roots_per_shard':64,'rows_per_root':64,'raw69_records_per_shard':4096,'pipeline_levels':12,'sink_edge':1,'read_seq_bits':16,'read_record_bits':102,'read_sink_tokens':16,'version_slots':32,'CRC_engines_total_two_shards':8,'packet_MAX256_FLIT256':True,'packet_header_bits':263,'packet_header_flits':2,'full_owner_credit_payload_bits':238,'transport_ACK8_is_not_owner_credit':True,'control_CDC_entries_each_direction':16,'control_CDC_payload_bits':238,'VM_writer_per_logical_owner':1},
      'port_intensity':{'MACs_per_cycle':0,'raw_root_ingress_bits_per_native_edge_per_shard':64*69,
        'proposed_scalar_read_return_bits_per_stream_edge_per_shard':102,'proposed_scalar_publication_bytes_per_stream_edge':4,
        'native_VM_demand_read_bytes_per_serial_edge':6080,'native_VM_demand_write_bytes_per_serial_edge':2372,
        'proposed_bank_backend_peak_bytes_per_service_edge_each_direction':32*4,
        'wire_payload_bits_per_accepted_flit':256,'forward_data_and_integrity_bits':330,'reverse_ready_ACK_credit_bits':12,
        'duplex_signal_lanes':684,'actual_directional_track_availability_after_PG_OBS':None,
        'throughput_limits':'CRC packet feedback II11 and one packet credit. VM upper envelope is demand, not granted throughput. Full backend G/L and phase concurrency unbound.',
        'replica_policy':'Both physical shard dies receive identical full4096-row component cell allocation. Original field2048 pairs and8192 ROM leaves per die unchanged.'},
      'sequencer':'RESET_ACK->IDLE->matchedBOTHSHARDreserve(all12writer_DRAIN,VMversion_slot,actualpair/node/rootempty)->CFG25accepted->GOmatchedloadergen->DRAIN(allrowsVMvisible+matchedpositivecredits,allread/packet/CDCdebt0,allnativeactualquiet)->RETIRE/registerqualifiedF->IDLE. VMversionretainedthroughactualSUreadR+2drain.',
      'quiet_monitor':{'signals_per_global_root':96,'logic':'32pairquiet +63nodequiet +rootquiet; pairbusy includesDRAIN127, but node/root actualfifo/pipeline/held empty exported indefaultoffsourcewrapper; simulation-onlyquiet=0 cannotbeused','local_registered_reduce_edges':4,'global_registered_reduce_edges':4,'generation_register_and_clear_at_GO_required':True,'synchronous_nooverlap_wired_not_an_assumed_annotation':True},
      'VMguard':{'source_formatter_unchanged':'obase+row+pos*ops AW30; fmt==1 or(fmt==0 && row<rsplit ?pw62:pw63) ->FP32 else retainedBF16<<16. RejectAW19alias beforepublication, never reround.',
        'writer_admission':'Reserveexclusivepublication service afterall12writerunit_DRAIN; gate NEW conflicting engineaccepts, do notstall unbuffered alreadyactivewriter output. All128nativeROMwe suppressed ONLYownedcapturedphase; slot0newownedpublication selected.',
        'version32_scope':'8retainedselectedoutputversions +3XN/ACT/EID sourceinputs +12writerowners +2link/context slots=25<32; fullprogram unknownlifetimes backpressure beforeacquisition, not drop/overwrite. Fullprogramdeadlockfree/rate needscompiledgraph enrollment.',
        'source_VM_payload_bits_not_duplicated':leases['existing_VM_payload_bits_per_rank'],'selected_source_max_output_versions':leases['conditional_maximum_selected_output_versions'],'selected_output_payload_words':leases['conditional_maximum_selected_output_FP32_words']},
      'CDC':{'scheme':'two16-entryGray-pointercontrolmailboxes; 2receiverFF sync andregisteredcapture. Full169ctx+era32+row16+seq16+shard1+opcode4 held inownedstableFIFO, no bitwisebussync','crossing_phase_bound_stream_edges':7,'latency_is_positive_with3:4_arbitrary_phase':True,'reset':'asyncassert/synchronous2FFreleaseeachdomain +bothreseteraACKquiescence BEFOREGO; resetdoesnoteraseacceptedbank/packet/versiondebt','gen':'full32+era32; no wrap/reuse beforeallaffectedoldVMversions/peerpacketsdrained. Epochrequesttokenalwaysmatchesidentity.', 'actual_CDC_SDF_and_resetrelation_qualification':False},
      'service':{'matched_shard_reservation_prep_edges':reserve,'I66_remote_packet_service':svc,'I66_prospective_F':F,'I66_native_idle':421,'I66_added_rearm_dependency_edges':F-421,'I66_added_rearm_dependency_us':(F-421)/1200,'worst_full4096_remote_service':worst,'previous4096_timeout_is_insufficient_for_newCRC':any(not p['previous4096_PASS'] for p in worst['packets']),'derived_single_timeout_candidate':8192,'timeout32bit_counter_state_unchanged':True,'timeout_is_successful_service_bound_not_relaxedclock_orretry':True,'normal_failure_faults_preserved_and_no_retry_job':True,'I66_conditional_SU_front_lower_edge':F+7,'wholeprogram_token_delta':None,
       'numeric_service_assumptions':'1337+1337 uncharacterized successful link edge envelope; full reserved packet RAM; VM exclusive scalar grant1/streamedge with postNBA1; positiveCDC7; no retransmission. Native VM G/L and physical wire stations still unbound.',
       'joined_delta_expression':'9466 streamedges + nativeVMgrant/response stalls + extra admitted wire/clock/CDC cuts + original phase arbitration. Apply only actual exposed dependency edges, not all ops or six positions multiplied blindly.'},
      'pinned_SU_fences':fences,'source_consumer_lease_Rplus2':'Lease release requiresactualsamectxSUread andmatchingR+2tag/nativeSUdrain, not firstconsumerdispatch; observercallback ABI pinnedbelow. Source12W1W3fencesV<F thenSUfront>=F+7;6nativeW2leasesremain enrolled.',
      'limits':['No source RTL, HDL build or P&R launched byconstruction.','Eight balanced XOR cuts plus capture/terminal CRC proof isnotSSFF timing; registered circuits and route caps screenedseparately.','Oneposition capacityand46509countcert: MTP6 needs6positionschedule/runtimeenrollment and serialization cost; notautomaticallycapacity for6 simultaneouspositions.','Newhome sitepacking andknowninventorynonoverlap not parentclock/PG/pin/DRTqualification; oldcaptureoverlay notcredited orsilentlydeleted.','No admittedfulltoken/persistentKV/headprovider/rate; parentall4778program criticalpath extra unitadmission stalls unknown, notzero.'],
      'component_construction_complete':False,'finite_component_counts_and_cell_run_allocation_complete':True,
      'initial_header_reset_era_omission_preserved_NOT_SELECTED':True,'defaultoff_RTL_preparation_ready':False,
      'next_admission_gate':'Bind native VM bank/mask grants, response/visible receipts and compiler batch/address exclusions; loaded 13-edge local path and parent clock/reset/PG relays must pass before reader/CDC build.',
      'HDL_build_GO':False,'context_PnR_GO':False,'physical_fit':False,'rate_adopted':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args()
 if a.verify:
  for f,h in json.loads((OUT/'source_pins.json').read_text()).items():
   if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise ValueError('source pin changed '+f)
  for f,h in json.loads((OUT/'manifest.json').read_text()).items():
   if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise ValueError('artifact changed '+f)
  raw=json.dumps(generate(),sort_keys=True,indent=2)+'\n'
  if raw!=(OUT/'model.json').read_text():raise ValueError('nonidentical component regeneration')
  print('PASS pinned sources, artifacts and exact component regeneration; NO BUILD ADMISSION')
 else:
  if a.out is None:p.error('--out required for generation')
  a.out.write_text(json.dumps(generate(),sort_keys=True,indent=2)+'\n')
