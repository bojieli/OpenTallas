#!/usr/bin/env python3
"""Retained r5 -> exact622 symbolic executable patches and physical-coordinate API.

No payload or RTL. Native admission failures remain failures; symbolic key/address
patches do not install cfg, ECC, HE/CROM or a remote-stage adapter.
"""
from __future__ import annotations
import argparse,collections,copy,gzip,hashlib,importlib.util,json,re
from pathlib import Path
import dsrom_full_owner_compiler as C
import dsrom_owner_cfg_interface_export as E
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/dsrom_native_weight_address_join_20261002'
PHASES=E.OUT/'export_r1/phase_directory.jsonl.gz'
JOURNAL=E.JOURNAL/'assignments.jsonl.gz'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def isa():
    spec=importlib.util.spec_from_file_location('retained_r5_ISA',D/'inputs/source/tools/hdc_isa_v41.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def encode(I,f):
    return I.encode(full_shape=True,**{k:tuple(v) if isinstance(v,list) and not k.startswith('_') else v for k,v in f.items()})

def expert_ids(ids):
    if len(ids)!=6 or any(type(x) is not int or not 0<=x<384 for x in ids) or list(ids)!=sorted(set(ids)):
        raise ValueError('six distinct ascending runtime EID values required')
    return ids

class Join:
    def __init__(self,demand,phases):
        self.demand=demand;self.phases={};self.nodes={};self.slots={};self.gu={}
        for p in phases:
            key=(p['layer'],p['alias'])
            if key in self.phases:raise ValueError('duplicate phase alias')
            if C.key_for(*key)!=(p['source_key_word']&((1<<30)-1)):raise ValueError('source key mismatch')
            self.phases[key]=p
        for n in demand['nodes']:
            if n['id'] in self.nodes:raise ValueError('duplicate node')
            self.nodes[n['id']]=n
            f=n.get('instruction',{});L=n['scope']
            if f.get('unit')==5 and 'EID' in f.get('_writes',[]):
                if f.get('xu_n')!=384 or f.get('xu_k')!=6:raise ValueError('runtime EID producer geometry')
                self.slots[L]=f['xu_dst']
            if f.get('unit')==3 and 'qe_wbase' in f:
                out=f.get('_writes',[])
                if len(out)==1 and re.fullmatch('GU[0-6]',out[0]):
                    self.gu.setdefault((L,out[0]),set()).add(f['qe_obase'])
        for k,addresses in self.gu.items():
            if len(addresses)!=2 or max(addresses)-min(addresses)!=576:raise ValueError('actual gate/up output halves')

    def binding(self,node_id):
        n=self.nodes[node_id];f=n.get('instruction',{});u=f.get('unit')
        qe=u==3 and 'qe_wbase' in f;me=u==1 and f.get('me_wsrc')==0
        if not(qe or me):return {'node':node_id,'classification':'NOT_WEIGHT_PHASE','reason':'actual unit/mode/source branch','instruction_unit':u}
        L=n['scope'];out=f.get('_writes',[])
        if len(out)!=1:raise ValueError('ambiguous weight output')
        dst=out[0];slot=None
        if qe:
            aliases={'QAL':'wq_a','KVAL':'wkv','Q':'wq_b','YTMP':'wo_b','EKVL':'engram.wkv','IQ':'indexer.wq_b'}
            if dst in aliases:alias=aliases[dst]
            elif re.fullmatch('GU[0-6]',dst):
                part='w1' if f['qe_obase']==min(self.gu[(L,dst)]) else 'w3'
                alias=('exp0.' if f.get('qe_ind',0) else 'shared.')+part
            elif re.fullmatch('E[0-6]',dst):alias=('exp0.' if f.get('qe_ind',0) else 'shared.')+'w2'
            else:raise ValueError('unbound QE output '+dst)
            if f.get('qe_ind',0):
                slot=f['qe_ibase']-self.slots[L]
                if not 0<=slot<6 or dst not in (f'GU{slot}',f'E{slot}'):raise ValueError('runtime selector/output slot mismatch')
                if f.get('qe_istride')!=1 or not f.get('qe_fp4'):raise ValueError('stale indexed template')
            elif dst in ('GU6','E6'):
                if f.get('qe_ind',0) or f.get('qe_fp4',0):raise ValueError('shared branch')
        else:
            aliases={'G12':'gate','CP_KVL':'compressor.wkv','CP_SCL':'compressor.wgate','CKAL':'compressor.wkv','IKA':'indexer.wk','WP':'indexer.weights_proj','LOGITS':'head'}
            if dst=='ZA':
                if f['me_wbase'] not in (0,65536):raise ValueError('source group offset')
                alias='wo_a.group'+str(f['me_wbase']//65536)
            elif dst in aliases:alias=aliases[dst]
            else:raise ValueError('unbound ME output '+dst)
        base={'node':node_id,'kind':'QE' if qe else 'ME','alias':alias,'layer':L,
              'classification':'WEIGHT_PHASE','source_node_semantic_sha256':digest(n),'template_word_sha256':n['template_word_sha256'],
              'selector_slot':slot,'selector_VM_element_address':f.get('qe_ibase') if slot is not None else None,
              'instruction_predicate':f.get('pred',0),'address_patches':{},'stage_dispatch_adapter_implemented':False}
        if alias=='head':
            return {**base,'classification':'UNBOUND_DEDICATED_HEAD','address_bound':False,'native_admission_failures':me_failures(f),
                    'reason':'622 layer field has no head allocation; do not fabricate a field phase'}
        p=self.phases[(L,alias)]
        K=f['qe_nb']*32 if qe else f['me_k']*(1<<f.get('me_split',0))
        rows=f['qe_nout'] if qe else f['me_nout']
        if (K,rows)!=(p['K_per_rank'],p['rows_per_rank']):raise ValueError('instruction/phase shape mismatch '+node_id)
        if (p['format']=='bf16')!=me or (qe and (p['format']=='fp4')!=bool(f.get('qe_fp4',0))):raise ValueError('format/provider mode')
        field='qe_wbase' if qe else 'me_wbase';basekey=p['source_key_word']&((1<<30)-1)
        if f[field]!=(65536 if alias=='wo_a.group1' else 0):raise ValueError('retained address placeholder changed')
        patches={field:{'old':f[field],'new':basekey}}
        if slot is not None:patches['qe_istride']={'old':1,'new':4096}
        choices=[self.phases[(L,alias.replace('exp0.',f'exp{e}.'))] for e in range(384)] if slot is not None else [p]
        for e,c in enumerate(choices):
            key=basekey+(e*4096 if slot is not None else 0)
            if key!=(c['source_key_word']&((1<<30)-1)):raise ValueError('expert key identity')
        return {**base,'address_bound':True,'address_patches':patches,'native_admission_failures':[] if qe else me_failures(f),
                'phase_choices':[{'expert':e if slot is not None else None,'stage':c['stage'],'phase':c['phase'],
                  'matrix_journal_ordinal':c['matrix_journal_ordinal'],'alias':c['alias'],'source_key_word':c['source_key_word'],
                  'config_logical_word_range':c['config_logical_word_range']} for e,c in enumerate(choices)],
                'runtime_selection_predicate':'accept only six distinct ascending IDs0..383 from actual EID producer; use VM[EIDbase+slot]' if slot is not None else 'instruction predicate',
                'consumer_X_FP32_VM_elements':[f['qe_xbase'],f['qe_xbase']+K] if qe else [f['me_xbase'],f['me_xbase']+K],
                'consumer_output_base_elements':f['qe_obase'] if qe else f['me_obase']*16,
                'output_format':'FP32' if me or f.get('qe_unrounded',0) else 'BF16-in-FP32-word'}

    def select(self,node_id,ids=None):
        b=self.binding(node_id)
        if not b.get('address_bound'):raise ValueError('no allocated weight provider')
        slot=b['selector_slot']
        if slot is not None:
            expert_ids(ids);return b['phase_choices'][ids[slot]]
        if ids is not None:raise ValueError('EID supplied to nonindexed branch')
        return b['phase_choices'][0]

    def patched(self,node_id,ids=None):
        b=self.binding(node_id);choice=self.select(node_id,ids);f=copy.deepcopy(self.nodes[node_id]['instruction'])
        for k,v in b['address_patches'].items():
            if f[k]!=v['old']:raise ValueError('stale patch')
            f[k]=v['new']
        actualkey=f.get('qe_wbase',f.get('me_wbase'))
        if b['selector_slot'] is not None:actualkey+=ids[b['selector_slot']]*f['qe_istride']
        if actualkey!=choice['source_key_word']&((1<<30)-1):raise ValueError('key lookup mismatch')
        return f,choice


def me_failures(f):
    tests={'xks==1':f.get('me_xks',0)==1,'xcs==k':f.get('me_xcs',0)==f['me_k'],
      'xjs==0':f.get('me_xjs',0)==0,'ots==IL8':f.get('me_ots',0)==8,'ojs==1':f.get('me_ojs',0)==1,
      'round':bool(f.get('me_round',0)),'!amax':not f.get('me_amax',0),'!mmode':not f.get('me_mmode',0)}
    return [k for k,v in tests.items() if not v]


def physical_address(matrix,phase,rank,row,k,ecc_provider=None):
    if (matrix['layer'],matrix['alias'],matrix['stage'])!=(phase['layer'],phase['alias'],phase['stage']):raise ValueError('wrong matrix owner')
    if C.sha(json.dumps(matrix['plans'],separators=(',',':')).encode())!=phase['payload_plan_sha256']:raise ValueError('wrong physical plan')
    a=C.Assignment([matrix]).address(matrix['layer'],matrix['alias'],rank,row,k)
    fmt=matrix['format'];a['scale_physical_bit_range']=([256,264] if fmt=='fp8' else [128+(k%512//256)*136,136+(k%512//256)*136]) if fmt!='bf16' else None
    a['ECC_inline_bit_range']=[272,274] if fmt=='fp4' else ([264,274] if fmt=='fp8' else [256,266])
    a['configuration']={'phase':phase['phase'],'first_word':E.config_address(phase['phase'],0),'last_word':E.config_address(phase['phase'],24)}
    if fmt=='fp4':
        if ecc_provider is None or ecc_provider['stage']!=a['stage']:raise ValueError('wrong ECC sidecar owner')
        a['ECC_extra_sidecar_first_bit']=E.sidecar_address(ecc_provider,a['ECC_sidecar_linear_bit_offset'])
        a['ECC_extra_sidecar_last_bit']=E.sidecar_address(ecc_provider,a['ECC_sidecar_linear_bit_offset']+7)
    a['physical_provider_implemented']=False
    return a


def generate(out):
    if out.exists():raise ValueError('fresh output required')
    out.mkdir(parents=True)
    receipt=json.loads((D/'inputs/source_receipt.json').read_text())
    if sha(D/'inputs/demand-r5.json.gz')!=receipt['demand_sha256']:raise ValueError('demand hash')
    for p,s in receipt['sources'].items():
        if sha(D/'inputs/source'/p)!=s['sha256']:raise ValueError('source hash '+p)
    if sha(D/'inputs/ot_v41_rom_adapt.sv')!=receipt['adapt_sha256']:raise ValueError('adapter hash')
    demand=json.load(gzip.open(D/'inputs/demand-r5.json.gz','rt'));phases=list(C.readrows(PHASES));join=Join(demand,phases);I=isa()
    bindings=[];census=collections.Counter();used=set();native_failed=[]
    for n in demand['nodes']:
        if n['kind']=='instruction':
            w=encode(I,n['instruction'])
            if hashlib.sha256(w.to_bytes(256,'little')).hexdigest()!=n['template_word_sha256']:raise ValueError('ISA template pin '+n['id'])
        b=join.binding(n['id']);bindings.append(b);census[b['classification']]+=1
        if b.get('address_bound'):
            for c in b['phase_choices']:used.add((b['layer'],c['alias']))
            f,_=join.patched(n['id'],[0,1,2,3,4,383] if b['selector_slot'] is not None else None)
            encode(I,f)
        if b.get('native_admission_failures'):native_failed.append({'node':n['id'],'failures':b['native_admission_failures']})
    if len(used)!=46509 or len(bindings)!=4887 or sum(n['kind']=='instruction' for n in demand['nodes'])!=4778:raise ValueError('exhaustive source coverage')
    C.gzrows(out/'node_bindings.jsonl.gz',bindings)
    # Stream the immutable full-model plans once; no allocator or payload rerun.
    byalias=join.phases;ec={p['stage']:p for p in C.readrows(E.OUT/'export_r1/FP4_ECC_provider_directory.jsonl.gz')}
    def addresses():
        for ordinal,m in enumerate(C.readrows(JOURNAL)):
            p=byalias[(m['layer'],m['alias'])]
            if p['matrix_journal_ordinal']!=ordinal:raise ValueError('journal identity')
            # Symbolic address API is exhaustive for all legal row,K coordinates.
            # These receipts independently exercise first/last rank-local boundaries.
            a=physical_address(m,p,0,0,0,ec.get(m['stage']))
            z=physical_address(m,p,0,m['rows']-1,m['K']-1,ec.get(m['stage']))
            yield {'layer':m['layer'],'alias':m['alias'],'stage':m['stage'],'phase':p['phase'],
                   'matrix_journal_ordinal':ordinal,'rank_slices':m['rank_slices'],'first_rank0':a,'last_rank0':z,
                   'all_rank_geometry_identical':True,'other_rank_source_coordinates':'rank_slices[rank].rows/cols origin + local row/K',
                   'exhaustive_API':'physical_address(matrix_record, phase_record, rank0..3, row, K, ECC_provider)',
                   'source_journal_contains_complete_ordered_run_map':True}
    C.gzrows(out/'physical_address_boundaries.jsonl.gz',addresses())
    result={'schema':'opentallas.dsrom.native-weight-address-join.v1','verdict':'PASS_EXHAUSTIVE_SYMBOLIC_WEIGHT_PATCHES_NATIVE_EXECUTION_BLOCKED',
      'candidate':'DS4096-TP4-S58-PAIR1','nodes':len(bindings),'native_instructions':4778,'classification':dict(census),
      'all_layer_matrix_phases_reachable':len(used),'all40_all384_experts_covered':True,'TP_ranks':[0,1,2,3],
      'native_admission_failures':native_failed,'dedicated_head_unallocated':True,
      'runtime_expert_ids':'actual VM read at retained qe_ibase; 6distinct ascending IDs0..383; stride patched1->4096; no cached or forced IDs',
      'native_source_bad_EID_guard_present':False,'invalid_EID_rule':'software contract rejects before dispatch; original adapter multiplies vi_q without range guard',
      'native_fault_does_not_suppress_s_go_proven':False,'source_fault_path':'m_ok failure or key miss sets sticky fault; original S_LOOK->S_GO is unconditional. Stop/freeze interface remains separate.',
      'symbolic_patch_execution_is_not_actual_RTL_execution':True,'cfg_ECC_raw_provider_calendar_or_whole_token_qualified':False,
      'head_and_nonweight_provider_bindings_not_fabricated':True,'allocator_rerun_or_checkpoint_payload':False,'jobs':[],
      'tool_sha256':sha(Path(__file__)),'source_input_sha256':{'demand':sha(D/'inputs/demand-r5.json.gz'),'phase_export':sha(PHASES),'assignment_journal':sha(JOURNAL),'adapter':sha(D/'inputs/ot_v41_rom_adapt.sv')},
      'next_gate':'Bind stage dispatch and native mode/rounding/operand/result ownership to cfg/codeword/ECC/HE/CROM finite accepted event calendars; head requires dedicated provider assignment. No build/physical/rate admission.'}
    (out/'model.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({k:result[k] for k in ['verdict','classification','all_layer_matrix_phases_reachable']}),flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);generate(p.parse_args().out)
