#!/usr/bin/env python3
"""Pinned H1/shared/GU endpoint contract and finite bank-fence G0 model.

Models source port handshakes and opaque SRAM words, without numerical oracles.
Candidate gateway wiring is not installed RTL. Full physical admission remains
mandatory before implementation; no provisional calendar delta is inserted.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'results/uarch/h4_hbm_atomic_source_g0_20261002'
MANIFEST_SHA='d0f809d2a8d1dda52bb19a00832f4bc4cf101fd57f7dbd5db9d84263370c78ce'

def sha(b):return hashlib.sha256(b).hexdigest()
def uint(x,bits,label):
    if type(x)is not int or not 0<=x<2**bits:raise ValueError(label)
    return x
def sources():
    raw=(INPUT/'manifest.json').read_bytes()
    if sha(raw)!=MANIFEST_SHA:raise ValueError('source manifest pin mismatch')
    m=json.loads(raw);out={}
    for r in m['inputs']:
        p=(INPUT/r['archive']).resolve()
        if not p.is_relative_to(INPUT.resolve()):raise ValueError('source origin escapes')
        b=p.read_bytes()
        if len(b)!=r['bytes'] or sha(b)!=r['sha256']:raise ValueError('source origin mismatch')
        out[r['path']]=b
    return m,out

class DrainGate:
    """Observe real full-SM ports after quiescing competing request valids.

    No caller RF_drained boolean substitutes for the individual observations.
    Previously accepted host/SIMD/shared results retain their original sinks.
    """
    REQUESTS=('host_rd_valid','host_wr_valid','simd_valid','scratch_valid')
    SIGNALS=REQUESTS+('host_rd_ready','host_wr_ready','host_rsp_valid','host_ack_valid','simd_done','scratch_ready','scratch_done')
    def __init__(self):self.phase='idle';self.owner=None
    def request(self,ticket):
        if self.phase!='idle':raise ValueError('SM owner already pending')
        if type(ticket)is not tuple or len(ticket)!=5 or any(type(x)is not int for x in ticket):raise ValueError('C0 owner tuple')
        self.owner=ticket;self.phase='drain'
    def sample(self,pins):
        if set(pins)!=set(self.SIGNALS) or any(type(v)is not bool for v in pins.values()):raise ValueError('exact source port observations required')
        if self.phase!='drain':raise ValueError('not draining')
        if any(pins[n]for n in self.REQUESTS):raise ValueError('source requests must be quiesced before idle probe')
        idle=pins['host_rd_ready'] and pins['host_wr_ready'] and pins['scratch_ready'] and not any(pins[n]for n in ('host_rsp_valid','host_ack_valid','simd_done','scratch_done'))
        if idle:self.phase='owned'
        return idle
    def release(self,ticket,*,all_completion_sinks_drained,reverse_grant):
        if self.phase!='owned' or ticket!=self.owner or all_completion_sinks_drained is not True or reverse_grant is not True:raise ValueError('source completions and reverse grant required')
        self.phase='idle';self.owner=None
    def controls(self):return dict(allow_competing_requests=self.phase=='idle',retain_preexisting_completion_sinks=self.phase=='drain',mask_bulk_response=False)

class BankFence:
    """Eight bank owners shared by C0/GU/KV, not per-client hidden queues.

    Same-bank nonoverlapping accesses also serialize. GU's existing16-entry
    producer FIFO holds unaccepted l2_v packets; KV uses existing client seats.
    A bank holds one word in flight and retains its full line through reverse.
    """
    def __init__(self,model,rank,stack):
        if model not in ('Qwen','DeepSeek'):raise ValueError('model')
        uint(rank,7,'rank');uint(stack,2,'stack')
        if rank>=(2 if model=='Qwen' else 96):raise ValueError('rank')
        self.model=model;self.rank=rank;self.stack=stack;self.live={};self.watermark={}
    def reserve(self,ticket,*,producer,bank,address,size,write,lease,producer_ref,GU=None):
        if type(ticket)is not tuple or len(ticket)!=5 or any(type(x)is not int for x in ticket):raise ValueError('source owner tuple')
        gen,pc,seq,rank,sm=ticket;uint(gen,64,'generation');uint(seq,40,'sequence');uint(sm,5,'SM')
        if not gen or not seq or rank!=self.rank or sm//8!=self.stack or not 0<=pc<(1737 if self.model=='Qwen' else 2213):raise ValueError('source owner extent')
        uint(bank,3,'producer bank')
        if producer not in ('C0','GU','KV') or type(write)is not bool or not isinstance(lease,str) or not lease or not isinstance(producer_ref,str) or not producer_ref:raise ValueError('bound producer and lease required')
        if type(address)is not int or type(size)is not int or size not in (4,32,64,128) or address<0 or address%size or address+size>262144:raise ValueError('actual bank extent and alignment')
        if producer=='C0' and size!=128:raise ValueError('C0 line128')
        if ticket in (x['ticket']for x in self.live.values()):raise ValueError('same owner already holds a bank')
        if bank in self.live:raise ValueError('bank owner busy, even for nonoverlapping range')
        key=(producer,sm)
        if (gen,seq)<=self.watermark.get(key,(0,0)):raise ValueError('stale producer sequence')
        if producer=='GU':
            if not write or size!=4 or bank!=sm%8 or not isinstance(GU,dict):raise ValueError('GU source scalar producer mapping')
            if set(GU)!={'epoch','mapped_epoch','row','partition_base','local_row','id','column'}:raise ValueError('complete GU descriptor mapping required')
            for n,b in [('epoch',16),('mapped_epoch',16),('row',18),('partition_base',18),('local_row',16),('id',4),('column',4)]:uint(GU[n],b,'GU '+n)
            if GU['row']!=GU['partition_base']+GU['local_row'] or GU['epoch']!=GU['mapped_epoch'] or address!=4*GU['local_row']:raise ValueError('GU row/epoch/physical home mismatch')
        elif GU is not None:raise ValueError('foreign GU descriptor')
        self.live[bank]=dict(ticket=ticket,producer=producer,address=address,size=size,write=write,lease=lease,producer_ref=producer_ref,GU=dict(GU)if GU else None,next=0,pending=None,receipts=[],phase='accepted')
        self.watermark[key]=(gen,seq)
    def owner(self,bank,ticket):
        if bank not in self.live or self.live[bank]['ticket']!=ticket:raise ValueError('stale/foreign bank owner')
        return self.live[bank]
    def word_request(self,bank,ticket,*,data=None):
        x=self.owner(bank,ticket)
        if x['phase']!='accepted' or x['pending']is not None:raise ValueError('one physical bank word in flight')
        count=1 if x['size']<=32 else x['size']//32
        if x['next']>=count:raise ValueError('all source words already issued')
        a=x['address']+x['next']*32;word=a//32;lane=(a%32)//4
        width=x['size']if x['size']<32 else 32
        if x['write']:
            if not isinstance(data,bytes) or len(data)!=width:raise ValueError('opaque exact word bytes required')
            wd=data*8 if width==4 else data
        else:
            if data is not None:raise ValueError('read data must come from SRAM capture')
            wd=None
        request=dict(bank=bank,macro=word//1024,row=word%1024,ordinal=x['next'],r_ce=not x['write'],w_ce=x['write'],w_mask=((1<<(8*width))-1)<<(32*lane) if width==4 else (1<<256)-1,wdata=wd)
        x['pending']=request;return dict(request)
    def capture(self,bank,ticket,*,lease,producer_ref,clock_edge,w_ce_accepted=False,r_ce_captured=False,rdata=None):
        x=self.owner(bank,ticket);r=x['pending']
        if r is None or x['phase']!='accepted' or lease!=x['lease'] or producer_ref!=x['producer_ref']:raise ValueError('actual source word identity required')
        if type(clock_edge)is not int or clock_edge<=0 or (x['receipts'] and clock_edge<=x['receipts'][-1]['edge']):raise ValueError('ordered positive SRAM edges')
        if x['write']:
            if w_ce_accepted is not True or r_ce_captured is not False or rdata is not None:raise ValueError('actual SRAM write edge required')
        else:
            if r_ce_captured is not True or w_ce_accepted is not False or not isinstance(rdata,bytes) or len(rdata)!=32:raise ValueError('actual256bit SRAM capture required')
        x['receipts'].append(dict(edge=clock_edge,data=rdata));x['next']+=1;x['pending']=None
        if x['next']==(1 if x['size']<=32 else x['size']//32):x['phase']='complete'
    def visible(self,bank,ticket,lease):
        x=self.owner(bank,ticket)
        if x['phase']!='complete' or lease!=x['lease']:raise ValueError('all words complete before visibility')
        x['phase']='visible'
        if x['producer']=='GU':return dict(commit_v=True,commit_id=x['GU']['id'],commit_row=x['GU']['row'],commit_epoch=x['GU']['epoch'],column=x['GU']['column'])
        if not x['write']:
            data=b''.join(r['data']for r in x['receipts']);offset=x['address']%32 if x['size']<32 else 0
            return data[offset:offset+x['size']]
    def consume(self,bank,ticket):
        x=self.owner(bank,ticket)
        if x['phase']!='visible':raise ValueError('visibility acceptance required')
        x['phase']='consumed'
    def reverse(self,bank,ticket,*,grant):
        x=self.owner(bank,ticket)
        if x['phase']!='consumed' or grant is not True:raise ValueError('reverse retirement required')
        del self.live[bank]

class JoinedGateway:
    """Compose bank reservation, actual H1 idle observation and retirement.

    This drives a software port contract only. It provides no installed source
    inventory and cannot admit hardware; physical producers must use it too.
    """
    def __init__(self,fence,SM):
        uint(SM,5,'SM')
        if SM//8!=fence.stack:raise ValueError('source quadrant')
        self.fence=fence;self.SM=SM;self.drain=DrainGate();self.bank=None;self.ticket=None
    def submit(self,ticket,**kwargs):
        if self.drain.phase!='idle':raise ValueError('one SM gateway command')
        if type(ticket)is not tuple or len(ticket)!=5 or ticket[4]!=self.SM:raise ValueError('source SM owner')
        self.fence.reserve(ticket,**kwargs)
        self.drain.request(ticket);self.bank=kwargs['bank'];self.ticket=ticket
    def sample(self,pins):return self.drain.sample(pins)
    def word_request(self,**kwargs):
        if self.drain.phase!='owned':raise ValueError('H1 old consumers have not drained')
        return self.fence.word_request(self.bank,self.ticket,**kwargs)
    def capture(self,**kwargs):
        if self.drain.phase!='owned':raise ValueError('source owner not acquired')
        self.fence.capture(self.bank,self.ticket,**kwargs)
    def visible(self,lease):return self.fence.visible(self.bank,self.ticket,lease)
    def consume(self):self.fence.consume(self.bank,self.ticket)
    def retire(self,*,all_completion_sinks_drained,reverse_grant):
        x=self.fence.owner(self.bank,self.ticket)
        if x['phase']!='consumed' or self.drain.phase!='owned' or all_completion_sinks_drained is not True or reverse_grant is not True:raise ValueError('atomic bank/SM retirement guard')
        self.drain.release(self.ticket,all_completion_sinks_drained=True,reverse_grant=True)
        self.fence.reverse(self.bank,self.ticket,grant=True);self.bank=None;self.ticket=None
    def bulk_response(self,packet):
        if set(packet)!={'rsp_v','rsp_tag','rsp_data'} or type(packet['rsp_v'])is not bool or not isinstance(packet['rsp_data'],bytes) or len(packet['rsp_data'])!=128:raise ValueError('source bulk response pins')
        uint(packet['rsp_tag'],10,'source bulk tag')
        return packet

def build():
    manifest,b=sources();text={p:v.decode()for p,v in b.items()if p.endswith('.sv')}
    checks={'rtl/gpu/ot_gpu_full_sm_service.sv':['assign host_rd_ready=idle && !choose_simd && rr','assign host_wr_ready=idle && !choose_simd && wr','assign simd_done=state==DONE'],
        'rtl/gpu/ot_gpu_rf_service.sv':['!read_pending && !rsp_valid && !ack_valid','if(write_go) begin ack_valid<=1','wr_addr[8:7]'],
        'rtl/gpu/ot_gpu_scratch_service.sv':['rst_n && !pending && !done','else if(done && done_ready) done<=0'],
        'rtl/gpu/ot_gpu_qwen_gu64_l2.sv':['input wire commit_v','if(l2_v && !l2_ready)','commit_epoch==epoch[commit_id] && commit_row==row[commit_id]'],
        'rtl/gpu/ot_gpu_bulk_copy.sv':['input  wire                  rsp_v','if (rsp_v) ring[rsp_tag] <= rsp_data']}
    for p,tokens in checks.items():
        if any(t not in text[p]for t in tokens):raise ValueError('source endpoint ABI mismatch '+p)
    ctx=json.loads(b['results/uarch/h4_hbm_service_context_g0_20261002/final/model.json'])
    #16 GU AR-column producers at each SM arbitrate locally before the slice.
    #32 data +18 row +16 epoch +4 entry +4 column +2 control =76 bits.
    local_mux_bits=15*76;local_gates=4*local_mux_bits+256
    local_logic=local_gates*.3+128*.2916;local_footprint=2*local_logic
    #8 existing256bit owner slots hold C0/GU/KV; no640-entry range CAM.
    fields=dict(ticket=128,epoch=16,canonical_row=18,entry_id=4,column=4,producer_class=2,bank=3,byte_offset=18,length=8,write=1,state=4,provider_tag=16,word_receipt_mask=4)
    request_bits=128+42+18+3+2+4;reverse_bits=128+42+2+2
    added_tracks=8*(request_bits+reverse_bits);total_tracks=2368+added_tracks
    models={}
    for name,key in [('Qwen','qwen'),('DeepSeek','deepseek')]:
        c=ctx['models'][name];fp=json.loads(b['results/uarch/qwen_hbm_interface_geometry_20261002/'+key+'_floorplan_r11.json'])
        controllers=[]
        for old in c['L2_controller_slots']:
            box=list(old['bbox_um'])
            # Endpoint owner compares, address decoder, scalar-mask decode,
            # and256bit bank data/control steering, priced conservatively.
            endpoint_gates=8*(256*4+128*2+64)
            extra=2*(endpoint_gates*.3+8*64*.2916)
            required=old['controller_footprint_um2']+extra
            label=['s0','s1','n0','n1'][old['stack']];region=next(x for x in fp['regions']if x['name']=='l2_'+label)
            halos=[]
            for p in fp['macro_placements']:
                if not p['name'].startswith('l2_'+label+'_m'):continue
                a=[p['x']-4,p['y']-4,p['x']+174.744+4,p['y']+70.47+4]
                if max(a[0],box[0])<min(a[2],box[2]) and max(a[1],box[1])<min(a[3],box[3]):halos.append(p['name'])
            contained=box[0]>=region['x'] and box[1]>=region['y'] and box[2]<=region['x']+region['w'] and box[3]<=region['y']+region['h']
            cut=dict(old['cuts'][0]);cut.update(demand_tracks=total_tracks,margin_tracks=cut['signal_capacity_tracks']-total_tracks,screen_pass=cut['signal_capacity_tracks']>=total_tracks)
            controllers.append(dict(stack=old['stack'],bbox_um=box,capacity_um2=512*64,required_footprint_um2=required,macro_halo_conflicts=halos,fit=contained and not halos and required<=512*64,cut=cut))
        residual=c['area']['actual_reserved_strip_residual_um2_per_SM']-c['area']['incremental_connector_footprint_um2_per_SM']
        local_slots=[dict(SM=s['SM'],bbox_um=[s['bbox_um'][0],s['bbox_um'][3],s['bbox_um'][2],s['bbox_um'][3]+local_footprint/1400])for s in c['SM_connector_slots']]
        models[name]=dict(SMs=32,SM_additional_local_GU_mux_footprint_um2=local_footprint,SM_remaining_strip_capacity_um2=residual,SM_local_mux_slots=local_slots,SM_fit=local_footprint<=residual,L2_controller_slots=controllers,source_SM_adapter=c['source_cut_owner_adapter'],full_reserved_die_mm2=c['area']['full_die_reserved_occupancy_mm2'],new_SRAM_macros=0,old_SRAM_or_provider_cost_recharged=False,area_and_constructive_cut_screen_pass=local_footprint<=residual and all(x['fit']and x['cut']['screen_pass']for x in controllers),installed_endpoint=False,hardware_admitted=False)
    return dict(schema='opentallas.HBM.atomic-source-G0.v1',enabled_default=False,source_main=manifest['source_main'],source_manifest_sha256=MANIFEST_SHA,source_ports_verified=True,models=models,owner_slot_fields_bits=fields,owner_slot_total_bits=sum(fields.values()),owner_slot_capacity_bits=256,bank_owners_per_slice=8,scalar_mux_GU_producers_per_SM=16,local_GU_mux_gate_equivalents=local_gates,
        source_connections=dict(RF='existing C0/V1 sole host data path; gate host/SIMD valids, retain prior rsp/ACK/done sinks during drain; no new4096bit crossbar',shared='same owner drives scratch_valid/write/addr/wdata; sample scratch_ready/done; retain done_ready for prior accepted command',GU='16source AR columns arbitrate locally; accepted l2_v&&l2_ready must acquire bank owner first; hold source packet stable until accepted; commit_v/id/row/epoch only after actual write edge',L2='new generic SRAM256bit adapter required: one request word per bank, held return, four-word line publication; source injectors are sizing only and no installed generic module exists',KV='actual mutable provider must enter same bank fence; any writer bypass refuses admission',bulk='rsp_v/tag/data always passed unchanged independently; source has no ready port'),
        latency_contract=dict(bank_parallelism=8,same_bank_even_nonoverlap_serialized=True,line_word_transactions=4,scalar_word_transactions=1,line_read_leaf_edges=12,line_write_leaf_edges=8,scalar_write_leaf_edges=2,local_GU_arbitration_positive_provisional_ticks=1,max_other_column_packets_ahead=15,actual_backend_stall_bound=None,actual_Dewey_interval_join=False,automatic_delta=False,whole_token_ns=None,RF_I64_RMW_C0_recharged=False,selected_clock_GHz=1.2,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25),
        admission='FAIL_PHYSICAL_SOURCE_BINDING',implementation_allowed=False,blockers=['No installed atomic gateway/genericL2endpoint yet; candidate port contract only','GU descriptor canonical/local-row and full-generation mapping require actual producer ownership binding; do not infer from scalar FIFO epoch alone','KV source writers must bind fence; all old accepted returns/ACKs drain before generation reuse','actual parent FF/cone placement and exhaustive cuts, PG/vias and clock bindings remain absent','bank serialization and GU local arbitration require actual whole-program event interval composition before G0 implementation admission'],no_RTL_or_PnR=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
    b=(json.dumps(build(),indent=2,sort_keys=True)+'\n').encode();pins={s:sha((ROOT/s).read_bytes())for s in ['tools/h4_hbm_atomic_source_g0.py','tests/test_h4_hbm_atomic_source_g0.py']}
    if a.verify:
        if (a.out/'model.json').read_bytes()!=b or json.loads((a.out/'source_pins.json').read_text())!=pins:raise ValueError('source contract replay mismatch')
        print('PASS_EXACT_ATOMIC_SOURCE_G0_REPLAY');return
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'model.json').write_bytes(b);(a.out/'source_pins.json').write_text(json.dumps(pins,sort_keys=True,indent=2)+'\n')
    print('ATOMIC_SOURCE_G0_RECORDED_NO_IMPLEMENTATION_ADMISSION')
if __name__=='__main__':main()
