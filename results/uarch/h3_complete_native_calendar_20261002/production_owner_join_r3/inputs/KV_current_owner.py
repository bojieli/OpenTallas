#!/usr/bin/env python3
"""Source-bound KV validity, metadata fence and finite service design model.

This successor preserves source call order and refuses absent physical bounds.
It is an executable prebuild contract, not installed RTL or a DRAM scheduler.
"""
import argparse
import ast
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]/'results/uarch/h4_hbm_kv_validity_fence_20261003'
PIN = 'efeaba387fb6efe85953a23eec59143e8cc250f86255c56d018dd0e98c485e34'
COST_KEYS = ('grant', 'SRAM_read', 'SRAM_write', 'refill', 'backend_visible', 'merge',
             'child_consumer', 'child_reverse', 'metadata_fence', 'RF_pair_read',
             'RF_both_copy_write', 'RF_mirror_ACK', 'SCORES_consumer', 'PV_consumer', 'parent_reverse',
             'directory_lookup', 'tag_allocate', 'ACK_route', 'CDC_request', 'CDC_return')


def require(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def inputs():
    raw=(BASE/'input_manifest.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==PIN, 'hard manifest pin')
    out={}
    for r in json.loads(raw)['inputs']:
        p=(BASE/r['archive']).resolve()
        require(p.is_relative_to((BASE/'inputs').resolve()), 'exact archive origin')
        raw=p.read_bytes()
        require(len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'], 'exact source bytes')
        out[p.name]=raw
    return out


def compile_plan():
    source=inputs();directory=json.loads(gzip.decompress(source['directory.json.gz']))
    tree=ast.parse(source['bounded.py'])
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BoundKVStorage')
    methods={n.name:ast.get_source_segment(source['bounded.py'].decode(),n) for n in cls.body if isinstance(n,ast.FunctionDef)}
    commit=methods['commit']
    require(commit.index('self.state_write(rank,index//8') < commit.index('self.put_record'), 'retained bitmap-before-record source order')
    require('self.bytes.get((rank,e[\'base\']+offset+i),0)' in methods['state_read'], 'source missing byte is logical zero, not physical validity')
    require('read_pending<=read_go' in source['rf.sv'].decode() and 'if(write_go) begin ack_valid<=1' in source['rf.sv'].decode(), 'actual RF registered read and two-copy write ACK source')
    leaf=json.loads(source['H1_edges.json'])
    for name,archive in [('rtl/gpu/ot_gpu_rf_service.sv','rf.sv'),('rtl/gpu/ot_gpu_scratch_service.sv','scratch.sv'),('rtl/gpu/ot_gpu_full_sm_service.sv','service.sv')]:
        require(hashlib.sha256(source[archive]).hexdigest()==leaf['source_pins'][name], 'matched leaf edge contract source')
    rows=[]
    for g in directory['groups']:
        events=g['source_events'];base=g['state_home_range'][0];layer,rank,_=g['key']
        writes=[('begin_header',base+37440,(g['writer_tag']+1).to_bytes(8,'little')),
                ('commit_bitmap',events[1]['state']['bitmap_address'],bytes([events[1]['state']['bitmap_byte']]))]
        for name,event in zip(('commit_record','acquire_record','SCORES_record','PV_record'),events[1:5]):
            writes.append((name,event['state']['record_address'],bytes.fromhex(event['state']['record_hex'])))
        metadata=[]
        for ordinal,(name,address,data) in enumerate(writes):
            offset=address%32
            require(offset+len(data)<=32, 'source metadata fits one32B sector')
            patch=bytearray(32);patch[offset:offset+len(data)]=data
            metadata.append(dict(ordinal=ordinal,operation=name,address=address&~31,source_byte_address=address,
                mask=((1<<len(data))-1)<<offset,patch_hex=patch.hex(),bytes=len(data),
                provider_ref=g['state_provider_ref'],old_valid_capture_required=True,
                visibility='whole-sector write visible; preserve neighboring record/header bytes',
                reader_eligibility='writer outer lock held through bitmap AND producer record visibility'))
        producers={s['producer_version'] for s in g['sectors']};outputs={s['decoded_read_version'] for s in g['sectors']}
        hs=g['source_RF_control_version_homes']
        producer_homes=[h for h in hs if h['version'] in producers]
        output_homes=[h for h in hs if h['version'] in outputs]
        require(sum(h['word_count'] for h in producer_homes)==1024, 'actual source KV producer word count')
        producer_vectors=[]
        for h in producer_homes:
            require(h['home']['class']=='RF' and h['word_count']==256, 'actual producer RF2 vectors/home')
            for local in (0,128):
                producer_vectors.append(dict(version=h['version'],provider_ref=h['provider_ref'],SM=h['SM'],
                    RF_slot=h['home']['slot_first']+local//128,source_birth_PC=h['birth_pc'],physical_mirrors=2))
        # Runtime position0 output is512 contiguous FP32 words/version. Static
        # homes reserve full-context capacity; NEVER materialize/charge it as
        # this token's output, nor relabel spilled output as RF storage.
        output_homes=[h for h in output_homes if h['SM'] in (0,1)]
        decoded_sectors=[]
        for h in output_homes:
            require(h['home']['class']=='spill' and h['word_count']>=256, 'exact decoded persistent spill home')
            for ordinal in range(32):
                decoded_sectors.append(dict(version=h['version'],provider_ref=h['provider_ref'],SM=h['SM'],
                    address=h['home']['global_byte_base']+32*ordinal,bytes=32))
        require(len(decoded_sectors)==128 and len(producer_vectors)==8, 'actual bounded position0 page counts')
        rows.append(dict(key=g['key'],die=rank,writer_tag=g['writer_tag'],reader_lease=g['reader_lease'],metadata_writes=metadata,
            source_metadata_read_calls=dict(bitmap_byte=1027,record16=5),
            metadata_init_sector_range=[base//32,(g['state_home_range'][1]+31)//32],
            source_producer_homes=producer_homes,decoded_result_homes=output_homes,
            source_RF_unique_vectors=8,producer_vectors=producer_vectors,decoded_sectors=decoded_sectors,
            selected_provider_RF_pair_reads=8,producer_RF_write_cost_already_owned_by_PC5_PC9=True,
            source_RF_bus_receipts=None,payload=g['sectors']))
    return dict(schema='HBM_KV_VALIDITY_FENCE_PLAN_R1',groups=rows,
        actual_KV_source_archive=directory['observed_archive_commit'],actual_source_events=432,
        source_leaf_edges=leaf['service_edges'],leaf_SS_FF_verified=False,
        source_leaf_sink_policy=leaf['sink_policy_required'],
        metadata_bus_observed=False,source_order='bitmap write precedes producer record; serialize writer and fence both before reader eligibility',
        initial_zero_policy='source logical zeros require explicit full-sector initialization/visibility on fresh allocation, or actual valid old-sector capture; absent receipt refuses',
        hardware_admitted=False,production_consumer_receipts=False)


class SectorTransaction:
    """One opaque32B RMW buffer; never default an unknown old byte to zero."""
    def __init__(self):
        self.active=None;self.watermarks={}

    def reserve(self,identity,*,address,mask):
        require(type(identity) is tuple and len(identity)==3 and all(type(x) is int for x in identity), 'epoch/rank/sequence identity')
        epoch,rank,sequence=identity
        require(0<epoch<2**64 and rank in (0,1) and 0<sequence<2**40, 'source finite identity bounds')
        require(self.active is None and (epoch,sequence)>self.watermarks.get(rank,(0,0)), 'single child credit; stale identity refused')
        require(type(address) is int and 0<=address<2**34 and address%32==0 and type(mask) is int and 0<mask<2**32, 'finite address and byte mask')
        self.active=dict(identity=identity,address=address,mask=mask,phase='OLD',data=None)
        self.watermarks[rank]=(epoch,sequence)

    def event(self,identity,event,*,payload=None,receipt=None):
        x=self.active
        require(x is not None and identity==x['identity'], 'exact granted child identity')
        if event=='old_capture' and x['phase']=='OLD':
            require(type(payload) is bytes and len(payload)==32, 'actual complete old-sector bytes')
            require(receipt==dict(identity=identity,address=x['address'],full_sector_valid=True), 'same full-address validity/capture receipt')
            x['data']=payload;x['phase']='MERGE'
        elif event=='merge' and x['phase']=='MERGE':
            require(type(payload) is bytes and len(payload)==32, 'opaque32B patch')
            x['data']=bytes(payload[i] if x['mask']>>i&1 else x['data'][i] for i in range(32));x['phase']='WRITE'
            return x['data']
        elif event=='write_visible' and x['phase']=='WRITE':
            require(receipt==dict(identity=identity,address=x['address'],data=x['data']), 'actual preserved full-sector backend visibility')
            x['phase']='CONSUMER'
        elif event=='consumer' and x['phase']=='CONSUMER':x['phase']='REVERSE'
        elif event=='reverse' and x['phase']=='REVERSE':self.active=None
        else:raise ValueError('old-valid/merge/write-visible/consumer/reverse causal order')


class MetadataFence:
    """Keep actual source bitmap-before-record writes inaccessible until fenced."""
    def __init__(self,group):
        self.group=group;self.ordinal=0;self.writer_held=True;self.reader_lease=None;self.mirrors=set();self.decoded=set();self.done=set();self.reversed=False
    def visible(self,ordinal,*,address,data):
        require(ordinal==self.ordinal and self.ordinal<len(self.group['metadata_writes']), 'source ordered metadata completion')
        require(len(self.mirrors)==16, 'actual source producer pages two-copy publication ACK prerequisite')
        op=self.group['metadata_writes'][ordinal]
        require(address==op['address'] and type(data) is bytes and len(data)==32, 'actual metadata sector visibility')
        patch=bytes.fromhex(op['patch_hex'])
        require(all(data[i]==patch[i] for i in range(32) if op['mask']>>i&1), 'source exact metadata bits')
        if ordinal==3:require(self.reader_lease is not None, 'acquired reader identity before record write')
        if ordinal==4:require('SCORES' in self.done, 'SCORES completion before done-bit write')
        if ordinal==5:require('PV' in self.done, 'PV completion before final record write')
        self.ordinal+=1
    def publish_fence(self):
        require(self.writer_held and self.ordinal==3, 'header/bitmap/producer record all visible')
        self.writer_held=False
    def acquire(self,lease):
        require(not self.writer_held and self.ordinal==3 and self.reader_lease is None and type(lease)is int and 0<lease<2**64 and lease==self.group['reader_lease'], 'reader blocked through producer visibility fence')
        self.reader_lease=lease
    def mirror_ACK(self,*,vector,copy,provider_ref,RF_slot):
        require(type(vector)is int and 0<=vector<8 and type(copy)is int and copy in (0,1) and not self.reversed, 'exact source8 producer vector mirror ACK')
        require(provider_ref==self.group['producer_vectors'][vector]['provider_ref'] and RF_slot==self.group['producer_vectors'][vector]['RF_slot'], 'actual producer RF home reference and row')
        require((vector,copy) not in self.mirrors, 'duplicate mirror ACK')
        self.mirrors.add((vector,copy))
    def combined_ACK(self,*,vector,provider_ref,RF_slot,copy0_write_edge,copy1_write_edge,host_ACK_edge,valid,ready):
        require(all(type(e)is int and e>=0 for e in (copy0_write_edge,copy1_write_edge,host_ACK_edge)), 'actual nonnegative write and accepted ACK edges')
        require(copy0_write_edge==copy1_write_edge and host_ACK_edge>=copy0_write_edge and valid is True and ready is True, 'source common write_go and accepted registered host ACK')
        require((vector,0) not in self.mirrors and (vector,1) not in self.mirrors, 'combined ACK not partially consumed or duplicated')
        self.mirror_ACK(vector=vector,copy=0,provider_ref=provider_ref,RF_slot=RF_slot)
        self.mirror_ACK(vector=vector,copy=1,provider_ref=provider_ref,RF_slot=RF_slot)
    def decoded_visible(self,*,lease,version,address):
        require(lease==self.reader_lease and self.reader_lease is not None and not self.reversed, 'decoded result bound to actual reader lease')
        wanted={(s['version'],s['address']) for s in self.group['decoded_sectors']}
        require((version,address) in wanted and (version,address) not in self.decoded, 'actual decoded persistent spill sector visibility')
        self.decoded.add((version,address))
    def consumer(self,stage,*,lease):
        require(lease==self.reader_lease and len(self.decoded)==128 and self.ordinal>=4, 'all decoded spill sectors and acquired state visible')
        require(stage in ('SCORES','PV') and stage not in self.done and (stage!='PV' or 'SCORES' in self.done), 'source consumer order/identity')
        require(self.ordinal==(4 if stage=='SCORES' else 5), 'prior consumer record write order')
        self.done.add(stage)
    def retire(self,*,lease,reverse_accepted):
        require(lease==self.reader_lease and self.done=={'SCORES','PV'} and self.ordinal==6 and reverse_accepted is True and not self.reversed, 'consumer records visible plus distinct parent reverse')
        self.reversed=True


class BankArbiter:
    """Constructive selected policy, no installed fairness claim.

    One descriptor/client and one bank owner. Cursor advances ONLY on owner
    reverse. A numeric bound exists only if every client's full hold is priced.
    """
    def __init__(self,clients,hold_bounds):
        require(type(clients) is tuple and len(clients)>0 and len(set(clients))==len(clients), 'finite exact client inventory')
        require(set(hold_bounds)==set(clients), 'all contenders need complete ACK/consumer/reverse hold cost')
        self.holds={k:Fraction(v) for k,v in hold_bounds.items()}
        require(all(v>0 for v in self.holds.values()), 'positive finite service holds')
        self.clients=clients;self.pending={};self.active=None;self.cursor=0;self.selected=None
    def enqueue(self,client,identity):
        require(client in self.clients and client not in self.pending and (self.active is None or self.active[0]!=client), 'one actual client credit')
        require(type(identity) is int and 0<=identity<2**145, 'finite source-width request identity')
        self.pending[client]=identity
    def grant(self):
        if self.active is not None:return None
        for offset in range(len(self.clients)):
            i=(self.cursor+offset)%len(self.clients);client=self.clients[i]
            if client in self.pending:
                self.active=(client,self.pending.pop(client));self.selected=i;return self.active
        return None
    def reverse(self,client,identity):
        require(self.active==(client,identity), 'exact granted reverse')
        self.cursor=(self.selected+1)%len(self.clients);self.selected=None;self.active=None
    def wait_bound(self,client):
        require(client in self.holds, 'bound only actual enrolled client')
        # Residual active hold plus at most one competing quantum/client.
        return sum(self.holds[k] for k in self.clients if k!=client)


class ConnectedPayloadService:
    """Join validity/RMW to the admitted observed endpoint's SAME bank ledger.

    Complete positive costs required before opt-in execution. MetadataFence
    remains the explicit publication prerequisite; no backend ACK fabricated.
    """
    def __init__(self,*,banks,profile,epoch):
        import h4_hbm_qwen_observed_kv_cache as q
        require(hashlib.sha256(Path(q.__file__).read_bytes()).digest()==hashlib.sha256(inputs()['observed_endpoint.py']).digest(), 'exact admitted endpoint source')
        require(type(epoch)is int and 0<epoch<2**64, 'explicit external source/backend session epoch')
        self.epoch=epoch
        self.priced=price(compile_plan(),profile)
        self.endpoint=q.KVEndpoint(q.compile_directory(),banks=banks)
        self.transactions={rank:SectorTransaction() for rank in (0,1)}
        self.sequences={0:0,1:0};self.identities={}
    def begin(self,key):self.endpoint.begin(key)
    def grant(self,key,*,address):
        key=tuple(key);x,g=self.endpoint._state(key)
        require(x['phase']=='WRITE', 'selected validity connection covers source write children')
        require(self.transactions[key[1]].active is None and self.sequences[key[1]]+1<2**40, 'finite reuse of validity buffer')
        s=g['sectors'][x['cursor']]
        require(s['old_bytes_required'], 'partial-only adapter; full writes use admitted endpoint full-sector path')
        self.endpoint.grant(key,address=address)
        self.sequences[key[1]]+=1;identity=(self.epoch,key[1],self.sequences[key[1]])
        self.transactions[key[1]].reserve(identity,address=address,mask=s['mask']);self.identities[key]=identity
        return identity
    def merge(self,key,*,old,validity_receipt):
        key=tuple(key);x,g=self.endpoint._state(key);s=x['child']['sector'];i=self.identities[key];t=self.transactions[key[1]]
        t.event(i,'old_capture',payload=old,receipt=validity_receipt)
        merged=t.event(i,'merge',payload=bytes.fromhex(s['patch_hex']))
        require(self.endpoint.child(key,event='old_sector_capture',payload=old)==merged, 'same source preserved sector through admitted endpoint')
        return merged
    def visible(self,key,*,receipt):
        key=tuple(key);t=self.transactions[key[1]];i=self.identities[key]
        t.event(i,'write_visible',receipt=receipt)
        self.endpoint.child(key,event='backend_write_visible',payload=receipt['data'])
    def consumer(self,key):
        key=tuple(key);self.transactions[key[1]].event(self.identities[key],'consumer')
        self.endpoint.child(key,event='consumer_accept')
    def reverse(self,key):
        key=tuple(key);self.transactions[key[1]].event(self.identities[key],'reverse')
        self.endpoint.child(key,event='validated_reverse_grant');del self.identities[key]


def price(plan,profile):
    require(set(profile)=={'costs_ps','contender_hold_ps','qualification','origin'}, 'complete explicit service-cost profile')
    require(set(profile['costs_ps'])==set(COST_KEYS), 'all mandatory costs priced exactly once')
    costs={k:Fraction(v) for k,v in profile['costs_ps'].items()}
    require(all(v>0 for v in costs.values()) and profile['qualification']=='provisional', 'only explicit provisional pricing accepted until installed event and timing receipts are joined')
    require(costs['RF_pair_read']>=Fraction(2500,3)*plan['source_leaf_edges']['host_read'] and
        costs['RF_mirror_ACK']>=Fraction(2500,3)*plan['source_leaf_edges']['host_write'], 'priced RF service below retained source edge count at target clock')
    holds=profile['contender_hold_ps']
    require(len(holds)==64 and all(len(v)>0 and all(Fraction(x)>0 for x in v.values()) for v in holds.values()), 'all2die32banks finite actual contender bounds')
    counts=Counter(grant=0,SRAM_read=0,SRAM_write=0,refill=0,backend_visible=0,merge=0,
                   child_consumer=0,child_reverse=0,metadata_fence=72,RF_pair_read=576,
                   RF_both_copy_write=0,RF_mirror_ACK=576,SCORES_consumer=72,PV_consumer=72,parent_reverse=72)
    # Conservative design: no cache-hit credit. Each partial RMW and metadata
    # source read captures full32B through explicit backend-validity protocol.
    for g in plan['groups']:
        partial=sum(s['old_bytes_required'] for s in g['payload']);writes=len(g['payload'])+6
        reads=len(g['payload'])+1032;rmw=partial+6
        counts.update(grant=writes+reads,SRAM_read=reads+rmw,SRAM_write=writes,
                      refill=reads+rmw,backend_visible=writes,merge=rmw,
                      child_consumer=writes+reads,child_reverse=writes+reads)
    # Decoded position0 persistent output is spill, not mirrored RF.
    counts.update(grant=9216,SRAM_write=9216,backend_visible=9216,child_consumer=9216,child_reverse=9216)
    counts.update(directory_lookup=counts['grant'],tag_allocate=counts['grant'],
        ACK_route=counts['child_consumer']+counts['RF_mirror_ACK'],CDC_request=counts['grant'],CDC_return=counts['child_reverse'])
    # Cold-start full metadata extent initialization costs retained separately.
    ranges={(g['die'],*g['metadata_init_sector_range']) for g in plan['groups']}
    init=sum(stop-start for die,start,stop in ranges)
    cold=init*(costs['grant']+costs['SRAM_write']+costs['backend_visible']+costs['child_consumer']+costs['child_reverse']+costs['directory_lookup']+costs['tag_allocate']+costs['ACK_route']+costs['CDC_request']+costs['CDC_return'])
    subtotal=sum(counts[k]*costs[k] for k in COST_KEYS)
    worst_wait=max(sum(Fraction(v) for v in bank.values()) for bank in holds.values())
    # Conservative full serialization across both ranks. No speculative overlap.
    wait=counts['grant']*worst_wait
    return dict(schema='KV_COMPLETE_CONDITIONAL_SERVICE_PRICE_R1',qualification=profile['qualification'],origin=profile['origin'],
        counts=dict(counts),mandatory_service_ps=str(subtotal),metadata_cold_init_sectors=init,
        metadata_cold_init_ps=str(cold),contender_wait_upper_ps=str(wait),serialized_total_upper_ps=str(subtotal+cold+wait),
        HBM_command_or_refill_observation=None,design_refill_policy='worst-case full-sector capture for every modeled read and partial write; not actual PHY command count',
        measured_physical_latency=False,hardware_admitted=False,whole_token=False,RF_producer_write_charge_reused=True,
        bound_is_standalone_not_incremental_Dewey_charge=True,source_RF_ACK_intervals_must_be_reused=True,
        existing_Dewey_interval_reconciliation_required=True,actual_program_contender_composition=False)


def model():
    plan=compile_plan();source=inputs();parent=json.loads(source['parent_model.json'])
    # Nine finite entries/bank: eight SM-side clients in that slice plus one
    # KV/metadata client sharing a single rank credit. Potential routing reach,
    # not proof of actual emitted whole-program contenders or installed policy.
    descriptor=64+11+21+5+6+5+32+1+34+32+3+1+32+9+5+3+16
    queue_bits=32*9*descriptor;arb_bits=32*(4+4+1)
    data_bits=256;parent_bits=64+64+13+11+2+2+4+16+128+3+1+1+3+1+9
    total=queue_bits+arb_bits+data_bits+parent_bits
    gate_upper=32*9*descriptor*2+32*9*4+256*2+32*32
    per_die=(total*.2916+gate_upper*.3)/.5/1e6
    return dict(schema='KV_VALIDITY_FENCE_SOURCE_G0_R1',status='FAIL_INSTALLED_VALIDITY_FENCE_AND_COMPOSED_BOUND',
        source_findings=dict(logical_zero_is_not_initialized_HBM=True,source_bitmap_precedes_record=True,
            writer_lock_must_mask_prefix_reads_through_both_visible=True,source_RF_two_copy_ACK_registered=True,
            context_has_no_connected_KV_L2_validity_refill_fence=True),
        source_demands=dict(groups=72,payload_sectors_each_direction=19584,partial_payload_RMW=18432,
            metadata_partial_writes=432,source_metadata_reads=74304,source_metadata_write_bytes=5256,
            source_RF_producer_vectors=576,required_producer_RF_copy_facts=1152,source_combined_producer_ACKs=576,decoded_persistent_spill_sectors=9216),
        source_semantics='FP8/U8 and metadata bits opaque; preserve exact source bitmap/record order under writer exclusion; no rounding changes',
        constructive_design=dict(sector_buffer_bytes_per_rank=32,replicas_per_die=1,
            request_descriptor_bits=descriptor,descriptor_fields=dict(source_identity=145,address=34,mask=32,operation=3,valid=1,provider_reference=32,RF_slot=9,SM=5,phase=3,physical_tag=16),
            potential_clients_per_bank=9,queue_bits_per_die=queue_bits,
            arbitration_bits_per_die=arb_bits,parent_identity_bits_per_die=parent_bits,total_state_bits_per_die=total,
            gate_equivalents_upper_ASSUMED=gate_upper,incremental_footprint_mm2_per_die_ASSUMED=per_die,
            full_die_with_delta_upper_only={k:v['with_RMW_upper_mm2']+per_die for k,v in parent['composed_area_upper_only'].items()},
            reuse_policy='Candidate replaces abstract KV buffer obligations; do not add its buffer or RF/RMW/highword costs to earlier intervals twice',
            ports=dict(old_capture_bits=256,write_bits=256,byte_mask_bits=32,address_bits=34,source_identity_bits=145,
                RF_pair_read_bits=8192,RF_write_payload_bits=4096,RF_physical_copies=2,shared64_bits=512),
            routing_tracks_lower=dict(old_capture=256,write=256,mask=32,address=34,identity=145),
            mux_fanout_max=9,source32SM_organisation_preserved=True,
            DeepSeek_row_is_geometry_screen_only_no_DS_operator_binding=True),
        admission_requirements=list(COST_KEYS)+['actual contenders by bank and fully bounded hold intervals','full-context slot/clock/PG/cut admission'],
        numeric_cost_policy='price(plan,complete_positive_profile) refuses missing/zero costs; no automatic provisional profile or software-tick conversion',
        matched_leaf_edges=plan['source_leaf_edges'],leaf_edges_are_not_physical_SS_FF=True,
        timing_profile_installed=False,physical_cuts_admitted=False,installed_numeric_provider_reference_directory=False,installed_tag_allocator_and_ACK_routing=False,engine_build_ready=False,hardware_admitted=False,
        full_token_lifecycle='UNKNOWN_NOT_CAPTURED')


def outputs():
    return {'plan.json.gz':gzip.compress(canonical(compile_plan()),mtime=0),
            'model.json':json.dumps(model(),indent=2,sort_keys=True).encode()+b'\n'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--verify',action='store_true');p.add_argument('--profile',type=Path);a=p.parse_args()
    data=outputs()
    if a.profile:
        data['priced_service.json']=json.dumps(price(compile_plan(),json.loads(a.profile.read_bytes())),indent=2,sort_keys=True).encode()+b'\n'
    if a.verify:
        for name,raw in data.items():require((BASE/name).read_bytes()==raw,'byte exact replay '+name)
        print('PASS exact source-bound validity/fence model replay')
    else:
        require(a.output is not None,'explicit new output directory');a.output.mkdir(parents=True,exist_ok=True)
        for name,raw in data.items():(a.output/name).write_bytes(raw)


if __name__=='__main__':main()
