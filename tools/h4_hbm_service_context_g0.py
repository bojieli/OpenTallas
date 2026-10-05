#!/usr/bin/env python3
"""Complete32SM RF/shared/L2 service context and finite atomic connector G0.

Analytical reservation and executable ownership/byte-movement contracts only.
No native build, engine RTL, P&R, numerical callback or timing qualification.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import h4_v1_g0_model as V
import h4_v1_expanded_service as E
ROOT=Path(__file__).resolve().parents[1]
EXPANDED='4885f71d419c8a14443377b399c148459e05584a'
EP='results/uarch/h4_v1_expanded_service_20261002/private_routes_r4/model.json'
L2PIN='5df5be3336f34998dad44b5ad3efc8477879f1d8'
L2PATH='results/uarch/qwen_hbm_connected_20261001/L2_injector_before_RTL_r2.json'
MODEL_PHASES=['accepted','provider_complete','visible_ACK','consumer_accept','reverse_grant','retire']


def finite(value,lower,upper,label):
    if type(value)is not int or not lower<=value<upper:raise ValueError(label)
    return value


def source_SM(slot):
    """Map the geometrical8x4 slot to the actual contiguous8-client quadrant."""
    finite(slot,0,32,'geometrical slot');row,col=divmod(slot,8)
    stack=(row//2)*2+col//4;local=(row%2)*4+col%4
    return dict(geometric_slot=slot,SM=8*stack+local,stack=stack,producer_bank=local,
                weight_client=8*stack+local,L2_vector_KV_client=32+stack)


def shared_address(byte_address,size=64):
    if type(byte_address)is not int or size!=64 or byte_address<0 or byte_address%64 or byte_address+64>65536:raise ValueError('actual shared64B aligned10bit beat required')
    return dict(beat=byte_address//64,bank_words=[0,1],word_bits=256)


def L2_words(bank,byte_address,size=128):
    finite(bank,0,8,'actual producer bank')
    if type(byte_address)is not int or size!=128 or byte_address<0 or byte_address%128 or byte_address+128>262144:raise ValueError('actual L2 bank128B line and extent required')
    return [dict(bank=bank,macro=(byte_address//32+i)//1024,row=(byte_address//32+i)%1024,bytes=32,word_ordinal=i)for i in range(4)]


def service_cost(kind,*,write=False,request_hops,response_hops,stall_bound,commands_ahead=0):
    for v in (request_hops,response_hops,stall_bound,commands_ahead):finite(v,0,2**64,'finite explicit route/stall/queue bound')
    if kind not in ('shared64','L2_128') or type(write)is not bool:raise ValueError('supported physical service kind required')
    words=1 if kind=='shared64' else 4
    payload_beats=1 if kind=='shared64' else 2
    leaf=words*(2 if write else 3)
    fixed=2+request_hops+payload_beats+leaf+response_hops+2+2
    return dict(kind=kind,write=write,leaf_transactions=words,payload64B_beats=payload_beats,leaf_no_stall_ticks=leaf,
                no_stall_ticks=fixed,bounded_ticks=(commands_ahead+1)*(fixed+words*stall_bound),
                request_hops=request_hops,response_hops=response_hops,clock_qualified=False,
                RF_I64_RMW_recharged=False,C0_front_recharged=False,
                cost_scope='standalone service demand; reconcile existing Dewey provider interval before insertion, not automatic delta')


class SliceSeats:
    """Share the existing KV/L2 client's512 seats, preserving36client16bit tags.

    Weight clients0..31 and their unbackpressured returns are never masked.
    New C0 requests use at most8 of a slice's512 existing seats, not8 extra.
    """
    def __init__(self,stack):
        finite(stack,0,4,'stack');self.stack=stack;self.active={};self.c0={};self.ranges={}
    def reserve(self,owner,kind,*,bank_range=None,write=False):
        if kind not in ('C0','KV') or not isinstance(owner,(str,tuple)):raise ValueError('source service class and hashable owner identity')
        if owner in self.active.values():raise ValueError('owner already has a seat')
        if kind=='C0':
            if not isinstance(owner,tuple) or len(owner)!=5 or any(type(v)is not int for v in owner) or not 0<=owner[4]<32 or owner[4]//8!=self.stack:raise ValueError('source producer quadrant required')
            if len(self.c0)>=8 or any(t[3:]==owner[3:]for t in self.c0):raise ValueError('one C0 service seat per source SM')
        if bank_range is not None:
            bank,lo,hi=bank_range
            finite(bank,0,8,'producer range bank');finite(lo,0,262144,'range start');finite(hi,1,262145,'range end')
            if hi<=lo or type(write)is not bool:raise ValueError('physical range/mode')
            for _,(b,a,z,w)in self.ranges.items():
                if b==bank and max(a,lo)<min(z,hi) and (w or write):raise ValueError('actual producer range already leased')
        if len(self.active)>=512:raise ValueError('existing512 seat capacity exhausted')
        tag=next(t for t in range(512)if t not in self.active)
        self.active[tag]=owner
        if kind=='C0':self.c0[owner]=tag
        if bank_range is not None:self.ranges[owner]=(*bank_range,write)
        return ((32+self.stack)<<10)|tag
    def check(self,owner,tag):
        if type(tag)is not int or tag>>10!=32+self.stack or self.active.get(tag&1023)!=owner:raise ValueError('stale/wrong global provider tag')
    def release(self,owner,tag):
        self.check(owner,tag);del self.active[tag&1023];self.c0.pop(owner,None);self.ranges.pop(owner,None)


class AtomicConnector:
    """Finite source-owned movement connector protocol, without data oracle.

    A caller supplies the real provider home extent, producer ref and lease.
    RF/shared/L2 hardware endpoints remain separately qualified source gates.
    This model only copies opaque bytes after matching backend proof events.
    """
    def __init__(self,*,model,rank,SM,generation,slice_seats):
        if model not in ('Qwen','DeepSeek'):raise ValueError('supported model')
        finite(rank,0,2 if model=='Qwen' else 96,'source rank');finite(SM,0,32,'source SM');finite(generation,1,2**64,'generation')
        if slice_seats.stack!=SM//8:raise ValueError('source slice mapping')
        self.model=model;self.rank=rank;self.SM=SM;self.generation=generation;self.pool=slice_seats
        self.owner=None;self.seq=0;self.trace=[];self.pending={};self.complete_set=set()
    def accept(self,ticket,kind,*,base,extent,byte_address,lease,producer_ref,physical_base,RF_drained,shared_drained,producer_bank=None,producer_stack=None,write=False,payload=None):
        if self.owner is not None:raise ValueError('atomic SM command credit held')
        if RF_drained is not True or shared_drained is not True:raise ValueError('source RF/SIMD/shared accepted returns and ACKs must drain before owner switch')
        if not isinstance(ticket,tuple) or len(ticket)!=5 or any(type(x)is not int for x in ticket):raise ValueError('source C0 owner tuple')
        gen,pc,seq,r,s=ticket
        if (gen,r,s)!=(self.generation,self.rank,self.SM) or not 0<=pc<(1737 if self.model=='Qwen' else 2213) or not self.seq<seq<2**40:raise ValueError('source PC/generation/sequence/SM mismatch')
        if kind not in ('shared64','L2_128') or type(write)is not bool or not isinstance(lease,str) or not lease or not isinstance(producer_ref,str) or not producer_ref:raise ValueError('supported service and actual provider lease/ref required')
        size=64 if kind=='shared64' else 128
        if any(type(x)is not int for x in (base,extent,byte_address)) or base<0 or extent<=0 or not base<=byte_address or byte_address+size>base+extent:raise ValueError('actual source home extent required; no modulo alias')
        capacity=65536 if kind=='shared64' else 262144
        if type(physical_base)is not int or physical_base<0 or physical_base+extent>capacity:raise ValueError('concrete physical home extent required')
        address=physical_base+byte_address-base
        if kind=='shared64':
            if producer_bank is not None or producer_stack is not None:raise ValueError('shared home does not own L2 producer coordinates')
            shared_address(address);words=1
        else:
            finite(producer_bank,0,8,'actual source producer bank required')
            if producer_stack!=self.pool.stack:raise ValueError('cross-slice producer needs separately bound route; unsupported here')
            L2_words(producer_bank,address);words=4
        if write and (not isinstance(payload,bytes)or len(payload)!=size):raise ValueError('opaque exact physical payload required')
        if not write and payload is not None:raise ValueError('read bytes must come from actual provider receipt')
        tag=self.pool.reserve(ticket,'C0',bank_range=(producer_bank,address,address+size),write=write) if kind=='L2_128' else None
        self.word_refs=shared_address(address)if kind=='shared64'else L2_words(producer_bank,address)
        self.owner=ticket;self.seq=seq;self.kind=kind;self.write=write;self.size=size;self.words=words
        self.lease=lease;self.producer=producer_ref;self.producer_bank=producer_bank;self.producer_stack=producer_stack;self.tag=tag;self.phase='accepted';self.payload=payload
        self.pending={};self.complete_set=set();self.trace.append(('accepted',ticket))
        return tag
    def backend_word(self,ticket,ordinal,*,lease,producer_ref,global_tag=None,data=None,committed=False):
        if ticket!=self.owner or self.owner is None or self.phase!='accepted':raise ValueError('stale/foreign/nonaccepted provider owner')
        if lease!=self.lease or producer_ref!=self.producer:raise ValueError('actual provider receipt identity mismatch')
        if self.tag is not None:self.pool.check(ticket,global_tag)
        elif global_tag is not None:raise ValueError('shared provider does not own L2 tag')
        finite(ordinal,0,self.words,'physical word ordinal')
        if ordinal in self.complete_set:raise ValueError('duplicate backend completion')
        if self.write:
            if committed is not True or data is not None:raise ValueError('actual SRAM/backend commit proof required')
        else:
            required=64 if self.kind=='shared64' else 32
            if not isinstance(data,bytes)or len(data)!=required:raise ValueError('actual physical provider response bytes required')
            self.pending[ordinal]=data
        self.complete_set.add(ordinal)
        if len(self.complete_set)==self.words:
            if not self.write:self.payload=b''.join(self.pending[i]for i in range(self.words))
            self.phase='complete';self.trace.append(('provider_complete',ticket))
    def visible(self,ticket,lease):
        if ticket!=self.owner or self.phase!='complete' or lease!=self.lease:raise ValueError('all backend words and matching visibility lease required')
        self.phase='visible';self.trace.append(('visible_ACK',ticket));return self.payload
    def consumer(self,ticket):
        if ticket!=self.owner or self.phase!='visible':raise ValueError('actual visible acceptance required')
        self.phase='consumer';self.trace.append(('consumer_accept',ticket))
    def retire(self,ticket,*,reverse_grant):
        if ticket!=self.owner or self.phase!='consumer' or reverse_grant is not True:raise ValueError('consumer/reverse retirement required')
        if self.tag is not None:self.pool.release(ticket,self.tag)
        self.trace.extend([('reverse_grant',ticket),('retire',ticket)]);self.owner=None;self.phase='idle'
    def unrelated_RF_shared_ready(self):return self.owner is None
    def weight_response_ready_contract(self):return 'No ready port: retained bulk-copy ring always accepts its owned responses; RF/shared lock cannot mask them'


def build():
    prior=V.load(EXPANDED,EP);l2=V.load(L2PIN,L2PATH)
    sources=[(EXPANDED,EP),(EXPANDED,'tools/h4_v1_expanded_service.py'),(L2PIN,L2PATH),
             (V.H1,'rtl/gpu/ot_gpu_full_sm_service.sv'),(V.H1,'rtl/gpu/ot_gpu_rf_service.sv'),(V.H1,'rtl/gpu/ot_gpu_scratch_service.sv'),
             (V.C0,'rtl/gpu/ot_gpu_bulk_copy.sv'),(V.C0,'rtl/gpu/ot_gpu_qwen_gu64_l2.sv'),(V.C0,'tools/uarch_model.py'),(V.C0,'tools/h4_c0_bridge.py')]
    blobs={(c,p):V.pinned(c,p)for c,p in sources}
    if Path(E.__file__).read_bytes()!=blobs[EXPANDED,'tools/h4_v1_expanded_service.py']:
        raise ValueError('expanded geometry helper source pin mismatch')
    scratch=blobs[V.H1,'rtl/gpu/ot_gpu_scratch_service.sv'].decode();bulk=blobs[V.C0,'rtl/gpu/ot_gpu_bulk_copy.sv'].decode()
    if 'input wire [9:0] addr' not in scratch or 'rst_n && !pending && !done' not in scratch or 'input  wire [LINE_BITS-1:0]  rsp_data' not in bulk:raise ValueError('H1 shared/bulk source ABI gate')
    if l2['shape']['macro_count_per_die']!=256 or l2['service_contract']['clients']!=36 or l2['service_contract']['client_credits']!=512:raise ValueError('source L2 resource schema')
    shared_L2_field_bits=dict(shared_request=704,shared_response=704,L2_request=704,L2_response=704,line_assembly=1216,home_receipt=256,state_and_counters=128)
    connector_bits=sum(shared_L2_field_bits.values())
    # Additional mux/control/tag compare and byte-enable expansion are priced,
    # not an unbounded queue or zero-cost full-vector cache interface.
    connector_gates=2048+704*2+128*3+256
    connector_logic=connector_bits*.2916+connector_gates*.3
    slice_bits=8*256+512+9+8*1216
    slice_logic=slice_bits*.2916+(8*128*2+512+256)*.3+1024
    slice_footprint=2*slice_logic+l2['area']['added_controller_footprint_mm2_per_slice']*1e6
    models={}
    for name,key in [('Qwen','Qwen'),('DeepSeek','DS')]:
        m=prior['models'][name];old=V.load('56506fb5bacb993107ff11f7df45f6f03363f667','results/uarch/qwen_hbm_interface_geometry_20261002/'+('qwen'if key=='Qwen'else'deepseek')+'_floorplan_r11.json')
        grid=json.loads(V.pinned(EXPANDED,'results/uarch/h4_v1_expanded_service_20261002/inputs/'+key+'_grid.json'))
        slots=[]
        for tile in m['SM_placements']:
            identity=source_SM(tile['SM']);entry=dict(tile,**{'source_provider_identity':identity});entry['SM']=identity['SM'];slots.append(entry)
        if sorted(t['SM']for t in slots)!=list(range(32)):raise ValueError('source SM permutation')
        strip_capacity=m['area']['C0_strip_spare_before_transport_um2']-m['area']['central_endpoint_footprint_um2'];connector_footprint=2*connector_logic
        controllers=[]
        for stack,label in enumerate(['s0','s1','n0','n1']):
            region=next(r for r in old['regions']if r['name']=='l2_'+label)
            y=region['y']+8 if stack<2 else region['y']+region['h']-8-64
            box=E.rect(region['x']+8,y,512,64)
            macros=[p for p in old['macro_placements']if p['name'].startswith('l2_'+label+'_m')]
            if len(macros)!=64:raise ValueError('source64L2 macros per slice')
            halo_conflicts=[]
            for p in macros:
                halo=[p['x']-4,p['y']-4,p['x']+174.744+4,p['y']+70.47+4]
                if E.overlap(box,halo):halo_conflicts.append(p['name'])
            cuts=[E.cut(grid,'X',box[0],box[2],['M7','M9'],l2['routing']['vector_horizontal_bits'],'L2'+label+'/read_write_owner_bus',y)]
            controllers.append(dict(stack=stack,bbox_um=box,macro_halo_conflicts=halo_conflicts,controller_footprint_um2=slice_footprint,controller_capacity_um2=512*64,fit=slice_footprint<=512*64 and not halo_conflicts,cuts=cuts,
                baseline_Qwen_controller_scope='same32KB1R1W process geometry and explicit candidate controller cost; DS does not inherit GU scalar producer arithmetic qualification',hardware_word_adapter_implemented=False))
        connector_slots=[]
        for tile in slots:
            x,y=tile['service_origin_um'];cx=x+400;cy=y+4*E.BANK_H
            used=m['service']['C0_required_footprint_um2']+m['area']['central_endpoint_footprint_um2']
            box=E.rect(cx,cy+used/1400,1400,connector_footprint/1400)
            slot=E.rect(cx,cy,1400,E.CONTROL_H)
            connector_slots.append(dict(SM=tile['SM'],bbox_um=box,fit=E.contained(box,slot),source_C0_ticket_held_through_reverse=True))
        word_ports=dict(shared_bytes_per_SM=65536,shared64B_beats=1024,shared_macro_count=2,
                        RF_logical_bytes_per_SM=262144,RF_physical_bytes_per_SM=524288,RF_macros_per_SM=128,
                        retained_bulk_ring_bytes_per_SM=131072,retained_bulk_outstanding=512,
                        L2_bytes_per_die=8388608,L2_macros_per_die=256,L2_bytes_per_bank=262144,L2_banks_per_slice=8)
        profile={kind+('_write'if write else'_read'):service_cost(kind,write=write,request_hops=5,response_hops=5,stall_bound=1,commands_ahead=511)for kind in ['shared64','L2_128']for write in [False,True]}
        area_pass=connector_footprint<=strip_capacity and all(c['fit']for c in controllers)and all(s['fit']for s in connector_slots)
        routes_pass=all(c['screen_pass']for row in controllers for c in row['cuts'])and m['global_service_cut_screens_pass']and m['corridor_screens_pass']
        models[name]=dict(source_SM_placement_adapter=slots,source_cut_owner_adapter=[dict(old_geometric_cut_SM=t['source_provider_identity']['geometric_slot'],source_provider_SM=t['SM'],source_bank=t['source_provider_identity']['producer_bank'],stack=t['source_provider_identity']['stack'])for t in slots],source_quad_clients=[[8*q+i for i in range(8)]+[32+q]for q in range(4)],
            storage=word_ports,SM_connector_slots=connector_slots,L2_controller_slots=controllers,
            area=dict(incremental_connector_cell_um2_per_SM=connector_logic,incremental_connector_footprint_um2_per_SM=connector_footprint,actual_reserved_strip_residual_um2_per_SM=strip_capacity,
                incremental_controller_footprint_um2_per_slice=slice_footprint,incremental_controller_footprint_mm2_per_die=4*slice_footprint/1e6,
                full_die_reserved_occupancy_mm2=m['area']['complete_reserved_occupancy_mm2'],existing_RF_shared_L2_SRAM_recharged=False,new_logic_fits_inside_existing_expanded_reservations=area_pass),
            routing=dict(local_L2_cuts=sum(len(c['cuts'])for c in controllers),existing_global_service_cuts=len(m['global_service_cuts']),existing_corridor_cuts=len(m['corridor_cuts']),
                additional_wide_data_trunk_bits=0,C0_transport_reuse='existing512data+512metadata pair, one arbiter credit; fetch/control and value transfer serialize, never free concurrent bandwidth',source_pending_route_bindings=m['blockers'],constructive_cut_screen_pass=routes_pass),
            latency=dict(provisional_profiles=profile,service_stall_bound_is_example_only=True,whole_token_ns=None,calendar_requires_actual_event_receipts=True,backend_wait_parameter='actual positive bounded backend/byte-arbitration delay required; exampleB1 is not a measured guarantee',queue_scope='up to511 older occupied shared-client seats; weight traffic byte arbitration remains a separate provider bound',clock_GHz=1.2,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25),
            atomic_connector_source_present=False,L2_generic_word_endpoint_source_present=False,
            admission='FAIL_PHYSICAL_SOURCE_BINDING'if area_pass and routes_pass else'FAIL_COMPOSED_AREA_OR_CUT_SCREEN',
            blockers=['actual mapped parent FF/cone placement and exhaustive routes remain unbound','new atomic connector/shared-L2 gateway has no connected source endpoint','all GU/KV cache writers must join the producer-range fence; generic L2 line read/write adapter absent; Qwen GU scalar producer is not generic L2 hardware coverage','new PG/via/crossing geometry and context SS/FF remain unqualified','Dewey actual event/provider interval reconciliation before total-token latency'],hardware_admitted=False)
    return dict(schema='opentallas.H4.HBM.complete-service-G0.v1',enabled_default=False,models=models,connector_field_bits=shared_L2_field_bits,connector_register_bits=connector_bits,connector_gate_equivalents_assumed=connector_gates,
        slice_state_bits=slice_bits,slice_lease_fields_bits=dict(ticket=128,lease=64,local_tag=10,bank=3,byte_offset=18,length=8,state=4,write=1),source_drain_probe=dict(RF='quiesce unaccepted host/SIMD requests; host_rd_ready&&host_wr_ready&&!host_rsp_valid&&!host_ack_valid with all requestvalids0 proves original idle; drain existing consumers first',shared='scratch_ready&&!scratch_done after existing consumer ACK',bulk='never mask an owned no-ready weight response; source staging ring remains independent'),source_pins=[dict(commit=c,path=p,sha256=hashlib.sha256(b).hexdigest())for(c,p),b in blobs.items()],
        tag_contract=dict(existing_clients=36,weight_clients=list(range(32)),shared_C0_clients=list(range(32,36)),global_tag_bits=16,client_bits=6,local_tag_bits=10,per_client_seats=512,C0_max_seats_per_slice=8,KV_seats_at_full_C0_occupancy=504,
            weight_seats_reduced=0,KV_outstanding_capacity_reduction_fraction=8/512,semantics='512 total shared seats, not512+8; all return/write visibility and reverse grants drain before reuse',bank_read_contract='explicit source producer_bank/stack from actual home; never infer producer from consumerSM; cross-slice producer route unsupported until bound',finite_credit_bound='one connector command per SM; all-or-none reserve, no RF lock held while waiting for a slice seat'),
        byte_arithmetic_contract='Opaque bytes only; NaN,Inf,signed zero and I64 word patterns unchanged. Numerical primitives not executed here.',hardware_opcode_coverage=[],actual_endpoint_inventory=dict(RF=dict(source='rtl/gpu/ot_gpu_rf_service.sv',read_vectors=2,write_vectors=1,tag_port=False,owner_metadata_required_outside=True),shared=dict(source='rtl/gpu/ot_gpu_scratch_service.sv',ports=['valid','ready','write','addr10','wdata512','done','done_ready','rdata512'],generation_port=False),L2=dict(GU_scalar_producer_source='rtl/gpu/ot_gpu_qwen_gu64_l2.sv',scalar_data_bits=32,epoch_bits=16,generic_word_read_write_endpoint_present=False),bulk_copy=dict(source='rtl/gpu/ot_gpu_bulk_copy.sv',MAX_OUT=512,DEPTH=1024,response_ready_port=False)),PVE2_or_PVE3_used=False,no_RTL_or_PnR=True,hardware_admitted=False)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--verify',action='store_true');a=ap.parse_args();p=Path(a.out)
    b=(json.dumps(build(),indent=2,sort_keys=True)+'\n').encode();pins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in ['tools/h4_hbm_service_context_g0.py','tests/test_h4_hbm_service_context_g0.py']}
    if a.verify:
        if (p/'model.json').read_bytes()!=b or json.loads((p/'source_pins.json').read_text())!=pins:raise ValueError('service context replay/source mismatch')
        print('PASS_EXACT_COMPLETE_SERVICE_CONTEXT_REPLAY');return
    p.mkdir(parents=True,exist_ok=False);(p/'model.json').write_bytes(b);(p/'source_pins.json').write_text(json.dumps(pins,sort_keys=True,indent=2)+'\n');print('COMPLETE_SERVICE_G0_RECORDED')
if __name__=='__main__':main()
