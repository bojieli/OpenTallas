#!/usr/bin/env python3
"""S81 native source-node to actual allocated row-fragment join.

Reuse the pinned checkpoint/program identity checks, not historical addresses.
Does not qualify dispatch, arithmetic, timing, or the complete token calendar.
"""
import argparse, gzip, hashlib, json
from pathlib import Path
import dsrom_s73_pair1 as M
ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / 'results/uarch/dsrom_s81_released_binding_20261004/canonical'
def execution_fragments(matrices,layer,alias,rank,expert_ids=None,selector_slot=None):
    """Bind runtime source operation to ordered row fragments and real source ranks.

    Dispatch each fragment only after its producer input is available; this API
    supplies addresses, not a zero-latency dispatch/multicast/gather assumption.
    """
    if rank not in range(4):raise ValueError('rank')
    if selector_slot is not None:
        if expert_ids is None or len(expert_ids)!=6 or any(type(e)!=int or not 0<=e<384 for e in expert_ids) or list(expert_ids)!=sorted(set(expert_ids)):
            raise ValueError('six distinct ascending runtime EIDs')
        if not 0<=selector_slot<6 or not alias.startswith('exp0.'):raise ValueError('selector identity')
        alias=alias.replace('exp0.',f'exp{expert_ids[selector_slot]}.',1)
    elif expert_ids is not None:raise ValueError('unexpected expert IDs')
    fragments=[m for m in matrices if m['layer']==layer and m.get('original_alias',m['alias'])==alias]
    if not fragments:raise KeyError((layer,alias))
    fragments.sort(key=lambda m:m.get('row_offset',0))
    expected=0
    result=[]
    for m in fragments:
        if m.get('row_offset',0)!=expected:raise ValueError('row gather gap/overlap')
        expected+=m['rows']
        a=M.physical_address(m,rank,0,0)
        result.append(dict(matrix=m,die_id=4*m['stage']+a['physical_owner_rank'],
            requested_rank=rank,source_slice=m['rank_slices'][rank],
            gather_local_rows=[m.get('row_offset',0),expected],ordered_K=m['segments'],
            result_multicast_required=a['owner_result_multicast_required'],
            dispatch_timing_qualified=False))
    return result

class SourceExecution:
    """Resolve pinned descriptor IDs into selected S81 fragments using live EID values.

    Retained node records provide source operation identity only. Old stage,
    phase, address patches and native admission verdicts never authorize selected S81.
    """
    def __init__(self,matrices,bindings,demand):
        import hashlib
        self.matrices={}
        for m in matrices:
            self.matrices.setdefault((m['layer'],m.get('original_alias',m['alias'])),[]).append(m)
        self.nodes={n['id']:n for n in demand['nodes']};self.bindings={}
        for b in bindings:
            if b['node'] in self.bindings:raise ValueError('duplicate source binding')
            if b.get('address_bound') or b.get('alias')=='head':
                n=self.nodes[b['node']]
                digest=hashlib.sha256(json.dumps(n,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                if digest!=b['source_node_semantic_sha256']:raise ValueError('source node identity')
                if n['template_word_sha256']!=b['template_word_sha256']:raise ValueError('source template identity')
            self.bindings[b['node']]=b
        if set(self.bindings)!=set(self.nodes):raise ValueError('source node coverage')
    def resolve(self,node,rank,expert_ids=None):
        b=self.bindings[node]
        if not b.get('address_bound'):raise ValueError('non-field operation requires dedicated execution interface')
        slot=b['selector_slot'];alias=b['alias']
        if slot is not None:
            if expert_ids is None or len(expert_ids)!=6 or any(type(e)!=int or not 0<=e<384 for e in expert_ids) or list(expert_ids)!=sorted(set(expert_ids)):
                raise ValueError('six distinct ascending runtime EIDs')
            alias=alias.replace('exp0.',f'exp{expert_ids[slot]}.',1)
        elif expert_ids is not None:raise ValueError('unexpected expert IDs')
        ms=self.matrices[(b['layer'],alias)]
        f=execution_fragments(ms,b['layer'],alias,rank)
        instruction=self.nodes[node]['instruction']
        qe=b['kind']=='QE'
        rows=instruction['qe_nout'] if qe else instruction['me_nout']
        K=instruction['qe_nb']*32 if qe else instruction['me_k']*(1<<instruction.get('me_split',0))
        if sum(x['matrix']['rows'] for x in f)!=rows or any(x['matrix']['K']!=K for x in f):raise ValueError('source operation dimensions')
        return dict(node=node,fragments=f,input_VM_elements=b['consumer_X_FP32_VM_elements'],
            output_VM_base=b['consumer_output_base_elements'],predicate=b['instruction_predicate'],
            output_format=b['output_format'],source_identity_verified=True,
            native_dispatch_qualified=False,calendar_qualified=False)

def rows(path):
    with gzip.open(path, 'rt') as f:
        for line in f:
            yield json.loads(line)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--canonical',type=Path,default=CANONICAL)
    ap.add_argument('--node',required=True)
    ap.add_argument('--rank',type=int,required=True)
    ap.add_argument('--expert-ids',type=int,nargs=6)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    inv=json.loads((args.canonical/'inventory.json').read_text())
    geo=(inv['stages'],inv.get('pairs_per_rank_die',inv.get('pairs_bf_stage')),
         inv.get('BF_dual_pairs',inv.get('BF_pairs_TP4',0)//max(1,4*inv['stages'])))
    if geo not in ((81,2417,519),(77,2304,512)):   # released 20261004 / 20261007 (bf_merge_ksplit)
        raise ValueError('selected S81 allocation required')
    source=ROOT/'results/uarch/dsrom_native_weight_address_join_20261002'
    demand_path=source/'inputs/demand-r5.json.gz'
    bindings_path=source/'r3/node_bindings.jsonl.gz'
    with gzip.open(demand_path,'rt') as f: demand=json.load(f)
    bindings=list(rows(bindings_path))
    binding=next(b for b in bindings if b['node']==args.node)
    alias=binding['alias']
    if binding['selector_slot'] is not None:
        if args.expert_ids is None: raise ValueError('runtime expert IDs required')
        alias=alias.replace('exp0.',f"exp{args.expert_ids[binding['selector_slot']]}.",1)
    matrices=[]; phase_by_stage={}
    for m in rows(args.canonical/'matrix_map.jsonl.gz'):
        stage=m['stage']; phase=phase_by_stage.get(stage,0)
        phase_by_stage[stage]=phase+1
        if m['layer']==binding['layer'] and m.get('original_alias',m['alias'])==alias:
            m['selected_phase']=phase
            matrices.append(m)
    result=SourceExecution(matrices,bindings,demand).resolve(args.node,args.rank,args.expert_ids)
    result['canonical_matrix_map']=str(args.canonical/'matrix_map.jsonl.gz')
    result['runtime_expert_ids']=args.expert_ids
    result['source_inputs']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [demand_path,bindings_path]}
    result['selected_return_generator_pin']='58168eb1d'
    result['return_inventory_bound']=True
    result['native_return_execution_qualified']=False
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({'node':args.node,'rank':args.rank,'fragments':len(result['fragments']),
                      'source_identity_verified':True,'out':str(args.out)}))

if __name__=='__main__':main()
