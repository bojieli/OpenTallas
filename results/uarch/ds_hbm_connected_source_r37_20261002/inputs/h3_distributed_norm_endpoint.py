#!/usr/bin/env python3
"""Distributed source-partition/ABI implementation model; no RTL or tensor execution."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'results/uarch/h3_versioned_lowering_20261002'

def ceil(n,d):return (n+d-1)//d

def round512(n):return ceil(n,512)*512

def stripe_words(words,sm):
    # 256 F32 words = 32 whole chunk8 leaves. Never split a leaf across SMs.
    blocks,tail=divmod(words,256);full,rem=divmod(blocks,32)
    return full*256+(256 if sm<rem else tail if sm==rem else 0)

def counts(v,rank,sm,target):
    n=ceil(v['elements_per_rank'][rank]*v['bits_per_element'],32)
    # HC four planes must share dimension ownership, not flatten across planes.
    planes=4 if target=='DeepSeek' and v['name'] in ('h','attn_res','ffn_res','engram_h') else 1
    if planes==4 and n!=20480:raise ValueError('HC source shape')
    return planes*stripe_words(n//planes,sm)

def layout(v,rank,sm,target):
    planes=4 if target=='DeepSeek' and v['name'] in ('h','attn_res','ffn_res','engram_h') else 1
    return {'rank':rank,'SM':sm,'planes':planes,'global_to_local':
      'plane=floor(word/5120);dim=word%5120;block=floor(dim/256);SM=block%32;local=plane*256+dim%256' if planes==4 else
      'block=floor(word/256);SM=block%32;local=floor(block/32)*256+word%256',
      'native_RF_bank_map':'slot page=slot>>7,row=slot&127;lane bank=floor(lane/8),bit=(lane%8)*32',
      'word_count':counts(v,rank,sm,target)}

def firstfit(size,live):
    p=0
    for lo,hi in sorted(live):
        if p+size<=lo:break
        p=max(p,hi)
    return p

def distribute(target,data):
    vals=data['operands'];groups=defaultdict(list)
    for rank in range(2 if target=='Qwen' else 96):
        groups[tuple(v['elements_per_rank'][rank] for v in vals)].append(rank)
    output=[];peaks=[]
    for signature,ranks in groups.items():
        rank=ranks[0]
        for sm in range(32):
            rf_live={};spill_live={};peak_rf=32;peak_spill=0
            for v in sorted(vals,key=lambda x:(x['birth_pc'],x['id'])):
                pc=v['birth_pc'];rf_live={i:x for i,x in rf_live.items() if x[2]>=pc};spill_live={i:x for i,x in spill_live.items() if x[2]>=pc}
                if v['name'].startswith(('window.','compressed.','index_keys.','selected.')):continue
                if v['bits_per_element']==0:continue
                words=counts(v,rank,sm,target)
                if not words:continue
                vectors=ceil(words,128);live=[(lo,hi) for lo,hi,_ in rf_live.values()]
                # Native contiguous vector slots; fragmented free space spills rather than aliases.
                slot=firstfit(vectors,[(0,32)]+live)
                if slot+vectors<=512:
                    rf_live[v['id']]=(slot,slot+vectors,v['retire_pc']);home={'class':'RF','slot_first':slot,'vectors':vectors}
                else:
                    size=round512(words*4);off=firstfit(size,[(lo,hi) for lo,hi,_ in spill_live.values()]);spill_live[v['id']]=(off,off+size,v['retire_pc'])
                    peak_spill=max(peak_spill,off+size);home={'class':'spill','byte_offset':off,'bytes':size}
                peak_rf=max(peak_rf,32+sum(hi-lo for lo,hi,_ in rf_live.values()))
                output.append({'version':v['id'],'name':v['name'],'rank_group':ranks,'SM':sm,'home':home,
                  'birth_pc':pc,'retire_pc':v['retire_pc'],'word_count':words,
                  'partition':'HC_plane_dimension' if target=='DeepSeek' and v['name'] in ('h','attn_res','ffn_res','engram_h') else 'chunk32_block256'})
            peaks.append({'rank_group':ranks,'SM':sm,'peak_RF_vectors':peak_rf,'spill_bytes':peak_spill,'shared_reserved_bytes':8192})
    return {'target':target,'rank_pattern_groups':len(groups),'homes':output,'peaks':peaks,
      'whole_graph_operations':len(data['operations']),'matrix_owner_mapping':'output global row descriptor must translate to this same RF partition; no SM0 copy',
      'persistent_state_layout':'retained owner sharding; no transient-RF substitution'}

def verify_homes(d):
    # Lifetimes include retirement at same PC: source and destination stay disjoint.
    groups=defaultdict(list)
    for h in d['homes']:groups[(tuple(h['rank_group']),h['SM'])].append(h)
    for group,homes in groups.items():
        live=[]
        for h in sorted(homes,key=lambda h:(h['birth_pc'],h['version'])):
            live=[x for x in live if x['retire_pc']>=h['birth_pc']]
            p=h['home'];lo=p['slot_first'] if p['class']=='RF' else p['byte_offset'];size=p['vectors'] if p['class']=='RF' else p['bytes']
            if p['class']=='RF' and (lo<32 or lo+size>512):raise ValueError('RF aperture/workspace')
            for other in live:
                q=other['home']
                if q['class']!=p['class']:continue
                qlo=q['slot_first'] if q['class']=='RF' else q['byte_offset'];qsize=q['vectors'] if q['class']=='RF' else q['bytes']
                if lo<qlo+qsize and qlo<lo+size:raise ValueError('live home overlap')
            live.append(h)
    return True

def tree(leaves):
    n=1<<(leaves-1).bit_length();a=[f'chunk{i}' if i<leaves else '+0' for i in range(n)];nodes=[];level=0
    while len(a)>1:
        nxt=[]
        for i in range(0,len(a),2):
            name=f'L{level}_{i//2}';nodes.append({'dst':name,'left':a[i],'right':a[i+1]});nxt.append(name)
        a=nxt;level+=1
    return nodes

def norm(n,hc):
    leaves=ceil(n,8);padded=1<<(leaves-1).bit_length();groups=ceil(leaves,32)
    # Group32 is a subtree of the original power-of-two tree, not a changed reduction.
    local=[{'SM':sm,'chunks':[sm*32,min((sm+1)*32,leaves)],'padded_local_leaves':32,
       'input_RF_vectors_per_plane':2,'HC_planes':4 if hc else 1,
       'workspace':{'gather_dst':0,'square':1,'accumulator':2,'pair_left':3,'pair_right':4,'tree_dst':5,'scalar':6},
       'input_vector_local':{'left':'selected operand slot_first+plane*2','right':'selected operand slot_first+plane*2+1'},
       'partial_root_destination':'collector_SM0.RF_slot7.lane[SM]',
       'shared_home':{'root_queue_byte_offset':0,'packet_bytes':64,'max_outstanding':1},
       'leaf_order':'chunk=(SM*32+lane), term=0..7, accumulator starts at+0'} for sm in range(groups)]
    native_local=(14 if hc else 0)+16+5 # HC two128lane vectors, chunk8 square/add32lane and local tree5 levels
    root_levels=(padded//32).bit_length()-1
    native_global=root_levels+(14 if hc else 15) # global root tree5; DS divide versus Qwen reciprocal-N multiply
    native_scale=4 if hc else 0
    return {'shape':n,'active_SM_count':groups,'declared_SM_count':32,'local':local,
      'original_tree':tree(leaves),'root_tree':tree(padded//32),
      'collector_commands':[{'op':'FILL_ZERO','dst':7,'retire_after':'mirrored_ACK'}]+[{'op':'ROOT_INSERT','a':7,'b':29,'dst':7,'active':sm+1,'source_SM':sm,'retire_after':'mirrored_ACK then source commit_ACK'} for sm in range(groups)],
      'collector_input_generation':'rootRF7 write RMW serialization; slot29 filled only by accepted root decoder; exact receivedSM mask prevents duplicate ownership',
      'root_padding_SM_ids':list(range(groups,padded//32)),
      'native_FP_cycle_candidate':{'local_before_root':19*native_local,'collector_root_tree_and_tail':19*native_global,
        'scale_after_scalar_delivery':19*native_scale,'critical_path_FP_only':19*(native_local+native_global+native_scale),
        'basis':'H1 DS alias-driver19 functional edge counts; nonalias/new-loop transfer remains candidate'},
      'latency_expression':f"{19*(native_local+native_global+native_scale)}*FPedge + {28 if hc else 20}*MOVE_local + {20 if hc else 0}*INT_local + ROOT_DRAIN_{groups} + {2*root_levels}*MOVE_collector + 5*INT_tail + {'DIV_tail + SCALAR_DELIVERY_'+str(groups) if hc else 'MEAN_CONST_DELIVERY'} + INPUT_COEFFICIENT_AND_GAMMA_STAGING",
      'unbound_terms':['MOVE_endpoint','INT_endpoint','root_route_and_RF_insert','input_gamma_or_constant_provider']+(['DIV_endpoint','scalar_delivery'] if hc else []),
      'calibrated_cycles_are_not_native_GPU_ns':True,'matrix_consumer_delivery':{'native_targets':32,'per_target_NC':8 if hc else 16,'source_RF_read_bytes':n*4,'packed_BF16_source_bytes':n*2,'XSTORE_broadcast_bytes_all_targets':32*n*2*(8 if hc else 16),'native_xw_payload_bytes':256,'native_xw_beats_all_targets':ceil(32*n*2*(8 if hc else 16),256),'finite_packing_queue_depth_512B':2,'simultaneous_source_versions':1,'ordered_source_groups':'group0..activeSM-1, no arrival-order transpose','latency_term':'actual RF ACK/pack/CDC/xw_staging; full beats counted, no ideal overlap','first_matrix_issue_guard':'all xw fragments complete+x_rdy+barrier release+native weight readiness'},
      'full_latency_cycles':None}

class RootLedger:
    """Finite selected kernel exchange. IDs here are observer identities, not wide wire serials."""
    def __init__(self,n):self.n=n;self.token=0;self.pending={};self.retired=set();self.closed=False
    def offer(self,sm,version):
        if self.closed or not 0<=sm<self.n or sm in self.pending or sm in self.retired:raise ValueError('root ownership')
        self.pending[sm]=version
    def ack(self,sm,version,RF_mirrored_ack):
        if self.pending.get(sm)!=version or not RF_mirrored_ack:raise ValueError('root premature/stale ACK')
        del self.pending[sm];self.retired.add(sm)
    def seal(self,delivery_fence):
        if self.pending or len(self.retired)!=self.n or not delivery_fence:raise ValueError('root quiescence')
        self.closed=True
    def restart(self):
        if not self.closed:raise ValueError('root restart before drain')
        self.token^=1;self.pending={};self.retired=set();self.closed=False


def abi():
    return {'selected_endpoint':'ot_gpu_rf_word_int_candidate','enabled_default':False,
      'source_parent':'rtl/gpu/ot_gpu_full_sm_service.sv','RF_provider':'rtl/gpu/ot_gpu_rf_service.sv',
      'ports':{'command':'valid/ready,opcode4,phase3,a9,b9,dst9,active_lanes8','result':'held done/ready +fault1',
       'root':'F32 bits32,SM5,token1,valid/ready/commit_ACK3=41tracks;64B local staging packet carries root atword0; held until collector mirrored ACK',
       'refill':'host write4096bits9-bit slot, native mirrored ACK; version record remains in descriptor lease'},
      'opcodes':{'GATHER8':'dst lanes0..15=a[8*lane+phase],16..31=b[8*(lane-16)+phase];higher lanes+0',
       'PAIR_EVEN':'dst lane i=a[2*i] for i<active_lanes/2;others+0',
       'PAIR_ODD':'dst lane i=a[2*i+1] for i<active_lanes/2;others+0',
       'SPLAT':'dst all128lanes=b[phase]','ROOT_INSERT':'dst=a, replace laneSM with held root F32',
       'RF_COPY':'dst=a full vector under the same lease','PACK_BF16':'pack upper16 of two128-lane already-rounded F32 vectors into one512B vector; no new rounding','FILL_ZERO':'all128 words positivezero bit pattern','SHR':'logical fixed shifts1 or16','AND':'bitwise mask','XOR':'bitwise/sign XOR','IADD':'32-bit wrap add','ISUB':'32-bit wrap subtract'},
      'lease':'one command perSM reserves the complete RF through mirrored ACK/done; no SIMD or host bypass while owned',
      'partial_write_policy':'ROOT_INSERT performs full-vector RMW under RF lease; neighboring roots cannot be erased',
      'CDC':'forward FIFO41bits depth2 +reverse7bits depth2;128DFF bits perSM including Gray/synchronizer state; exact clock-phase latency remains priced term, not ideal crossing',
      'root_fence':'collector exact all roots, mirrored ACKs, both queues empty and certified no old delivery before token reuse',
      'ghost_limitation':'one-bit token cannot detect wire-identical old root after reuse; closed delivery provider must suppress old packets, otherwise restart remains blocked',
      'source_model_scope':'root receipt not causal PHY write visibility; spill retirement additionally requires actual H2 visibility/fence',
      'future_added_copy_paths':['rtl/test/h3_native_norm/ot_gpu_full_sm_service_wordint.sv','rtl/test/h3_native_norm/ot_gpu_rf_word_int.sv','rtl/test/h3_native_norm/tb_distributed_norm.sv'],
      'ABI_implemented_in_RTL':False}


def cost():
    # Same explicit proxy constants used by unified gpu_payload_transport_model.
    # Does not imply contextual SS/FF or routing placement.
    storage_bits=4096+64+32+32+128+128 # output latch, command/control, tx/rx1slot, root-valid/lane masks
    mux2_bits=32*32*7+128*32*15+128*32*8+4096 # gather8,mode select,conservative wrap-add/sublogic,insert mask
    proxy=(storage_bits*.2916+mux2_bits*.2+512)/.5/1e6
    tracks=8192+4096+51+41
    corridor={}
    for target,model in [('Qwen','qwen'),('DeepSeek','v41')]:
        fp=json.loads((ROOT/f'results/floorplan/hbm_gpu/{model}_hbm_die.json').read_text())
        width=41/fp['channels_um']['tracks_per_um_v'];b=fp['barrier_network']
        added_mm2=width*(32*b['max_leaf_um']+4*b['max_trunk_um'])/1e6
        corridor[target]={'existing_floorplan_source':f'results/floorplan/hbm_gpu/{model}_hbm_die.json','added_tracks':41,'reserved_extra_channel_width_um_candidate':width,'added_route_corridor_mm2_per_rank_candidate':added_mm2,'new_layers':0,'no_free_existing_tracks_claimed':True,'forward_reverse_use_half_duplex':True,'physical_reservation_review_pending':True}

    return {'entry':'H3_RF_WORD_INT_ROOT_ENDPOINT','replicas_per_rank':32,'MACs_per_cycle':0,
      'RF_bytes_per_transaction':{'read':1024,'mirrored_write_logical':512},'boundary_bits':{'RF_in':8192,'RF_out':4096,'root_link':32,'root_control':9},
      'storage_bits_per_SM':storage_bits,'mux2_bit_proxy_per_SM':mux2_bits,
      'CDC_bits_included_per_SM':128,'root_transfer_payload_bytes':4,'local_shared_staging_bytes':64,'logic_footprint_mm2_per_SM_proxy':proxy,'logic_footprint_mm2_per_rank_proxy':32*proxy,
      'area_basis':'uarch_model.py DFF0.2916, mux bit0.2um2,512um2control,util0.5; mux-equivalent INT bound is proposal, not mapped area',
      'route_corridor_price':corridor,'local_total_pin_tracks':tracks,'existing_payload_channel_capacity_proxy':3200,
      'existing_payload_channel_fit':tracks<=3200,'required_internal_RF_channel_tracks':8192+4096+51,
      'external_root_tracks':41,'no_hub_layer_change_assumed':False,
      'routing_requirement':'RF read/write wide pins remain local to same SM macro cluster; external root only uses message route; must reserve both separately',
      'next_model_admission_owner':'Maxwell: explicit extra corridor and within-SM branch reservation, actual DIV/store/fence latencies before execution','latency':'native FP19 measured driver; MOVE/INT/root/div remain explicit symbolic terms',
      'physical_slot_fit':None,'SSFF':False,'build_admitted':False}


def word_bits(op,a,b,phase=0,active=32):
    if len(a)!=128 or len(b)!=128 or any(not isinstance(x,int) or not 0<=x<2**32 for x in a+b):raise ValueError('typed U32 RF words')
    if not 0<=phase<8 or not 1<=active<=128:raise ValueError('word ABI range')
    out=[0]*128
    if op=='RF_COPY':out=a.copy()
    elif op=='PACK_BF16':
        for i in range(128):
            v=a if i<64 else b;j=2*(i%64);out[i]=(v[j]>>16)|(v[j+1]&0xffff0000)
    elif op=='FILL_ZERO':out=[0]*128
    elif op=='GATHER8':
        for i in range(32):out[i]=(a if i<16 else b)[8*(i%16)+phase]
    elif op in ('PAIR_EVEN','PAIR_ODD'):
        if active not in (2,4,8,16,32):raise ValueError('tree active lanes')
        for i in range(active//2):out[i]=a[2*i+(op=='PAIR_ODD')]
    elif op=='SPLAT':out=[b[phase]]*128
    elif op=='ROOT_INSERT':
        if not 0<=active-1<32:raise ValueError('root lane')
        out=a.copy();out[active-1]=b[0]
    elif op in ('SHR','AND','XOR','IADD','ISUB'):
        for i in range(128):
            if op=='SHR':out[i]=a[i]>>(1 if phase==0 else 16)
            elif op=='AND':out[i]=a[i]&b[i]
            elif op=='XOR':out[i]=a[i]^b[i]
            elif op=='IADD':out[i]=(a[i]+b[i])&0xffffffff
            else:out[i]=(a[i]-b[i])&0xffffffff
    else:raise ValueError('unsupported native opcode')
    return out

def bind_flow(d,source,target):
    selected=[o for o in source['operations'] if o['opcode']=='RSTD' and target=='Qwen' or o['opcode']=='hc_pre_norm' and target=='DeepSeek']
    index=defaultdict(list)
    for h in d['homes']:index[h['version']].append(h)
    bindings=[];templates={}
    for o in selected:
        slots=index[o['reads'][0]]
        if any(h['home']['class']!='RF' for h in slots):raise ValueError('selected norm operand requires spill')
        commands=[]
        for h in slots:
            planes=4 if target=='DeepSeek' else 1
            if h['home']['vectors']!=planes*2:raise ValueError('selected norm shape/plane packing')
            first=h['home']['slot_first'];cmd=[]
            def emit(op,**attrs):cmd.append({'op':op,**attrs,'issue_after_previous':'mirrored_ACK_or_SIMD_done',
                'command_index':len(cmd),'native_clock_latency':None})
            if planes==4:
                # Slots24,26..28 are provider-staged coefficient/round constants.
                for half in range(2):
                    for plane in range(4):
                        emit('SPLAT',a=24,b=24,phase=plane,dst=21)
                        emit('FMUL',a=first+plane*2+half,b=21,dst=11+plane,driver_cycles=19)
                    emit('FADD',a=11,b=12,dst=15,driver_cycles=19)
                    emit('FADD',a=15,b=13,dst=16,driver_cycles=19)
                    emit('FADD',a=16,b=14,dst=17,driver_cycles=19)
                    emit('SHR',a=17,b=17,phase=1,dst=18)
                    emit('AND',a=18,b=26,dst=19)
                    emit('IADD',a=17,b=27,dst=18)
                    emit('IADD',a=18,b=19,dst=10)
                    emit('AND',a=10,b=28,dst=22+half)
                lo,hi=22,23
            else:lo,hi=first,first+1
            emit('FILL_ZERO',a=0,b=0,dst=2)
            acc=2
            for j in range(8):
                emit('GATHER8',a=lo,b=hi,phase=j,dst=0)
                emit('FMUL',a=0,b=0,dst=1,driver_cycles=19)
                nxt=8 if acc==2 else 2
                emit('FADD',a=acc,b=1,dst=nxt,driver_cycles=19);acc=nxt
            active=32;current=acc
            while active>1:
                emit('PAIR_EVEN',a=current,b=current,dst=3,active=active)
                emit('PAIR_ODD',a=current,b=current,dst=4,active=active)
                nxt=5 if current!=5 else 6
                emit('FADD',a=3,b=4,dst=nxt,driver_cycles=19);current=nxt;active//=2
            versions={first+i:f"operand.wordvector{i}" for i in range(planes*2)}
            versions.update({24:'provider.coefficient4',26:'constant.U1',27:'constant.U7FFF',28:'constant.UFFFF0000'})
            for command in cmd:
                reads=[] if command['op']=='FILL_ZERO' else [command['b']] if command['op']=='SPLAT' else [command['a'],command['b']]
                if any(x not in versions for x in reads):raise ValueError('uninitialized native RF slot')
                command['input_versions']=[versions[x] for x in reads]
                command['output_version']=f"cmd{command['command_index']}"
                versions[command['dst']]=command['output_version']
            template=hashlib.sha256(json.dumps(cmd,sort_keys=True).encode()).hexdigest()[:20];templates.setdefault(template,cmd)
            commands.append({'rank_group':h['rank_group'],'SM':h['SM'],'operand_slot_first':first,
              'command_template':template,'identity_scope':[target,o['pc'],h['SM']],'root_RF_slot':current,'root_version':versions[current],
              'command_fields_all_addresses_concrete':True,'all_commands_wait_previous_retirement':True,
              'coefficient_constant_provider_preconditions':['slots24,26,27,28 mirrored_ACK with exact source versions'] if planes==4 else [],
              'hardware_endpoints_present':False})
        bindings.append({'pc':o['pc'],'input_version':o['reads'][0],'output_versions':o['writes'],'output_homes':[h for vid in o['writes'] for h in index[vid]],'output_commit':'copy to each output version home under lease and mirrored_ACK; identical named outputs are not free aliases',
          'participant_commands':commands,'native_opcode_endpoint_ABI':'ot_gpu_rf_word_int_candidate',
          'ordinary_host_oracle_used':False,'source_opcode':o['opcode']})
    return {'bindings':bindings,'command_templates':templates,'observer_version_identity':'scope=(target,pc,rank,SM)+template version; not on-wire wide serial'}

class SpillLease:
    def __init__(self,version):self.version=version;self.state='reserved'
    def issue_write(self,version):
        if version!=self.version or self.state!='reserved':raise ValueError('spill issue identity')
        self.state='accepted'
    def visible(self,version,causal_provider):
        if version!=self.version or self.state!='accepted' or not causal_provider:raise ValueError('spill no causal visibility')
        self.state='published'
    def retire(self,version,readers_done,reverse_ACK):
        if version!=self.version or self.state!='published' or not readers_done or not reverse_ACK:raise ValueError('spill early retire')
        self.state='retired'

def resident(d,target):
    patterns={tuple(p['rank_group']) for p in d['peaks']};result=[]
    if target=='Qwen':
        import importlib.util
        spec=importlib.util.spec_from_file_location('qshape',ROOT/'tools/qwen_hbm_complete_program.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
        allocations=q.compile_program()['memory_allocation']
        for ranks in patterns:
            peaks=[p for p in d['peaks'] if tuple(p['rank_group'])==ranks];total=sum(p['spill_bytes'] for p in peaks)
            extent=next(e for e in allocations[ranks[0]]['extents'] if e['name']=='activation_scratch')
            result.append({'rank_group':list(ranks),'required_bytes':total,'source_extent':extent,'fits':total<=extent['bytes'],
              'spill_source_base':extent['base'] if total<=extent['bytes'] else None,
              'status':'REFUSED_NO_SOURCE_RESIDENT_EXTENT' if total>extent['bytes'] else 'SOURCE_EXTENT_NUMERIC_BINDING_ONLY',
              'provider_ABI':{'AW':34,'LENW':6,'BEATW':5,'TAGW':16,'sector_bytes':32,'read_commands_inflight':1,'write_commands_inflight':1},
              'vector_transfer':'16 selected-sector reads or writes per512B RF vector;4stacks128B stripe;32B writes;retain version until actual visible/readers/reverseACK',
              'reserve_reuse':'no address may be overwritten while accepted intent/read lease exists; no timer completion'})
    else:
        for ranks in patterns:
            result.append({'rank_group':list(ranks),'required_spill_bytes':sum(p['spill_bytes'] for p in d['peaks'] if tuple(p['rank_group'])==ranks),
              'status':'NO_TRANSIENT_SPILL_FOR_THIS_DISTRIBUTED_LAYOUT','persistent_or_packed_state_is_not_free_RF':True})
    return result


def build():
    manifest=json.loads((INPUT/'manifest.json').read_text())
    for path,want in manifest['outputs'].items():
        if hashlib.sha256((INPUT/path).read_bytes()).hexdigest()!=want:raise ValueError('input closure '+path)
    out={}
    for target in ('Qwen','DeepSeek'):
        with gzip.open(INPUT/(target+'.json.gz'),'rt') as f:data=json.load(f)
        out[target]=distribute(target,data);verify_homes(out[target]);out[target]['selected_command_bindings']=bind_flow(out[target],data,target);out[target]['spill_resident_bindings']=resident(out[target],target)
    selected={'Qwen_RSTD4096':norm(4096,False),'DeepSeek_HC_PRE_NORM5120':norm(5120,True)}
    return {'schema':'opentallas.H3.distributed-native-endpoint.v1','source_sha256':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in ['tools/h3_distributed_norm_endpoint.py','tools/uarch_model.py','rtl/gpu/ot_gpu_rf_service.sv','rtl/gpu/ot_gpu_full_sm_service.sv','tools/w19_hbm_tp96_isa.py','tools/qwen_hbm_complete_program.py','tools/w19_gpu_norm_calendar.py','results/floorplan/hbm_gpu/qwen_hbm_die.json','results/floorplan/hbm_gpu/v41_hbm_die.json','results/uarch/qwen_hbm_connected_20261001/common_HBM_backend_provider_binding_r2.json']},'input_manifest_sha256':hashlib.sha256((INPUT/'manifest.json').read_bytes()).hexdigest(),
      'targets':out,'selected_flow':selected,'endpoint_ABI':abi(),'unified_model_entry':cost(),
      'whole_native_software_feasibility_final':False,'hardware_generated_or_run':False,'no_CPU_oracle_cycles':True}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--verify',action='store_true');a=ap.parse_args();d=build()
    if a.verify:
        for target,data in d['targets'].items():
            with gzip.open(a.out/(target+'.json.gz'),'rt') as f:old=json.load(f)
            if data!=old:raise ValueError('distributed replay '+target)
        if json.loads(json.dumps({k:v for k,v in d.items() if k!='targets'}))!=json.loads((a.out/'model.json').read_text()):raise ValueError('model replay')
        print(json.dumps({'status':'PASS_DISTRIBUTED_LAYOUT_COMMAND_ABI_REPLAY','RTL_runs':0,'source_clock_transfer':False}));raise SystemExit(0)
    a.out.mkdir(parents=True,exist_ok=False)
    targets=d.pop('targets')
    for target,data in targets.items():
        raw=json.dumps(data,separators=(',',':')).encode()
        with (a.out/(target+'.json.gz')).open('wb') as f:
            with gzip.GzipFile(fileobj=f,filename='',mode='wb',mtime=0) as g:g.write(raw)
    (a.out/'model.json').write_text(json.dumps(d,indent=2)+'\n')
