#!/usr/bin/env python3
"""Atomic C0/V1 software ownership contract over actual H1 RF geometry.

No RTL or installed rank/SM map is fabricated. A connection inventory is an
explicit input; software protocol controls do not certify installed hardware.
V1's existing command lease and costs are loaded from the immutable owner pin.
"""
import copy, functools, hashlib, json, pathlib, threading, types, re, collections
from h4_c0_model import pinned, H1, NATIVE, ROOT
from h4_c0_bridge import AdmissionError
from uarch_model import DFF_UM2,GPU_LOGIC_UTIL

V1='f7fa8e290d419f6de3356385c0b55ded768c2090'
OUT=ROOT/'results/uarch/h4_c0_v1_owner_lock_20261002'

@functools.lru_cache(maxsize=1)
def v1_api():
    raw=pinned('tools/h4_v1_g0_model.py',V1)
    module=types.ModuleType('C0_V1_immutable_owner_API')
    module.__file__=str(ROOT/'tools/h4_v1_g0_model.py')
    exec(compile(raw,'V1@'+V1,'exec'),module.__dict__)
    return module

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))

class PhysicalBindings:
    """Exact logical-owner to named installed-RF mapping, with alias exclusion.

    Inventory attestation is not a physical qualification result. Source-only
    H1 evidence cannot supply this mapping and is never inferred as rank0/SM0.
    """
    def __init__(self,inventory,*,protocol_control=False):
        if inventory.get('schema')!='C0_PHYSICAL_RF_CONNECTION_MAP_V1':raise AdmissionError('physical connection map required')
        self.inventory=copy.deepcopy(inventory);self.mapping={}
        if not re.fullmatch('[0-9a-f]{40}',inventory.get('connection_source_pin','')) or not re.fullmatch('[0-9a-f]{64}',inventory.get('connection_source_sha256','')):
            raise AdmissionError('pinned actual connection inventory required')
        self.protocol_control=protocol_control
        if not protocol_control:
            path=inventory.get('connection_source_path','')
            if not path or pathlib.PurePosixPath(path).is_absolute() or '..' in pathlib.PurePosixPath(path).parts:
                raise AdmissionError('immutable installed connection inventory path required')
            raw=pinned(path,inventory['connection_source_pin'])
            if hashlib.sha256(raw).hexdigest()!=inventory['connection_source_sha256']:
                raise AdmissionError('installed connection inventory source hash mismatch')
            recorded=json.loads(raw)
            if recorded.get('schema')!='C0_PHYSICAL_RF_CONNECTION_MAP_V1' or recorded.get('bindings')!=inventory['bindings']:
                raise AdmissionError('physical mapping differs from immutable connection inventory')
        for row in inventory['bindings']:
            model=row['model'];rank=row['rank'];sm=row['SM']
            if model not in ('Qwen','DeepSeek') or type(rank)!=int or not 0<=rank<(2 if model=='Qwen' else 96) or type(sm)!=int or not 0<=sm<32:
                raise AdmissionError('logical rank/SM binding extent')
            key=(model,rank,sm)
            if key in self.mapping:raise AdmissionError('duplicate rank/SM binding')
            if not row.get('physical_RF_id') or not row.get('hierarchy') or row.get('RF_module')!='ot_gpu_rf_service':
                raise AdmissionError('exact physical RF instance required')
            if row.get('vectors')!=512 or row.get('lanes')!=128 or row.get('word_bits')!=32 or row.get('mirrors')!=2:
                raise AdmissionError('actual H1 RF geometry required')
            self.mapping[key]=copy.deepcopy(row)
    def resolve(self,model,rank,sm):
        key=(model,rank,sm)
        if key not in self.mapping:raise AdmissionError('unmapped installed physical rank/SM')
        return self.mapping[key]

class AtomicV1Owners:
    """One indivisible owner per physical RF across models/ranks/contenders.

    Holds through all reads, compute, low/high mirrored writes, done acceptance,
    source consumer capture and matching reverse grant. No actual port is driven.
    """
    def __init__(self,bindings,*,enabled=False,software_model=False):
        if not enabled or not software_model:raise AdmissionError('default OFF; software ownership model only')
        self.bindings=bindings;self.live={};self.trace=collections.deque(maxlen=4096);self.watermarks={};self.guard=threading.RLock()
    def accept(self,command):
        with self.guard:
            required={'model','family','source_PC','program_sha256','template_id','ordered_step_index',
                'owner_tag','generation','rank','SM','opcode','source_bittypes','destination_bittype',
                'source_version_home_refs','destination_version_home_ref','predicate','active_lanes','source_attrs_rounding'}
            if not required<=set(command):raise AdmissionError('complete C0/V1 typed command required')
            c=copy.deepcopy(command);model=c['model'];rank=c['rank'];sm=c['SM']
            if type(rank)!=int or type(sm)!=int or type(c['active_lanes'])!=int:
                raise AdmissionError('integer physical owner and lane fields required')
            if any(type(width)!=int for width in c['source_bittypes']) or type(c['destination_bittype'])!=int:
                raise AdmissionError('integer source bittypes required')
            binding=self.bindings.resolve(model,rank,sm);physical=binding['physical_RF_id']
            if physical in self.live:raise AdmissionError('physical RF atomic owner busy')
            for field in ('owner_tag','generation'):
                if type(c[field])!=int or not 0<=c[field]<2**64:raise AdmissionError('owner tag/generation width')
            watermark=(c['generation'],c['owner_tag'])
            if physical in self.watermarks and watermark<=self.watermarks[physical]:
                raise AdmissionError('physical owner tag/generation replay; fresh monotonic C0 owner required')
            for field in ('source_PC','ordered_step_index'):
                if type(c[field])!=int or c[field]<0:raise AdmissionError('source instruction identity')
            if len(c['source_version_home_refs'])!=len(c['source_bittypes']):raise AdmissionError('source home/bittypes disagree')
            cost=v1_api().command_cost(c['opcode'],c['source_bittypes'],c['destination_bittype'],elements=c['active_lanes'])
            words=[]
            for index,(home,width) in enumerate(zip(c['source_version_home_refs'],c['source_bittypes'])):
                self.validate_home(home,c,binding,width)
                for part,slot in enumerate(home['RF_vectors']):words.append(dict(operand=index,word=part,slot=slot))
            self.validate_home(c['destination_version_home_ref'],c,binding,c['destination_bittype'])
            if len(words)!=cost['RF_read_vectors']:raise AdmissionError('physical source word count mismatch')
            pairs=[]
            for index in range(0,len(words),2):
                pair=words[index:index+2]
                pairs.append(dict(addresses=[w['slot'] for w in pair]+([pair[0]['slot']] if len(pair)==1 else []),
                    used_ports=[True,len(pair)==2],source_words=pair))
            if len(pairs)!=cost['RF_read_pair_transactions']:raise AdmissionError('serialized read pair count mismatch')
            identity=(rank,sm,c['owner_tag'],c['generation'])
            lease=v1_api().CommandLease();lease.accept(identity,cost)
            token=(physical,model,rank,sm,c['owner_tag'],c['generation'])
            self.live[physical]=dict(token=token,identity=identity,command=c,binding=binding,cost=cost,lease=lease,
                read_pairs=pairs,read_pending=None,writes=c['destination_version_home_ref']['RF_vectors'],write_pending=None,
                consumer=False,reverse=False,provider_pending={},last_sequence=-1,last_fragment_sequence=-1,fragment_count=0)
            self.watermarks[physical]=watermark
            self.trace.append(dict(event='atomic_accept',owner=token,read_pairs=pairs,
                writes=self.live[physical]['writes'],hardware_qualification=False,
                connection_scope='protocol control only' if self.bindings.protocol_control else 'source-pinned connection map; physical gates still required'))
            return token
    @staticmethod
    def validate_home(home,c,binding,width):
        if home.get('rank')!=c['rank'] or home.get('SM')!=c['SM'] or home.get('generation')!=c['generation'] or home.get('physical_RF_id')!=binding['physical_RF_id']:
            raise AdmissionError('actual rank/SM/generation/home mapping mismatch')
        slots=home.get('RF_vectors');expected=(c['active_lanes']*max(32,width)+4095)//4096
        if not home.get('version') or not home.get('lease') or not isinstance(slots,list) or len(slots)!=expected:
            raise AdmissionError('explicit typed RF version/home lease required')
        if any(type(slot)!=int or not 0<=slot<512 for slot in slots) or len(set(slots))!=len(slots):
            raise AdmissionError('RF slot/word extent')
    def owner(self,token):
        state=self.live.get(token[0]) if isinstance(token,tuple) and token else None
        if state is None or state['token']!=token:raise AdmissionError('stale/wrong physical owner')
        return state
    def read_accept(self,token,pair):
        with self.guard:
            s=self.owner(token);lease=s['lease'].live
            if s['provider_pending'] or s['read_pending'] is not None or lease['computed'] or pair!=lease['reads'] or pair>=lease['required_reads']:
                raise AdmissionError('read pair order/credit/provider return not drained')
            s['read_pending']=pair;return copy.deepcopy(s['read_pairs'][pair])
    def read_return(self,token,pair):
        with self.guard:
            s=self.owner(token)
            if s['read_pending']!=pair:raise AdmissionError('matching accepted read response required')
            s['lease'].read_return(s['identity']);s['read_pending']=None
    def compute_complete(self,token):
        with self.guard:
            s=self.owner(token)
            if s['read_pending'] is not None or s['provider_pending']:raise AdmissionError('source return still owned')
            s['lease'].compute_complete(s['identity'])
    def write_accept(self,token,word):
        with self.guard:
            s=self.owner(token);lease=s['lease'].live
            if not lease['computed'] or s['provider_pending'] or s['write_pending'] is not None or word!=lease['writes'] or word>=lease['required_writes']:
                raise AdmissionError('low/high write order/credit')
            s['write_pending']={'word':word,'mirror_mask':0};return s['writes'][word]
    def write_mirror_ACK(self,token,word,mirror):
        with self.guard:
            s=self.owner(token);pending=s['write_pending']
            if pending is None or pending['word']!=word or mirror not in (0,1) or pending['mirror_mask']&(1<<mirror):
                raise AdmissionError('matching low/high mirror ACK required')
            pending['mirror_mask']|=1<<mirror
            if pending['mirror_mask']==3:
                s['lease'].write_ACK(s['identity'],3);s['write_pending']=None
    def consumer_accept(self,token):
        with self.guard:
            s=self.owner(token);lease=s['lease'].live
            if s['consumer'] or s['write_pending'] is not None or lease['writes']!=lease['required_writes'] or s['provider_pending']:
                raise AdmissionError('all low/high mirror ACK and provider returns required')
            s['consumer']=True
    def provider_accept(self,token,fragment):
        """Reserve one actual mapped fragment; caller supplies Kepler evidence.

        This validates a protocol receipt, never supplies missing evidence or
        infers a backing event from a metadata/digest declaration alone.
        """
        with self.guard:
            s=self.owner(token);c=s['command'];lease=s['lease'].live
            if s['provider_pending'] or s['read_pending'] is not None or s['write_pending'] is not None or s['consumer']:
                raise AdmissionError('single provider/scratch fragment credit busy')
            kind=fragment.get('kind')
            if kind not in ('source_refill','destination_writeback'):raise AdmissionError('actual refill/writeback direction required')
            if kind=='source_refill' and lease['computed']:raise AdmissionError('refill after source capture/compute')
            if kind=='destination_writeback' and lease['writes']!=lease['required_writes']:raise AdmissionError('writeback before all mirrored low/high ACK')
            identity=fragment.get('identity',{})
            expected=dict(model=c['model'],rank=c['rank'],SM=c['SM'],owner_tag=c['owner_tag'],generation=c['generation'],physical_RF_id=token[0])
            if any(identity.get(k)!=v for k,v in expected.items()):raise AdmissionError('provider exact physical owner mismatch')
            seq=identity.get('fragment_sequence')
            if type(seq)!=int or not 0<=seq<2**64:raise AdmissionError('fragment identity width')
            if seq<=s['last_fragment_sequence']:raise AdmissionError('fragment generation replay')
            if s['fragment_count']>=64:raise AdmissionError('finite64 provider fragments per V1 command')
            homes=c['source_version_home_refs'] if kind=='source_refill' else [c['destination_version_home_ref']]
            if not any(identity.get('version')==h['version'] and identity.get('lease')==h['lease'] for h in homes):
                raise AdmissionError('provider source version/home lease missing')
            from h3_deepseek_full_token_driver import workspace_extent
            extent=workspace_extent(fragment.get('workspace_extent',{}))
            address=fragment.get('byte_address');size=fragment.get('payload_bytes');scratch=fragment.get('scratch_byte_address')
            if type(address)!=int or type(size)!=int or not 0<size<=512 or address%32 or address<extent['base'] or address+size>extent['base']+extent['bytes']:
                raise AdmissionError('actual addressed provider fragment extent')
            if type(scratch)!=int or scratch<0 or scratch%64 or scratch+((size+63)//64)*64>65536:
                raise AdmissionError('actual64B finite scratch extent')
            if not re.fullmatch('[0-9a-f]{64}',fragment.get('observed_payload_sha256','')) or not re.fullmatch('[0-9a-f]{64}',fragment.get('provider_source_sha256','')):
                raise AdmissionError('observed actual payload and provider source pins required')
            s['provider_pending'][seq]=dict(fragment=copy.deepcopy(fragment),phase=0)
            s['last_fragment_sequence']=seq;s['fragment_count']+=1
    def provider_event(self,token,fragment_sequence,event):
        with self.guard:
            s=self.owner(token);p=s['provider_pending'].get(fragment_sequence)
            if p is None:raise AdmissionError('unmatched accepted provider fragment')
            f=p['fragment']
            phases=['software_backing_store_read_return' if f['kind']=='source_refill' else 'software_backing_store_write_commit',
                    'consumer_accept','validated_reverse_grant']
            if event.get('event')!=phases[p['phase']] or event.get('identity')!=f['identity'] or event.get('byte_address')!=f['byte_address'] or event.get('payload_bytes')!=f['payload_bytes'] or event.get('payload_sha256')!=f['observed_payload_sha256']:
                raise AdmissionError('actual backing/address/payload/consumer/reverse receipt mismatch')
            sequence=event.get('sequence')
            if type(sequence)!=int or not 0<=sequence<2**64 or sequence<=s['last_sequence']:raise AdmissionError('causal provider sequence order')
            s['last_sequence']=sequence;p['phase']+=1
            if p['phase']==3:del s['provider_pending'][fragment_sequence]
    def reverse_grant(self,token,receipt):
        with self.guard:
            s=self.owner(token)
            expected=dict(model=token[1],rank=token[2],SM=token[3],owner_tag=token[4],generation=token[5],physical_RF_id=token[0])
            if not s['consumer'] or s['reverse'] or s['provider_pending'] or receipt.get('event')!='validated_reverse_grant' or receipt.get('identity')!=expected:
                raise AdmissionError('matching actual consumer/reverse grant required')
            sequence=receipt.get('sequence')
            if type(sequence)!=int or not 0<=sequence<2**64 or sequence<=s['last_sequence']:raise AdmissionError('reverse sequence stale')
            s['last_sequence']=sequence;s['reverse']=True
    def retire(self,token):
        with self.guard:
            s=self.owner(token)
            s['lease'].retire(s['identity'],s['consumer'],s['reverse'])
            del self.live[token[0]];self.trace.append(dict(event='atomic_retire',owner=token))
    def contender_allowed(self,physical,contender_token=None):
        with self.guard:
            s=self.live.get(physical)
            return s is None or s['token']==contender_token

def export_contract():
    paths=['rtl/gpu/ot_gpu_full_sm_service.sv','rtl/gpu/ot_gpu_rf_service.sv','rtl/test/hbm_rf_visibility/tb_connected_rf_visibility.sv']
    pins={path:dict(commit=H1,sha256=hashlib.sha256(pinned(path,H1)).hexdigest()) for path in paths}
    pins['tools/h4_v1_g0_model.py']=dict(commit=V1,sha256=hashlib.sha256(pinned('tools/h4_v1_g0_model.py',V1)).hexdigest())
    worst=v1_api().command_cost('SELECT',[32,64,64],64,128)
    return dict(schema='H4_C0_ATOMIC_V1_OWNER_CONTRACT_V1',V1_pin=V1,H1_pin=H1,source_pins=pins,
        atomic_owner_fields=['physical_RF_id','model','rank','SM','owner_tag','generation'],
        owner_tag_policy='C0 allocates globally monotonic(generation,owner_tag) per physical RF, not reset-to1 per source PC; stale retired tags never alias a later command',
        source_join_fields=['family','source_PC','program_sha256','template_id','ordered_step_index','source_bittypes','destination_bittype','source_version_home_refs','destination_version_home_ref','predicate','active_lanes','source_attrs_rounding'],
        worst_case=worst,source_read_word_order=['predicate.low','a.low','a.high','b.low','b.high'],
        serialized_read_pairs=[['predicate.low','a.low'],['a.high','b.low'],['b.high','unused duplicate b.high']],
        ordered_destination_writes=['low:both mirror ACK','high:both mirror ACK'],
        owner_release_guard='all3 accepted read responses, compute, both low/high mirrored ACKs, consumer acceptance, matched validated reverse grant, all provider fragment credits drained',
        exclude_contenders=['unrelated host_rd','unrelated host_wr','matrix_capture host_wr','SIMD issue','other V1 model/rank/SM sharing same physical RF'],
        required_upstream_gate='Current H1 host ready/valid and matrix/SIMD request gates must all consult this same physical owner across every serialized pair and both writes; H1 itself does NOT implement it',
        existing_hardware_instance={'top':'tb_connected_rf_visibility','RF':'service.g_enabled.u_rf','scratch':'service.g_enabled.u_scratch','logical_rank':None,'logical_SM':None,'scope':'source instance evidence only; not an installed rank/SM connector'},
        physical_rank_SM_binding='UNKNOWN_REQUIRED_ACTUAL_INSTALLED_CONNECTION_MAP; no inference from CPU collector SM0 or block256%32',
        required_mapping_schema='C0_PHYSICAL_RF_CONNECTION_MAP_V1',installed_bindings=[],
        V1_capture_state_recharged=False,C0_512bit_command_latch_recharged=False,
        provider_fragment_credit=1,max_provider_fragments_per_command=64,scratch_port_bytes=64,scratch_capacity_bytes=65536,
        provider_identity_fields=['model','physical_RF_id','rank','SM','owner_tag','generation','version','lease','fragment_sequence'],
        provider_return_guard='actual addressed software backing/return, matching consumer accept and validated reverse grant; same source payload; no event synthesis',
        provider_writeback_guard='both low/high mirrored ACK first, then actual addressed store/consumer/reverse; no retirement while any accepted fragment remains',
        RF_cost_reconciliation='Dewey reconcile V1 RF pair/write delta with existing highword/RMW ledger once; C0 keeps its own positive fetch/decode/scoreboard/reverse charges',
        current_unknown_shared_calls=189476,RTL_written=False,hardware_admitted=False,physical_or_clock_admitted=False)

def owner_model():
    """Additive owner-gate control bound; no duplicate V1 captures/latch area.

    The command's immutable identity, source homes, V1 data captures and finite
    provider scoreboard stay in already priced C0/V1 storage. Only phase flags
    and indices are new here. Physical installed mapping is still mandatory.
    """
    fields={'phase':4,'read_pair_index':2,'write_word_index':2,'read_pending':1,
            'write_pending':1,'mirror_ACK_mask':2,'consumer_seen':1,'reverse_seen':1,
            'provider_pending':1,'provider_phase':2,'provider_fragment_count':7,
            'last_provider_fragment_sequence':64,'last_provider_event_sequence':64,
            'last_accepted_owner_tag':64,'last_accepted_generation':64,'owner_watermark_valid':1}
    new_bits=sum(fields.values());identity_bits=1+7+5+64+64
    match_logic_um2=(identity_bits+(identity_bits-1)+4*64)*0.2
    logic_um2=new_bits*DFF_UM2+match_logic_um2
    return dict(schema='H4_C0_ATOMIC_V1_OWNER_G0_ADDITIVE_MODEL_V1',fields_bits=fields,
        incremental_state_bits_per_physical_RF=new_bits,
        borrowed_command_identity_bits=identity_bits,new_identity_latch_bits=0,
        duplicate_V1_five_read_two_write_data_capture_bits=0,duplicate_C0_command_latch_bits=0,
        area_assumption='two-input XOR/equality-tree cells at0.2um2 per bit/equivalent; source DFF and utilization imported unchanged',
        incremental_logic_um2_per_physical_RF=logic_um2,incremental_footprint_mm2_per_physical_RF=logic_um2/GPU_LOGIC_UTIL/1e6,
        replicas_per_logical_rank=32,incremental_footprint_mm2_per_logical_rank=32*logic_um2/GPU_LOGIC_UTIL/1e6,
        physical_replica_count=None,replica_scope='Only installed physical RFs get locks; logical rank service counts do not imply physical replication',
        new_gate_control_bits_per_boundary=identity_bits+new_bits,
        owner_identity_interface='PROPOSED sideband identity/ready gate; H1 host ports have no tag/rank/SM inputs',
        added_payload_bytes_per_cycle=0,MACs_per_cycle=0,
        routing={'existing_C0_control_tracks':1152,'incremental_gate_control_tracks_upper':identity_bits+new_bits,
                 'composed_local_control_tracks_upper':1152+identity_bits+new_bits,'assumed_channel_tracks':3200,
                 'single_combined_RF_payload_control_channel_fits':False,'installed_route_allocation':'UNKNOWN_NO_ADDED_LAYERS'},
        composed_latency={'C0_accept_ticks':2,'C0_reverse_retire_ticks':2,'charges':'Owner match/release proposed within existing positive C0 accept/reverse phases; do not add whole V1 serialized ticks twice',
                          'new_measured_latency':None,'stall_and_clock_cost':'UNKNOWN_UNTIL_CONNECTED_PORT_GATING_AND_Dewey_COMPOSITION'},
        adoption='MANDATORY_MODEL_INTERFACE_ONLY; installed map, provider causal receipts, C0/V1 source join and physical gates still block RTL',
        headline_rate_changed=False,hardware_admitted=False)

def binding_requests():
    source=ROOT/'results/uarch/h4_c0_bridge_model_20261002/model.json'
    model=json.loads(source.read_text())
    return dict(schema='C0_SOURCE_LOGICAL_TO_PHYSICAL_BINDING_REQUESTS_V1',
        source_model_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_commit=NATIVE,source_PC_counts={k:p['PCs'] for k,p in model['programs'].items()},
        requests=[dict(model=k,rank=r,SM=sm,physical_RF_id=None,physical_scratch_id=None,
            source_context='native logical service identity; not an installed physical instance')
            for k,p in model['programs'].items() for r in range(p['ranks']) for sm in range(p['SMs_per_rank'])],
        installed_physical_bindings=0,physical_binding_qualified=False,
        required_inventory_fields=['connection_source_pin','connection_source_path','connection_source_sha256','model','rank','SM','physical_RF_id','hierarchy','RF_module','vectors','lanes','word_bits','mirrors'])

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'atomic_V1_owner_contract.json').write_text(json.dumps(export_contract(),indent=2,sort_keys=True)+'\n')
    (OUT/'owner_gate_model.json').write_text(json.dumps(owner_model(),indent=2,sort_keys=True)+'\n')
    (OUT/'physical_binding_requests.json').write_text(json.dumps(binding_requests(),indent=2,sort_keys=True)+'\n')
