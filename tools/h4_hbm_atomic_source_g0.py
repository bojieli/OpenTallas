#!/usr/bin/env python3
"""Pinned H1/shared/GU endpoint contract and finite bank-fence G0 model.

Models source port handshakes and opaque SRAM words, without numerical oracles.
Candidate gateway wiring is not installed RTL. Full physical admission remains
mandatory before implementation; no provisional calendar delta is inserted.
"""
import argparse
from collections import deque
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'results/uarch/h4_hbm_atomic_source_g0_20261002'
MANIFEST_SHA='a268a11140e2b8ddab97122c64653550e835296f6f178d35228ca3023eca9eb3'

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
        self.model=model;self.rank=rank;self.stack=stack;self.live={};self.watermark={};self.GU_epochs={}
    def bind_GU(self,ticket,*,epoch,free_row_credits):
        if self.model!='Qwen' or type(ticket)is not tuple or len(ticket)!=5 or any(type(v)is not int for v in ticket):raise ValueError('Qwen full-generation source frame required')
        gen,pc,seq,rank,sm=ticket;uint(epoch,16,'GU epoch')
        if not 0<gen<2**64 or not 0<=pc<1737 or not 0<seq<2**40 or rank!=self.rank or not 0<=sm<32 or sm//8!=self.stack:raise ValueError('GU source frame extent')
        if type(free_row_credits)is not list or len(free_row_credits)!=16 or any(type(c)is not int or c!=16 for c in free_row_credits):raise ValueError('all16 GU column source FIFOs must be fully drained')
        if any(x['ticket'][3:]==ticket[3:]for x in self.live.values()):raise ValueError('all source bank owners must drain before epoch reuse')
        if sm in self.GU_epochs and (gen,seq)<=(self.GU_epochs[sm]['frame'][0],self.GU_epochs[sm]['frame'][2]):
            raise ValueError('stale GU source frame')
        self.GU_epochs[sm]=dict(frame=ticket,epoch=epoch)
    def reserve(self,ticket,*,producer,bank,address,size,write,lease,producer_ref,GU=None):
        if type(ticket)is not tuple or len(ticket)!=5 or any(type(x)is not int for x in ticket):raise ValueError('source owner tuple')
        gen,pc,seq,rank,sm=ticket;uint(gen,64,'generation');uint(seq,40,'sequence');uint(sm,5,'SM')
        if not gen or not seq or rank!=self.rank or sm//8!=self.stack or not 0<=pc<(1737 if self.model=='Qwen' else 2213):raise ValueError('source owner extent')
        uint(bank,3,'producer bank')
        if producer not in ('C0','GU','KV','DS_ROW') or type(write)is not bool or not isinstance(lease,str) or not lease or not isinstance(producer_ref,str) or not producer_ref:raise ValueError('bound producer and lease required')
        if type(address)is not int or type(size)is not int or size not in (4,32,64,128) or address<0 or address%size or address+size>262144:raise ValueError('actual bank extent and alignment')
        if producer=='C0' and size!=128:raise ValueError('C0 line128')
        if ticket in (x['ticket']for x in self.live.values()):raise ValueError('same owner already holds a bank')
        if bank in self.live:raise ValueError('bank owner busy, even for nonoverlapping range')
        key=(producer,sm)
        if (gen,seq)<=self.watermark.get(key,(0,0)):raise ValueError('stale producer sequence')
        if producer=='GU':
            if self.model!='Qwen':raise ValueError('DS does not inherit Qwen GU ready/epoch protocol')
            if not write or size!=4 or bank!=sm%8 or not isinstance(GU,dict):raise ValueError('GU source scalar producer mapping')
            if set(GU)!={'epoch','mapped_epoch','row','partition_base','local_row','id','column'}:raise ValueError('complete GU descriptor mapping required')
            for n,b in [('epoch',16),('mapped_epoch',16),('row',18),('partition_base',18),('local_row',16),('id',4),('column',4)]:uint(GU[n],b,'GU '+n)
            if GU['row']!=GU['partition_base']+GU['local_row'] or GU['epoch']!=GU['mapped_epoch'] or address!=4*GU['local_row']:raise ValueError('GU row/epoch/physical home mismatch')
            binding=self.GU_epochs.get(sm)
            if binding is None or binding['frame'][0:2]!=ticket[0:2] or binding['frame'][3:]!=ticket[3:] or seq<binding['frame'][2] or GU['epoch']!=binding['epoch']:raise ValueError('actual full-generation GU epoch binding required')
        elif GU is not None:raise ValueError('foreign GU descriptor')
        if producer=='DS_ROW' and (self.model!='DeepSeek' or not write or size!=4 or bank!=sm%8):raise ValueError('DS actual row packet writer required')
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
        x['receipts'].append(dict(edge=clock_edge,data=rdata,write_data=r['wdata']));x['next']+=1;x['pending']=None
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

class DSResultFrame:
    """Reserve all4096 real512bit records before unbackpressured source start.

    Eight32KiB1R1W macros hold the frame; two256bit words write each accepted
    rv edge. The source arithmetic never stalls on a fabricated result-ready.
    Actual row ids accompany opaque NC<=8 FP32 words; there is no numerical
    host callback and no reuse of shared/compiler scratch storage.
    """
    def __init__(self):self.ticket=None;self.queue=deque();self.seen=set();self.last=(0,0)
    def start(self,ticket,*,op_rows,NC,source_busy,home):
        if self.ticket is not None or self.queue or source_busy is not False:raise ValueError('reserve entire frame before actual source start')
        if type(ticket)is not tuple or len(ticket)!=5 or any(type(v)is not int for v in ticket):raise ValueError('DS full owner tuple')
        g,pc,s,r,sm=ticket
        if not 0<g<2**64 or not 0<s<2**40 or not 0<=pc<2213 or not 0<=r<96 or not 0<=sm<32 or (g,s)<=self.last:raise ValueError('DS owner extent/stale frame')
        if type(op_rows)is not int or not 0<op_rows<=4096 or type(NC)is not int or not 0<NC<=8:raise ValueError('sourceRMAX4096/NC8 envelope')
        if not isinstance(home,dict) or set(home)!={'bank','base','extent','column_stride','lease','provider_ref'}:raise ValueError('actual DS result home required')
        if any(type(home[n])is not int for n in ('bank','base','extent','column_stride')) or home['bank']!=sm%8 or home['base']<0 or home['base']%4 or home['column_stride']%4 or home['column_stride']<op_rows*4 or home['extent']<NC*home['column_stride'] or home['base']+home['extent']>262144 or not all(isinstance(home[n],str) and home[n]for n in ('lease','provider_ref')):raise ValueError('actual bounded disjoint DS column homes')
        self.home=dict(home)
        self.ticket=ticket;self.rows=op_rows;self.NC=NC;self.captured=0;self.retired=0;self.column=0;self.seen=set();self.last=(g,s)
    def capture(self,ticket,*,rv,rrow,rdata,fault):
        if ticket!=self.ticket or self.ticket is None or type(rv)is not bool or type(fault)is not bool:raise ValueError('actual source owner/rv/fault pins')
        if not rv:return None
        if type(rrow)is not int or not 0<=rrow<self.rows or rrow in self.seen or self.captured>=self.rows:raise ValueError('unique actual row within reserved frame')
        if not isinstance(rdata,bytes) or len(rdata)!=4*self.NC:raise ValueError('actual NC*32 source result bits')
        ordinal=self.captured
        value=int.from_bytes(rdata,'little')|(rrow<<256)|(ordinal<<268)|(int(fault)<<280)|(self.NC<<281)|(1<<285)
        self.queue.append(value.to_bytes(64,'little'));self.seen.add(rrow);self.captured+=1
        return dict(macros=['DS_result.p'+str(ordinal//1024)+'.half'+str(h)for h in range(2)],row=ordinal%1024,write_words=2,write_bytes=64,ordinal=ordinal)
    def head(self):
        if not self.queue:raise ValueError('no accepted source row')
        record=self.queue[0];v=int.from_bytes(record,'little')
        rrow=(v>>256)&4095
        return dict(rrow=rrow,ordinal=(v>>268)&4095,fault=bool((v>>280)&1),column=self.column,data=record[self.column*4:self.column*4+4],address=self.home['base']+self.column*self.home['column_stride']+4*rrow,lease=self.home['lease'],producer_ref=self.home['provider_ref']+':DS-frame:'+repr(self.ticket)+':'+str(self.retired)+':'+str(self.column))
    def ack_column(self,fence,bank,bank_ticket,*,reverse_grant):
        h=self.head();x=fence.owner(bank,bank_ticket)
        if reverse_grant is not True or x['phase']!='consumed' or x['producer']!='DS_ROW' or x['producer_ref']!=h['producer_ref'] or bank!=self.home['bank'] or x['address']!=h['address'] or x['lease']!=h['lease'] or not x['receipts'] or x['receipts'][-1]['write_data']!=h['data']*8 or bank_ticket[0]!=self.ticket[0] or bank_ticket[1]!=self.ticket[1] or bank_ticket[3:]!=self.ticket[3:]:raise ValueError('actual matching bank visible/consumer/reverse proof required')
        fence.reverse(bank,bank_ticket,grant=True);self.column+=1
        if self.column==self.NC:self.queue.popleft();self.retired+=1;self.column=0
    def finish(self,ticket,*,source_busy):
        if ticket!=self.ticket or self.ticket is None or source_busy is not False or self.captured!=self.rows or self.retired!=self.rows or self.queue:raise ValueError('all actual source rows/columns and old source drained')
        self.ticket=None

def build():
    manifest,b=sources();text={p:v.decode()for p,v in b.items()if p.endswith('.sv')}
    checks={'rtl/gpu/ot_gpu_full_sm_service.sv':['assign host_rd_ready=idle && !choose_simd && rr','assign host_wr_ready=idle && !choose_simd && wr','assign simd_done=state==DONE'],
        'rtl/gpu/ot_gpu_rf_service.sv':['!read_pending && !rsp_valid && !ack_valid','if(write_go) begin ack_valid<=1','wr_addr[8:7]'],
        'rtl/gpu/ot_gpu_scratch_service.sv':['rst_n && !pending && !done','else if(done && done_ready) done<=0'],
        'rtl/gpu/ot_gpu_qwen_gu64_l2.sv':['input wire commit_v','output wire [4:0] free_row_credits','if(l2_v && !l2_ready)','commit_epoch==epoch[commit_id] && commit_row==row[commit_id]'],
        'rtl/gpu/ot_gpu_bulk_copy.sv':['input  wire                  rsp_v','if (rsp_v) ring[rsp_tag] <= rsp_data'],
        'rtl/gpu/ot_gpu_sm_v.sv':['parameter integer NC   = 8','parameter integer RMAX = 4096','output reg                     rv','output reg  [NC*32-1:0]        rdata'],
        'rtl/gpu/ot_gpu_sm.sv':['output reg                     rv','output reg  [NC*32-1:0]        rdata'],
        'rtl/gpu/ot_gpu_sm_bd.sv':['output reg                     rv','output reg  [NC*32-1:0]        rdata']}
    for p,tokens in checks.items():
        if any(t not in text[p]for t in tokens):raise ValueError('source endpoint ABI mismatch '+p)
    ctx=json.loads(b['results/uarch/h4_hbm_service_context_g0_20261002/final/model.json']);expanded=json.loads(b['results/uarch/h4_v1_expanded_service_20261002/private_routes_r4/model.json'])
    #16 GU AR-column producers at each SM arbitrate locally before the slice.
    #32 data +18 row +16 epoch +4 entry +4 column +2 control =76 bits.
    local_mux_bits=15*76;local_gates=4*local_mux_bits+256
    local_logic=local_gates*.3+(128+80)*.2916;local_footprint=2*local_logic
    DS_state_bits=4096+512+128+512+64+8
    DS_control_footprint=2*(DS_state_bits*.2916+4096*.3)
    #8 existing256bit owner slots hold C0/GU/KV; no640-entry range CAM.
    fields=dict(ticket=128,epoch=16,canonical_row=18,entry_id=4,column=4,producer_class=2,bank=3,byte_offset=18,length=8,write=1,state=4,provider_tag=16,word_receipt_mask=4)
    request_bits=128+42+18+3+2+4;reverse_bits=128+42+2+2
    added_tracks=8*(request_bits+reverse_bits);total_tracks=2368+added_tracks
    models={}
    for name,key in [('Qwen','qwen'),('DeepSeek','deepseek')]:
        c=ctx['models'][name];fp=json.loads(b['results/uarch/qwen_hbm_interface_geometry_20261002/'+key+'_floorplan_r11.json'])
        tw,th=expanded['models'][name]['SM_tile_um']
        source_hops=math.ceil((tw+th)*.81/(1000/1.2-60))
        source_pipeline_bits=2*source_hops*1024
        source_pipeline_footprint=2*source_pipeline_bits*.2916
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
        this_local=local_footprint+source_pipeline_footprint+(DS_control_footprint if name=='DeepSeek' else 0)
        local_slots=[dict(SM=s['SM'],bbox_um=[s['bbox_um'][0],s['bbox_um'][3],s['bbox_um'][2],s['bbox_um'][3]+local_footprint/1400])for s in c['SM_connector_slots']]
        for s in local_slots:s['bbox_um'][3]=s['bbox_um'][1]+this_local/1400
        local_cuts=[]
        template=expanded['models'][name]['service']['C0_cuts'][0]
        for s in local_slots:
            layers={};lo,hi=s['bbox_um'][0]*1000,s['bbox_um'][2]*1000
            for layer,g in template['layers'].items():
                raw=max(0,math.floor((hi-g['origin_DBU'])/g['pitch_DBU'])-max(0,math.ceil((lo-g['origin_DBU'])/g['pitch_DBU']))+1)
                layers[layer]=dict(raw_tracks=raw,signal_tracks=raw//2,PG_clock_via_reserved_tracks=raw-raw//2,pitch_DBU=g['pitch_DBU'],origin_DBU=g['origin_DBU'])
            capacity=sum(x['signal_tracks']for x in layers.values());demand=template['demand_tracks']+16*76+80+1024
            local_cuts.append(dict(SM=s['SM'],axis='X',coordinate_um=s['bbox_um'][1],span_um=[s['bbox_um'][0],s['bbox_um'][2]],layers=layers,demand_tracks=demand,signal_capacity_tracks=capacity,margin_tracks=capacity-demand,screen_pass=capacity>=demand,actual_new_PDN_bound=False))
        DS_macros=[];DS_cuts=[]
        if name=='DeepSeek':
            for slot in c['source_SM_placement_adapter']:
                ox,oy=slot['service_origin_um']
                for n in range(8):
                    x=ox+(n%4)*450;y=oy+(n//4)*508+304
                    DS_macros.append(dict(SM=slot['SM'],name='DS_result.p'+str(n//2)+'.half'+str(n%2),bank_slot=n,body_bbox_um=[x+4,y+4,x+178.744,y+74.47],halo_bbox_um=[x,y,x+182.744,y+78.47],master='ot_sram_1r1w_1024x256_m2_r2c2',OBS_layers=['M1','M2','M3','M4'],physical_write_bits=256))
                    #A512bit record uses two of these macros, positive finite
                    #word controls/addresses and return; no512bit broadcast.
                    bank_cuts=[x for x in expanded['models'][name]['service']['bank_cuts']if x['owner'].startswith('bank'+str(n)+'/')]
                    cap=min(x['signal_capacity_tracks']for x in bank_cuts);old_demand=max(x['demand_tracks']for x in bank_cuts)
                    DS_cuts.append(dict(SM=slot['SM'],bank_slot=n,extra_demand_tracks=512+128,existing_bank_cut_upper_tracks=old_demand,composed_demand_tracks=old_demand+640,minimum_existing_bank_signal_capacity_tracks=cap,margin_tracks=cap-old_demand-640,screen_pass=cap>=old_demand+640,actual_PDN_or_pin_escape_bound=False))
        conflicts=[]
        service=expanded['models'][name]['service']
        def overlap(a,z):return max(a[0],z[0])<min(a[2],z[2]) and max(a[1],z[1])<min(a[3],z[3])
        for new in DS_macros:
            slot=next(x for x in c['source_SM_placement_adapter']if x['SM']==new['SM']);ox,oy=slot['service_origin_um'];a=new['halo_bbox_um']
            for old in service['macro_placements']:
                z=old['halo_bbox_um'];z=[z[0]+ox,z[1]+oy,z[2]+ox,z[3]+oy]
                if overlap(a,z):conflicts.append([new['SM'],new['name'],old['name']])
            for old in service['logic_slots']:
                z=old['bbox_um'];z=[z[0]+ox,z[1]+oy,z[2]+ox,z[3]+oy]
                if overlap(a,z):conflicts.append([new['SM'],new['name'],'logic'+str(old['bank'])])
            if not(ox<=a[0] and oy<=a[1] and a[2]<=ox+service['width_um'] and a[3]<=oy+service['height_um']):conflicts.append([new['SM'],new['name'],'service bounds'])
        models[name]=dict(SMs=32,SM_additional_local_GU_mux_footprint_um2=local_footprint,DS_frame_controller_footprint_um2_per_SM=DS_control_footprint if name=='DeepSeek' else 0,SM_remaining_strip_capacity_um2=residual,SM_local_mux_slots=local_slots,SM_gateway_endpoint_cuts=local_cuts,SM_fit=this_local<=residual,L2_controller_slots=controllers,DS_result_macros=DS_macros,DS_result_macro_logic_conflicts=conflicts,DS_result_endpoint_cuts=DS_cuts,DS_frame_bytes_per_SM=262144 if name=='DeepSeek' else 0,source_SM_adapter=c['source_cut_owner_adapter'],full_reserved_die_mm2=c['area']['full_die_reserved_occupancy_mm2'],new_SRAM_macros=len(DS_macros),old_SRAM_or_provider_cost_recharged=False,area_and_constructive_cut_screen_pass=this_local<=residual and not conflicts and all(x['fit']and x['cut']['screen_pass']for x in controllers)and all(x['screen_pass']for x in local_cuts+DS_cuts),source_body_pipeline=dict(max_L1_um=tw+th,provisional_hops=source_hops,registered_bits=source_pipeline_bits,footprint_um2_per_SM=source_pipeline_footprint,assumed_ps_per_um=.81,actual_SS_macro_clk_to_q_ps=None,actual_placed_source_cones_bound=False,route_cost_already_charged_unknown=True,automatic_latency_delta=False),installed_endpoint=False,hardware_admitted=False)
    return dict(schema='opentallas.HBM.atomic-source-G0.v1',enabled_default=False,source_main=manifest['source_main'],source_manifest_sha256=MANIFEST_SHA,source_ports_verified=True,models=models,owner_slot_fields_bits=fields,owner_slot_total_bits=sum(fields.values()),owner_slot_capacity_bits=256,bank_owners_per_slice=8,scalar_mux_GU_producers_per_SM=16,local_GU_mux_gate_equivalents=local_gates,
        source_connections=dict(RF='existing C0/V1 sole host data path; gate host/SIMD valids, retain prior rsp/ACK/done sinks during drain; no new4096bit crossbar',shared='same owner drives scratch_valid/write/addr/wdata; sample scratch_ready/done; retain done_ready for prior accepted command',GU='Qwen only:16source AR columns arbitrate locally; accepted l2_v&&l2_ready must acquire bank owner first; hold source packet stable until accepted; commit_v/id/row/epoch only after actual write edge',DS='actual ot_gpu_sm_v NC8/RMAX4096 unbackpressured rv/rrow/rdata: reserve256KiB physical512bit row frame before start; eight32KiB macros perSM in free lower-left bank subslots; no fictitious result-ready; frame fully drained before next start',L2='new generic SRAM256bit adapter required: one request word per bank, held return, four-word line publication; source injectors are sizing only and no installed generic module exists',KV='actual mutable provider must enter same bank fence; any writer bypass refuses admission',bulk='rsp_v/tag/data always passed unchanged independently; source has no ready port'),
        latency_contract=dict(bank_parallelism=8,same_bank_even_nonoverlap_serialized=True,line_word_transactions=4,scalar_word_transactions=1,line_read_leaf_edges=12,line_write_leaf_edges=8,scalar_write_leaf_edges=2,DS_frame_accept_B_per_cycle=64,DS_frame_macro_writes_per_row=2,DS_frame_read_macro_transactions_per_row=2,DS_frame_read_provisional_ticks=3,DS_scalar_bank_writes_per_source_row_NC8=8,DS_output_reverse_and_frame_retirement_required=True,local_GU_arbitration_positive_provisional_ticks=1,max_other_column_packets_ahead=15,actual_backend_stall_bound=None,actual_Dewey_interval_join=False,automatic_delta=False,whole_token_ns=None,RF_I64_RMW_C0_recharged=False,selected_clock_GHz=1.2,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25),
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
