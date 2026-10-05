#!/usr/bin/env python3
"""Kind-specific home admission and finite two-seat throughput pipeline model.
The frozen predecessor is immutable. No endpoint RTL or hardware claim.
"""
import argparse,collections,hashlib,importlib.util,json,math
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'results/uarch/h4_hbm_baseline_bridge_20261003/pipeline_r2'
PIN='a7e1c222c182baa3d23449a83ca5f92764b575d80df50a5a33f7c790be5a16a5'
def require(x,msg):
    if not x:raise ValueError(msg)
def canonical(x):return (json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
def inputs():
    raw=(BASE/'input_manifest.json').read_bytes();require(hashlib.sha256(raw).hexdigest()==PIN,'manifest pin');out={}
    for row in json.loads(raw)['inputs']:
        p=(BASE/row['archive']).resolve();require(p.is_relative_to((BASE/'inputs').resolve()),'exact archive origin');v=p.read_bytes()
        require(len(v)==row['bytes'] and hashlib.sha256(v).hexdigest()==row['sha256'],'exact archive input');out[p.name]=v
    return out

def codec():
    inputs();p=BASE/'inputs/codec.py';spec=importlib.util.spec_from_file_location('frozen_bridge_codec',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def unpack(raw):
    c=codec();require(type(raw)is bytes and len(raw)==64 and raw[-1]==0,'protected descriptor64B');bits=0
    for i in range(7):
        code=int.from_bytes(raw[i*9:i*9+9],'little');syndrome=0
        for parity,mask in zip((1,2,4,8,16,32,64),c.PARITY_MASKS):
            if (code&mask).bit_count()&1:syndrome|=parity
        if syndrome:require(code.bit_count()&1 and syndrome<=71,'uncorrectable descriptor');code^=1<<(syndrome-1)
        elif code.bit_count()&1:code^=1<<71
        bits|=sum(((code>>(p-1))&1)<<j for j,p in enumerate(c.DATA_POSITIONS))<<(64*i)
    result={};shift=0
    for n,w in c.FIELDS:result[n]=(bits>>shift)&((1<<w)-1);shift+=w
    return result


def directory_admit(raw,requester,publication=None):
    """Home locality is distinct from the physically accepted requester.

    This is a proposed source-port adapter. Passed receipts are not promoted
    to installed endpoint traces. Current persistent publisher has rank/version
    and generation, but does not define a physical requesting SM.
    """
    row=unpack(raw);required={'SM','PC','rank','generation','lease','home_id','byte_offset','byte_count','source_port','source_sha256'}
    require(isinstance(requester,dict) and set(requester)==required,'actual requester source binding required, not home SM')
    for n,limit in [('SM',32),('PC',4095),('rank',96)]:require(type(requester[n])is int and 0<=requester[n]<limit,'requester '+n)
    require(type(requester['generation'])is int and 0<requester['generation']<2**64 and type(requester['lease'])is int and 0<requester['lease']<2**64,'live generation/lease')
    require(requester['home_id']==row['id'] and row['ranks']&(1<<requester['rank']),'source home/rank identity')
    require(requester['source_sha256']==hashlib.sha256(inputs()['wrapper.sv']).hexdigest(),'requester source wrapper pin')
    require(requester['source_port'] in {f'{prefix}_valid[{requester["SM"]}]&&{prefix}_ready[{requester["SM"]}]' for prefix in ('host_rd','host_wr','simd','scratch')},'actual port-index SM; no arbitrary home constant')
    require(type(requester['byte_offset'])is int and type(requester['byte_count'])is int and 0<=requester['byte_offset'] and requester['byte_count']>0 and requester['byte_offset']+requester['byte_count']<=row['span'],'exact requested home range')
    require(row['birth']==4095 or row['birth']<=requester['PC'],'source birth not yet live')
    if row['kind']==0:
        require(row['flags']&3==3,'RF requires source home SM/static retirement eligibility')
        require(row['SM']==requester['SM'] and (row['retire']==4095 or requester['PC']<=row['retire']),'RF directory consumer/lifetime mismatch')
        lifetime='RF static PC range is eligibility only; actual generation/consumer/reverse lease still prevents recycle'
    else:
        require(row['kind'] in (1,2),'documented offchip home')
        require(isinstance(publication,dict) and set(publication)=={'home_id','rank','generation','producer_PC','published_bytes','visibility_accepted','read_lease'},'persistent publication/read lease required')
        require((publication['home_id'],publication['rank'],publication['generation'])==(row['id'],requester['rank'],requester['generation']),'publication version/rank/generation mismatch')
        require(type(publication['producer_PC'])is int and (row['birth']==4095 or publication['producer_PC']==row['birth']),'source exact producer PC')
        require(type(publication['published_bytes'])is int and 0<publication['published_bytes']<=row['span'] and requester['byte_offset']+requester['byte_count']<=publication['published_bytes'] and publication['visibility_accepted']is True and publication['read_lease']==requester['lease'],'source publication and retained read lease')
        lifetime='persistent state retained by generation/publication and read lease, not an invented RF retire PC or home SM'
    return dict(home_id=row['id'],kind=row['kind'],requester_SM=requester['SM'],home_SM_required=row['kind']==0,lifetime=lifetime,
        static_home_valid=True,requester_origin='proposed source-port model; installed pairing still required',hardware_admitted=False)

class ElasticPipeline:
    """Registered two-seat FIFO at each hop; one beat/lane/edge.

    Transfers use OLD registered occupancy. No combinational ready ripple,
    no same-edge full-pop slot reuse. Payloads are exact bytes or opaque IDs.
    Egress acceptance frees only stage seats, never a parent owner lease.
    """
    def __init__(self,stages=38,lanes=4):
        require(type(stages)is int and stages>=1 and type(lanes)is int and lanes>=1,'finite stages/lanes')
        self.stages=stages;self.lanes=lanes;self.q=[[collections.deque() for s in range(stages)] for l in range(lanes)];self.edge=0
    def step(self,incoming,ready):
        require(len(incoming)==self.lanes and len(ready)==self.lanes and all(type(v)is bool for v in ready),'actual lane valid/ready')
        accepted=[];delivered=[]
        for lane in range(self.lanes):
            q=self.q[lane];moves=[bool(q[s]) and len(q[s+1])<2 for s in range(self.stages-1)]
            output=q[-1][0] if q[-1] and ready[lane] else None
            take=incoming[lane]is not None and len(q[0])<2
            if output is not None:q[-1].popleft()
            for s in range(self.stages-2,-1,-1):
                if moves[s]:q[s+1].append(q[s].popleft())
            if take:q[0].append(incoming[lane])
            require(all(len(x)<=2 for x in q),'two-seat ownership invariant');accepted.append(take);delivered.append(output)
        result=dict(edge=self.edge,accepted=accepted,delivered=delivered);self.edge+=1;return result
    def occupancy(self):return sum(len(q) for lane in self.q for q in lane)

class ParentLeases:
    """Bounded source ring parent held beyond output through matching reverse.

    Root delivery, common ACK, consumption and reverse are distinct. Stage
    drain does not authorize tag reuse. No timeouts or generation defaults.
    """
    def __init__(self,capacity=512):
        require(type(capacity)is int and 0<capacity<=512,'source finite ring capacity')
        self.capacity=capacity;self.live={};self.slots={};self.generations={}
    def reserve(self,tag,nbeats):
        require(type(tag)is int and 0<=tag<2**16 and type(nbeats)is int and 1<=nbeats<=32,'source tag/beat bounds')
        slot=tag>>4;generation=tag&15
        require(generation>self.generations.get(slot,0),'matching fresh generation; no wrap without source quiescence')
        require(slot not in self.slots and len(self.live)<self.capacity,'finite parent slot held through reverse')
        self.slots[slot]=tag;self.generations[slot]=generation
        self.live[tag]=dict(n=nbeats,delivered=set(),consumed=set(),reversed=set(),common_ACK=False)
    def deliver(self,tag,beat):
        p=self.live.get(tag);require(p is not None and type(beat)is int and 0<=beat<p['n'] and beat not in p['delivered'],'matching delivered beat once');p['delivered'].add(beat)
    def ACK(self,tag):
        p=self.live.get(tag);require(p is not None and len(p['delivered'])==p['n'] and not p['common_ACK'],'complete source common ACK');p['common_ACK']=True
    def consume(self,tag,beat):
        p=self.live.get(tag);require(p is not None and p['common_ACK'] and beat in p['delivered'] and beat not in p['consumed'],'matching consumer after common ACK');p['consumed'].add(beat)
    def reverse(self,tag,beat):
        p=self.live.get(tag);require(p is not None and beat in p['consumed'] and beat not in p['reversed'],'matching child reverse only');p['reversed'].add(beat)
        if len(p['reversed'])==p['n']:del self.live[tag];del self.slots[tag>>4]


class OwnedRFACK:
    """Model of the necessary source write_go tag echo + held common ACK.

    Source RF has one combined ack_valid/ready but no tag today. This shim
    model prices its necessary register/matcher; it is not installed source.
    """
    def __init__(self,SM):require(type(SM)is int and 0<=SM<32,'physicalSM');self.SM=SM;self.owner=None
    def write_go(self,tag,dst,lease,*,copy0_edge,copy1_edge):
        require(self.owner is None and type(tag)is int and 0<=tag<2**16 and type(dst)is int and 0<=dst<512 and type(lease)is int and lease>0,'ownedRF finite write request')
        require(type(copy0_edge)is int and copy0_edge>=0 and copy0_edge==copy1_edge,'actual common same-edge copy acceptance')
        self.owner=dict(tag=tag,dst=dst,lease=lease,phase='ACK',write_edge=copy0_edge)
    def ACK(self,tag,dst,lease,*,valid,ready,edge):
        o=self.owner;require(o is not None and (tag,dst,lease)==(o['tag'],o['dst'],o['lease']),'matching source captured tag/generation/destination/lease')
        require(o['phase']=='ACK' and type(edge)is int and edge>=o['write_edge']+1 and type(valid)is bool and type(ready)is bool,'source registered common ACK')
        if not(valid and ready):return False
        o['phase']='VISIBLE';return True
    def advance(self,tag,lease,event):
        o=self.owner;require(o is not None and (tag,lease)==(o['tag'],o['lease']),'same owner retained through reverse')
        phases={'visibility':('VISIBLE','CONSUMER'),'consumer':('CONSUMER','REVERSE'),'reverse':('REVERSE',None)}
        require(event in phases and o['phase']==phases[event][0],'visibility/consumer/reverse order')
        if phases[event][1]is None:self.owner=None
        else:o['phase']=phases[event][1]

COSTS=('owner_grant','RF_both_copy_accept','RF_common_ACK','ACK_identity_match','CDC_forward','CDC_return','visibility','consumer','reverse_match','reverse_grant')
def source_bindings():
    """Actual leaf attachment points; missing controller bodies stay missing.

    Source hashes bind the attachment, not a claimed installed successor.
    CDC synchronization counts remain receiver-clock counts until a real
    domain pair and acceptance/return intervals are supplied.
    """
    src=inputs()
    specs={
        'owner_grant':('wrapper.sv','rf_owner_grant[sm] && !collision',False,1),
        'RF_both_copy_accept':('rf.sv','write_go && wr_addr[8:7]==p; both u_operand_a/u_operand_b',True,1),
        'RF_common_ACK':('rf.sv','if(write_go) ack_valid<=1; ack_valid && ack_ready',True,1),
        'ACK_identity_match':('rf.sv','write_go capture; current ack_valid has no tag/destination echo',False,1),
        'CDC_forward':('bridge.sv','first(src_clk->fast_clk), route(EDGES=38), second(fast_clk->dst_clk)',True,38),
        'CDC_return':('bridge.sv','reverse instance of same first/route/second chain; actual domain pairing absent',False,38),
        'visibility':('fence.sv','pending && host_ack_valid; vector_ACK_visible',True,1),
        'consumer':('wrapper.sv','host_rsp_valid[sm] && host_rsp_ready[sm]; scratch_done && scratch_done_ready',True,1),
        'reverse_match':('wrapper.sv','no source reverse identity port; add owner retained matcher',False,1),
        'reverse_grant':('wrapper.sv','rf_owner_grant/shared_owner_grant release after matched child reverse',False,1),
    }
    return {k:dict(archive=name,source_sha256=hashlib.sha256(src[name]).hexdigest(),attachment=port,
        leaf_exists=exists,connected_owner_installed=False,minimum_provisional_FAST_edges=minimum,
        CDC_receiver_sync_edges_each=2 if k.startswith('CDC_') else None,
        actual_clock_pair=None if k.startswith('CDC_') else 'leaf clk; composed clock authority required',
        minimum_is_not_finite_contender_upper=True) for k,(name,port,exists,minimum) in specs.items()}

def compose(rows):
    """Selected connected owner service; every duration positive and keyed.

    Costs already paid elsewhere may be referenced by SAME occurrence ID.
    Cost proposals remain provisional, even when source hashes match.
    This cannot manufacture finite contender/hold bounds from cost durations.
    """
    bindings=source_bindings();seen={};owners={}
    for row in rows:
        require(set(row)=={'id','kind','owner','duration_edges','source_sha256','origin'},'source cost ABI')
        require(isinstance(row['id'],str) and row['id'] and row['kind'] in COSTS,'concrete event ID')
        require(type(row['duration_edges'])is int and row['duration_edges']>0,'no hidden zero/unknown mandatory cost')
        binding=bindings[row['kind']]
        require(row['source_sha256']==binding['source_sha256'] and row['origin']=='provisional_source_model','exact kind-specific source attachment; no hardware timing promotion')
        require(row['duration_edges']>=binding['minimum_provisional_FAST_edges'],'source route/registered stage lower bound cannot become 1/1/1')
        owner=row['owner'];require(isinstance(owner,str) and owner,'actual emitted lease owner')
        require(row['id'] not in seen or seen[row['id']]==row,'same charged occurrence cannot mutate')
        seen[row['id']]=row;owners.setdefault(owner,set()).add(row['kind'])
    require(owners and all(kinds==set(COSTS) for kinds in owners.values()),'all connected service terms required')
    return dict(unique_occurrences=len(seen),provisional_edge_sum=sum(r['duration_edges'] for r in seen.values()),
        cost_clock='provisional FAST-equivalent edges; receiver synchronizer edges not converted without actual clock pair',
        CDC_receiver_sync_edges_not_credited=True,source_bindings=bindings,
        actual_hold_contender_intervals=None,operator_critical_path_ns=None,hardware_admitted=False)

def cadence(stages=38,lanes=4,edges=640,ratio=False):
    p=ElasticPipeline(stages,lanes);next_id=[0]*lanes;outputs=[[] for l in range(lanes)]
    for e in range(edges):
        ready=not ratio or e%4!=3;r=p.step([(l,next_id[l]) for l in range(lanes)],[ready]*lanes)
        for l in range(lanes):
            if r['accepted'][l]:next_id[l]+=1
            if r['delivered'][l]is not None:outputs[l].append((e,r['delivered'][l][1]))
    for l in range(lanes):require([i for e,i in outputs[l]]==list(range(len(outputs[l]))),'exact ordered no-loss delivery')
    first=outputs[0][0][0];steady=sum(e>=128 for e,i in outputs[0]);return dict(stages=stages,lanes=lanes,edges=edges,
        first_delivery_edge=first,steady_window_edges=edges-128,steady_deliveries_per_lane=steady,
        observed_payload_Bpc_die=steady/(edges-128)*lanes*32*32,origin='cycle model only; actual target timing unqualified')

def outputs():
    src=inputs();old=json.loads(src['model.json']);c=codec();directions={};pipe_bits=0
    for n,raw in [('request',313),('return',277)]:
        coded=c.protected(raw);bits=32*38*(4*2*coded+c.protected(4*7));pipe_bits+=bits
        directions[n]=dict(raw_bits_per_lane=raw,coded_bits_per_lane=coded,lanes_per_SM=4,stages=38,seats_per_stage=2,control_bits_per_lane=7,
            data_control_protected_bits=bits,bit_boundary_per_SM=4*coded+4*2,
            handshake='per-hop registered occupancy; onehop credit dependency, no38hop combinational ready chain',
            payload_ECC='code at ingress, carry protected words through registers, decode at egress; no repeated fullword codec perstage')
    ctrl_ECC=32*38*2*768;end_ECC=32*4*5*4*768;gates=2*pipe_bits+ctrl_ECC+end_ECC
    oldpipe=old['actual_consumer_delta']['pipelined_route_candidate_bits'];delta=pipe_bits-oldpipe
    area=(pipe_bits*.2916+gates*.3)/.5/1e6
    root_fields=dict(tag=16,length=6,delivered_mask=32,consumer_mask=32,reverse_mask=32,common_ACK=1,phase=3,valid=1,home_id=32)
    root_bits=32*(512*c.protected(sum(root_fields.values()))+c.protected(4096*4))
    root_gates=32*(512*16*2+3*511*c.protected(sum(root_fields.values()))+4*3*768)
    root_area=(root_bits*.2916+root_gates*.3)/.5/1e6
    ack_cdc_bits=32*(16*c.protected(26)+c.protected(50))
    model=dict(schema='HBM_KIND_DIRECTORY_ELASTIC_PIPELINE_R2',source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in src.items()},
        predecessor='501a3babc57fd7bc7b7ddb117f31b370b6cc8aba',status='FINITE_CADENCE_DESIGN_READY_FAIL_SOURCE_RECEIPTS_PHYSICAL_CUTS',
        mandatory_baseline=True,performance_opt_in=False,directions=directions,total_pipeline_protected_bits=pipe_bits,
        connected_cost_source_bindings=source_bindings(),
        predecessor_single_seat_pipeline_bits=oldpipe,replacement_incremental_bits=delta,
        codec_mux_control_gate_equivalents_ASSUMED=gates,pipeline_FF_control_footprint_mm2_ASSUMED=area,
        owned_RF_ACK=dict(source_common_ACK_is_one=True,source_identity_missing=True,required_shadow_bits=32*c.protected(26),
            accepted_echo='tag16+RFdestination9+commonACK1 captured at actual common write_go',
            phase='write_go->commonACKheld->identitymatch->visibility->consumer->reverse',
            source_write_to_ACK_min_edges=1,proposed_identity_match_edges=1,existing_shadow_not_double_charged=True),
        ACK_CDC=dict(raw_bits=26,coded_bits=72,depth=16,SMs=32,protected_state_bits=ack_cdc_bits,actual_clock_domain_pair=None,
            installed=False,finite_wait_upper=None,required_positive_occurrence_ids=list(COSTS)),
        parent_guard_fields=root_fields,parent_guard_bits_upper=root_bits,parent_guard_reuse_not_credited_without_source_inventory=True,parent_guard_gate_equivalents_ASSUMED=root_gates,
        parent_guard_FF_mux_footprint_mm2_ASSUMED=root_area,complete_unallocated_screen_upper_mm2_ASSUMED=old['resource_ledger']['candidate_FF_mux_ECC_area_mm2_ASSUMED']+area+root_area+ack_cdc_bits*.2916/.5/1e6,
        conservative_replacement_logic_overlap_not_deducted=True,
        complete_controller_bits_after_replacement=old['resource_ledger']['candidate_control_bits']+delta+root_bits+ack_cdc_bits,
        replacement_not_added_twice=True,area_is_screen_only=True,
        throughput=dict(steady_beats_per_lane_per_FASTedge=1,with3to4_sink=0.75,sector_payload_bytes=32,SMs=32,lanes_per_SM=4,
            ceiling_equalclock_Bpc=4096,ceiling3to4_Bpc=3072,not_installed_or_measured=True),
        latency=dict(no_stall_route_edges=38,forward_reverse_pipeline_edges=76,target1p2GHz_component_ns=76/1.2,
            allocation_ACK_CDC_consumer_reverse_wait_upper=None,whole_operator_ns=None,
            positive_control_costs_required=True,existing72wire_edges_not_recharged_without_interval_receipt=True),
        directory_policy=dict(RF='source home SM and static birth/retire eligibility; generation/consumer/reverse lease prevents premature recycle',
            spill='offchip home locality independent of requester; source publication/read lease required',
            HBM_NATIVE_STATE='no required fixed home SM or RF-style retire PC; actual requester port and producer publication/generation lease',
            requester='actual accepted SM endpoint port index; Peirce/Sagan actual consumer binding and physical rank mapping must pair it',
            actual_appended4616_missing_SM_or_retire_is_not_itself_invalid=True,
            existing_provider='publish_state validates binding.PC/version/rank/source_result, shape/type, aperture and _leased(version)',
            arbitrary_home_SM_constant_refused=True,original501strict_allkind_refusal_superseded=True,installed_requester_receipts=None),
        owner_retention=dict(stage_pop_not_parent_release=True,source_common_ACK_once_for_all_copies=True,no_generation_wrap_without_quiescence=True,
            tag_held_until_all_consumer_and_reverse_acceptances=True,root_metadata_reuse_needs_actual_source_connection=True),
        physical=dict(actual38hop_routes_for_selected32SMs=None,coded_request_return_cuts_capacity=None,
            additional_clock_PG_OBS_via_allocation=None,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
            fixed1p2GHz_target_no_timing_relaxation=True),
        next_gates=['Peirce/Sagan actual requester/version/publication/generation lease paired with Dewey intervals',
            'actual producer acceptance and backend/CDC/commonACK/consumer/reverse finite waits',
            'coded4lane two-seat throughput pipeline complete32SM slot/clock/PG/cuts'],
        hardware_admitted=False,engine_build_ready=False)
    replay=dict(equalclock=cadence(),ratio3to4=cadence(ratio=True))
    return {'model.json':canonical(model),'cadence_replay.json':canonical(replay)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args();data=outputs()
    if a.verify:
        for n,v in data.items():require((BASE/n).read_bytes()==v,'exactr2replay '+n)
        print('PASS kind-directory policy and finite elastic pipeline replay')
    else:
        require(a.output is not None,'explicit output');a.output.mkdir(parents=True,exist_ok=True)
        for n,v in data.items():(a.output/n).write_bytes(v)
if __name__=='__main__':main()
