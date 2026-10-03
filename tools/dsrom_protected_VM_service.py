#!/usr/bin/env python3
"""Finite protected native-VM service contract; source-only arithmetic model.

One transaction and one held reply, with real shared parity macro addresses.
No engine, physical timing, or whole-token completion is inferred.
"""
import hashlib,json,math,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_protected_VM_service_20261003'


def pins():
    rows=json.loads((BASE/'inputs/origins.json').read_text())
    for r in rows:
        if hashlib.sha256((BASE/'inputs'/r['copy']).read_bytes()).hexdigest()!=r['sha256']:
            raise ValueError('Source drift '+r['copy'])
    return rows


def codec():
    p=BASE/'inputs/codec_model.py'
    row=next(r for r in json.loads((BASE/'inputs/origins.json').read_text()) if r['copy']=='codec_model.py')
    if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Codec source drift before execution')
    m=types.ModuleType('pinned_source_W6');m.__file__=str(p)
    exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__)
    return m


CODEC=codec()
MASK32=(1<<32)-1
SCHEDULE={
 'INIT':{'capture':0,'guard_encode':1,'write_issue':2,'data_and_parity_visible':4,'raw_ack':5,'verify_issue':6,'verify_return':10,'checked_compare':11,'publication':12},
 'WRITE_FULL':{'capture':0,'guard_encode':1,'write_issue':2,'data_and_parity_visible':4,'raw_ack':5,'verify_issue':6,'verify_return':10,'checked_compare':11,'publication':12},
 'WRITE_MASKED':{'capture':0,'guard':1,'old_read_issue':2,'old_read_return':6,'old_check':7,'merge_encode':8,'write_issue':9,'data_and_parity_visible':11,'raw_ack':12,'verify_issue':13,'verify_return':17,'checked_compare':18,'publication':19},
 'READ4':{'capture':0,'guard':1,'read_issue':2,'read_return':6,'checked_decode':7,'publication':8}}


def home(word):
    if type(word)is not int or not 0<=word<32768:raise ValueError('Word AW15 bounds')
    return (word&3,word>>12,(word>>2)&511,(word>>11)&1)


def encode_word(data):
    if type(data)is not int or not 0<=data<1<<512:raise ValueError('Raw512 bounds')
    return [CODEC.encode64((data>>(64*i))&((1<<64)-1)) for i in range(8)]


class Service:
    """Finite reference controller. No dictionary collapse of accepted IDs.

    Stores physical data and parity words only for test-populated addresses.
    Real hardware capacity is full32768 words/32 parity macros, not this sparse
    representation. INIT explicitly walks all words in order; reads/updates
    can use the initialized prefix. No constructor-zero policy is admitted.
    """
    def __init__(self):
        self.data={};self.parity={};self.init_next=0;self.now=0
        self.pending=None;self.response=None;self.fault=None;self.events=[]

    def accept(self,kind,word,owner,data=0,mask=0,rst_n=True):
        if type(rst_n)is not bool:raise ValueError('Typed reset input')
        if not rst_n or self.pending or self.response or self.fault:return False
        home(word)
        if type(owner)is not int or not 0<=owner<1<<228:raise ValueError('Owner228 bounds')
        if kind not in SCHEDULE:raise ValueError('Unsupported transaction kind')
        if type(mask)is not int or not 0<=mask<1<<16:raise ValueError('Mask16 bounds')
        encode_word(data)
        if kind=='READ4':
            if word&3 or word+3>=self.init_next:raise ValueError('Aligned read of four initialized words required')
        elif not mask:raise ValueError('No enabled lane')
        elif kind=='INIT':
            if word!=self.init_next or mask!=65535:raise ValueError('INIT must walk full word prefix')
        elif word>=self.init_next:raise ValueError('Update of uninitialized word')
        elif (kind=='WRITE_FULL')!=(mask==65535):raise ValueError('Source-selected full/masked operation mismatch')
        self.pending=dict(kind=kind,word=word,owner=owner,data=data,mask=mask,start=self.now)
        self.events.append(dict(edge=self.now,event='accept',owner=owner,word=word))
        return True

    def _codes(self,word):
        bank,pair,row,half=home(word)
        if word not in self.data or (bank,pair,row)not in self.parity:raise ValueError('Missing explicit initialization')
        checks=(self.parity[(bank,pair,row)]>>(half*64))&((1<<64)-1)
        data=self.data[word];codes=[]
        for i in range(8):
            raw=(data>>(64*i))&((1<<64)-1)
            # Actual W6 layout interleaves data into Hamming positions; stored
            # byte is parity at1,2,4,8,16,32,64 plus overall at72.
            code=CODEC.encode64(raw)
            positions=[0,1,3,7,15,31,63,71]
            for j,p in enumerate(positions):
                code=(code&~(1<<p))|(((checks>>(8*i+j))&1)<<p)
            codes.append(code)
        return codes

    def _decode(self,codes):
        result=0;corrected=0
        for i,code in enumerate(codes):
            value,corr,ue=CODEC.decode64(code)
            if ue:raise ValueError('Uncorrectable stripe: quarantine before write/publication')
            corrected|=int(corr)<<i;result|=value<<(64*i)
        return result,corrected

    def _commit(self,t):
        word=t['word'];bank,pair,row,half=home(word)
        old=self.data.get(word,0)
        value=old
        for lane in range(16):
            if t['mask']>>lane&1:
                value=(value&~(MASK32<<(lane*32)))|(((t['candidate']>>(lane*32))&MASK32)<<(lane*32))
        checks=0
        for i,c in enumerate(encode_word(t['candidate'])):
            for j,p in enumerate([0,1,3,7,15,31,63,71]):checks|=((c>>p)&1)<<(8*i+j)
        key=(bank,pair,row);oldchecks=self.parity.get(key,0)
        self.parity[key]=(oldchecks&~(((1<<64)-1)<<(half*64)))|(checks<<(half*64))
        self.data[word]=value
        self.events.append(dict(edge=self.now,event='data_and_parity_visible',owner=t['owner'],word=word,bank=bank,sidecar_pair=pair,row=row,half=half))

    def step(self):
        t=self.pending
        if t and not self.fault:
            age=self.now-t['start'];s=SCHEDULE[t['kind']]
            try:
                if age==s.get('guard_encode',-1):t['candidate']=t['data']
                if age==s.get('old_read_return',-1):t['old_codes']=self._codes(t['word'])
                if age==s.get('old_check',-1):t['old'],t['old_corrected']=self._decode(t['old_codes'])
                if age==s.get('merge_encode',-1):
                    value=t['old']
                    for lane in range(16):
                        if t['mask']>>lane&1:value=(value&~(MASK32<<(32*lane)))|(((t['data']>>(32*lane))&MASK32)<<(32*lane))
                    t['candidate']=value
                if age==s.get('data_and_parity_visible',-1):self._commit(t)
                if age==s.get('raw_ack',-1):self.events.append(dict(edge=self.now,event='raw_ack_NOT_publication',owner=t['owner']))
                if age==s.get('verify_return',-1):t['verify_codes']=self._codes(t['word'])
                if age==s.get('checked_compare',-1):
                    t['checked'],t['corrected']=self._decode(t['verify_codes'])
                    if t['checked']!=t['candidate']:raise ValueError('Postwrite checked value mismatch')
                if age==s.get('read_return',-1):
                    t['read_codes']=[self._codes(t['word']+i) for i in range(4)]
                if age==s.get('checked_decode',-1):
                    values=[self._decode(c)for c in t['read_codes']]
                    t['checked']=sum(v<<(512*i) for i,(v,c)in enumerate(values));t['corrected']=sum(c<<(8*i)for i,(v,c)in enumerate(values))
                if age==s['publication']:
                    self.response=dict(owner=t['owner'],kind=t['kind'],word=t['word'],mask=t['mask'],data=t['checked'],corrected=t['corrected'],at=self.now)
                    if t['kind']=='INIT':self.init_next+=1
                    self.events.append(dict(edge=self.now,event='checked_publication',owner=t['owner']))
            except ValueError as e:
                self.fault=dict(owner=t['owner'],edge=self.now,reason=str(e))
                self.events.append(dict(edge=self.now,event='quarantine',owner=t['owner']))
        self.now+=1

    def consume(self,owner):
        if self.fault or not self.response or owner!=self.response['owner']:raise ValueError('No matching checked response')
        self.events.append(dict(edge=self.now,event='consumer_receipt',owner=owner))
        response=self.response;self.response=None;self.pending=None
        return response

    def reset(self,positive_allcopies_fence=False):
        if self.pending or self.response or self.fault or not positive_allcopies_fence:raise ValueError('Reset is not drain or rollback')
        # SRAM remains physically populated, but initialized-version ownership
        # is invalidated and must be explicitly walked again.
        self.init_next=0


def tree(sinks,leaf,upper=8):
    counts=[math.ceil(sinks/leaf)]
    while counts[-1]>1:counts.append(math.ceil(counts[-1]/upper))
    return counts


def build():
    source=pins();prices=json.loads((BASE/'inputs/cell_prices.json').read_text())['facts'];macro=json.loads((BASE/'inputs/SRAM.json').read_text())
    records={'request':{'raw_bits':228+512+15+16+2+1},'raw_checked_capture_metadata':{'raw_bits':228+15+1+2+32+32},'response_metadata':{'raw_bits':228+15+16+2+32+32+1},'state_init_era_phase_debt':{'raw_bits':32+16+5+1+1+1+1+8+8}}
    for v in records.values():v['codewords']=math.ceil(v['raw_bits']/64);v['bits']=v['codewords']*72
    # Capture and response each retain the actual32 interleaved72bit codewords.
    records['raw_checked_capture_metadata']['bits']+=32*72
    records['response_metadata']['bits']+=32*72
    state=sum(v['bits']for v in records.values());g=CODEC.Gates()
    for _ in range(32):g.codec()
    codec_gates=g.dict();codec_body=sum(n*prices[k]['SS']['area_um2']for k,n in codec_gates.items())
    raw_registers = {
        'four_bank_command_data_masks': {'raw_bits': 4*(4+4+9+9+512+16), 'codewords': 4*(1+1+1+1+8+1)},
        'bank_partial_reduction': {'raw_bits': 4*4*512, 'codewords': 4*4*8},
        '64_group_local_write_data_mask_row_enable_and_masked_read': {'raw_bits': 64*(512+16+9+1+512), 'codewords': 64*(8+1+1+1+8)},
        '64_group_salt_selector_same_edge_64bit_records': {'raw_bits': 64*64, 'codewords': 64},
        'root_pipeline_and_output': {'raw_bits': 2082, 'codewords': 5+32},
        'write_ACK_16_owner_address_mask_valid_records': {'raw_bits': 4160, 'codewords': 16*5},
        'read_owner_5_records': {'raw_bits': 1140, 'codewords': 5*4}}
    assert sum(v['raw_bits'] for v in raw_registers.values()) == 89086
    backend_codes = sum(v['codewords'] for v in raw_registers.values())
    side_guard=CODEC.Gates()
    side_guard.OR(39+41+9+61+3)
    for _ in range(64):side_guard.eq(3)
    for _ in range(32):side_guard.eq(2)
    side_guard.AND(64*6+10)
    side_guard.mux(256,8)
    guard_counts=side_guard.dict()
    side_guard_body=sum(n*prices[k]['SS']['area_um2']for k,n in guard_counts.items())
    result={'schema':'DS_PROTECTED_VM_FINITE_SERVICE_R1','candidate':'DS4096-TP4-S58-PAR2-NP2048','source_pins':source,'MACs_per_cycle':0,'service':{'transaction_seats':1,'held_response_seats':1,'bank_issue_policy':'One write word total, selected actual bank; reads one aligned consecutive4word command. No simultaneous transactions; no free1520 ports or4write grants.','initialized_prefix_words':32768,'initialization':'Explicit in-order full-word writes, checked readback before advancing prefix. Uninitialized reads/partial writes refuse. No constructor zero. No invented golden checkpoint payload.','producer_stall':'req_ready false during service/held response/fault/reset; cannot lose accepted request.','consumer_stall':'Arbitrary held response wait consumes the sole credit. No finite liveness bound without actual consumer guarantee; memory completion independent of ready.','fault':'UE/postwrite mismatch quarantines full owner. Normal write/read receipt forbidden. Positive owner recovery/reset fence separately required, no local empty inference.'},'port_bandwidth':{'native_data_read_bits':2048,'native_data_read_bytes':256,'native_data_write_bits_max':512,'native_data_write_bytes_max':64,'sidecar_read_bits_physical':4*128,'sidecar_checked_bits_selected':256,'sidecar_write_bits_physical':128,'sidecar_enabled_write_bits':64,'raw_owner_bits':228},'sidecar':{'macros':32,'native_macro':'ot_sram_1r1w_512x128_m4_r2c2','actual_address':'bank=word&3,pair=word>>12,row=(word>>2)&511,half=(word>>11)&1','ports_per_macro':'1R1W; group halves share ports. Serialized service eliminates simultaneous conflicting half requests; not two independent ports.','bit_layout':'8 check bits/64data stripe, positions1,2,4,8,16,32,64,72; 8stripes/512word;64checks/half.','mask':'Only selected64-bit half written. Paired group otherhalf preserved.','sidecar_body_mm2':32*macro['area']['macro_area_um2']/1e6,'total_data_and_sidecar_body_mm2':288*macro['area']['macro_area_um2']/1e6},'state_records':records,'protected_service_state_bits':state,'ASR_body_floor_mm2':state*prices['DFFASRHQNx1_ASAP7_75t_R']['SS']['area_um2']/1e6,'codec_replicas':{'encoder':32,'decoder':32,'sharing':'Serialized whole-bank write uses8 of32 encoders; full checked read/held output uses32. No32perwritebank multiplication.'},'codec_gate_construction':codec_gates,'codec_body_mm2':codec_body/1e6,'calendar':SCHEDULE,'latency':{'clock_GHz':.9,'read_min_edges':8,'fullwrite_checked_publication_edges':12,'masked_write_checked_publication_edges':19,'read_min_II':9,'fullwrite_min_II':13,'maskedwrite_min_II':20,'all_VM_full_initialization_min_edges':32768*13,'source_model_only':'Functional stage placement, not loaded SSFF timing guarantee. Any additional codec/control cut changes calendar/state/II before engine adoption.','held_wait_charge':'actual H edges added to each transaction; no assumed perfect service or capped timeout','per_user_composition':'Sum actual source-selected READ4/WRITE_FULL/WRITE_MASKED counts times service II plus actual waits/CDC. Whole-token counts belong to system-stream peer, not invented here.'},'clock_load':{'service_ASR_sinks':state,'SS_CLK_fF':state*prices['DFFASRHQNx1_ASAP7_75t_R']['SS']['pins']['CLK']['cap_fF'],'FF_CLK_fF':state*prices['DFFASRHQNx1_ASAP7_75t_R']['FF']['pins']['CLK']['cap_fF'],'FF_RESETN_fF':state*prices['DFFASRHQNx1_ASAP7_75t_R']['FF']['pins']['RESETN']['cap_fF'],'sidecar_macro_SS_CLK_fF':32*macro['timing']['ss']['clk_cap_ff'],'sidecar_macro_FF_CLK_fF':32*macro['timing']['ff']['clk_cap_ff']},'routing':{'new_data_checks_boundary_bits':256+64,'new_boundary_bits_lower_bound':320,'48nm_signal_only_width_floor_um':320*.048,'PG_OBS_via_clock_exclusion_capacity':'Not bound; selected full288macro union required. No borrowed HUB_VM/co-resident space.'},'source_interfaces':{'req':'valid/ready +kind2 +word15 +data512 +mask16 +owner228','rsp':'held valid/ready +kind2 +status2 +word15 +checkeddata2048 +mask16 +corrected32 +owner228; faults cannot normalretire','owner_layout':'context169 +resetera32 +batch16 +requestID11=228; source readframe1520 requires11 bits, previous227 write-only tag10 must not truncate. r2 instantiatedTAG_W228; +21raw tagpipelineFF/+10interfacepins, unchanged W6wordcounts.', 'raw_backend':'Reviewed r2 N+2 data visible/N+3 rawACK/N+4 rawread','system_peer':'Publish credit only after matching held checked response; read-old/source NBA frame order and12writer guards remain peer parent responsibilities.'},'source_control_gap':{'raw_register_inventory':raw_registers,'raw_state_bits':89086,'prospective_protected_codewords':backend_codes,'prospective_protected_bits':backend_codes*72,'replacement_FF_delta_bits':backend_codes*72-89086,'packing_rule':'Salt/selector64 bits per group all update on same edge; same-stage root control vector grouped, never pack across pipeline ages. Codecs/decoded fanout need actual source mapping, no synthesized sharing credit.','prospective_codec_encoder_decoder_pairs':backend_codes,'conservative_full_codec_body_mm2':backend_codes*codec_body/32/1e6,'actual_raw_backend_address_and_selector_protection_installed':False,'reason':'r2 has unprotected address/group/row/selector/command tags. External data check alone cannot prove every wrong-address/control fault is detected; these exact mutable control registrations require protection adapter or source-selected replacement. No complete protected-provider claim.'},'admission':{'finite_reference_model':True,'sidecar_component_source_preparation':True,'protected_parent_engine_RTL':False,'connected_protected_VM_build':False,'physical':False,'SSFF':False,'whole_token':False},'four_targets':{'DS_ROM':'Selected raw backend candidate finite service only','DS_HBM':'Mutable protection methodology; no DSROM bank layout transfer','Qwen_ROM':'No source instance or service capacity credit','Qwen_HBM':'GPU SRAM protection separate; no DSROM topology credit'},'sidecar_component':{'command_record_R_bits':288,'command_record_W_bits':360,'R_pipe_records':5,'W_pipe_records':4,'checks_capture_state_bits':768,'fault_record_bits':72,'total_FF_bits':3720,'codec_encoder_count':10,'codec_decoder_count':41,'ASR_body_floor_mm2':3720*prices['DFFASRHQNx1_ASAP7_75t_R']['SS']['area_um2']/1e6,'codec_unmapped_conservative_41_fullpair_body_mm2':41*codec_body/32/1e6,'codec_extra_encoder_allowance':31,'SS_macro_CLK_fF':32*macro['timing']['ss']['clk_cap_ff'],'FF_macro_CLK_fF':32*macro['timing']['ff']['clk_cap_ff'],'source_guard_and_readmux_gate_construction':guard_counts,'source_guard_and_readmux_body_um2':side_guard_body,'native_source_prepared_path':'rtl/model_ready_ds_vm_sidecar_20261003/ot_ds_vm_check_sidecar.sv','source_prep_allowed':True,'functional_component_build_allowed_after_source_freeze':True,'physical_admission':False,'latency':{'raw_parity_read':4,'parity_write_visible':2,'tagged_parity_ACK':3}},'CDC_parent_swap':{'source':'27d86cfe4b8f87dab020886b70f4d75f89a819e6','classes_scope':'This reply models only protected nativeVM service request/response and links prior fullparent graph as separate unadopted scope. Not fullDS7classes orQwen53kbit parent closure.','prospective_forward_raw_bits':773,'prospective_reverse_raw_bits':2343,'forward_W6_coded_bits':936,'reverse_W6_coded_bits':2664,'reverse_consumer_receipt_raw_bits':237,'reverse_consumer_receipt_W6_bits':288,'shared_FIFO_parameters':{'DEPTH':4,'HOLD':2},'FIFO_encoded_data_plus_raw_control_FF':8*(936+2664+288)+3*26,'FIFO_unprotected_control_bits_each':26,'FIFO_control_protection_installed':False,'one_service_owner_credit':1,'replicas_per_selected_VM_service':1,'FIFO_instances':3,'receipt_rule':'ThirdF2S receipt plane transports full228owner+6positivefencebits+kind2+taken1. Sending checkedresponse toFIFO is not serviceconsumer receipt or bank reuse; pendingowner stays until matching reverse event. Fault quarantine never clears onFIFOflush.','4_over_3_slow_port_widening':False,'rate_policy':'Keep actual port widths; fast source requests must honor finite ready/one-owner credit. No continuous1.2G stream consumed at0.9G without stalls.','latency_scope':'Related phase no-stall bounds F2S5..8VCOticks andS2F4..6 from actual source; total roundtrip9..14ticks=2.5..3.8889ns before endpoint guard/protection/cuts/stalls. Not actual loaded-parent timing.','reset':'LocalFIFO DOWNWAIT flush/empty cannot clear pending owner. Stop admission, hold/quarantine accepted owner, require service visible/consumer/reverse/allcopies positive receipts before era rearm.','channel_signal_floor_bits':936+2664+288,'channel_signal_only_48nm_width_um':(936+2664+288)*.048,'loaded_actual_parent_sources_and_receivers_bound':False,'current_physical_G0':False},'no_new_jobs':True,'no_PVE2_PVE3_jobs':True,'global_solver_unchanged':True}
    return result


if __name__=='__main__':
    BASE.mkdir(parents=True,exist_ok=True);p=BASE/'model.json';p.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n');print(p)
