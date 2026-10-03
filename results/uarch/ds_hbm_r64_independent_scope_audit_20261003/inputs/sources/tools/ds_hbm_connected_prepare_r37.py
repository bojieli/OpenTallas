"""Metadata-only connected input preparation; never executes numerical kernels."""
import argparse,copy,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002'
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def classify(op,name,b,manifest):
    family=op['family'];kind=b['kind']
    if family=='attend' and name in ('q_own','rows','sink'):return 'R37_SOURCE_ATTENTION_RESHAPE_CONCAT_HEAD_SLICE'
    if family=='topk_merge' and name in ('ids','scores'):return 'DYNAMIC_R37_ORDERED_ADDRESSED_CANDIDATE_MERGE'
    if kind=='zero_initial_partial_destination':return 'R37_EXPLICIT_SOURCE_DECLARED_ZERO_INITIALIZATION'
    if family=='index_scores' and name in ('keys','key_codes','key_exp','query_codes','query_exp'):return 'DYNAMIC_R36_HISTORY_QUERY_REQUIRES_ACTUAL_PRODUCER'
    if family=='kv_gather' and name in ('selected_ckv_codes','selected_ckv_scales','selected_row_ids'):return 'DYNAMIC_R36_SELECTED_ROWS_REQUIRES_ACTUAL_SEL_APPEND'
    if family=='all_gather' and name in ('parts','ownership_mask'):return 'DYNAMIC_SAGAN_ADDRESSED_SPARSE_SOURCE'
    if name in ('route_weight','expert_outputs'):return 'DYNAMIC_SAGAN_ADDRESSED_ORDERED_SOURCE'
    if family=='all_reduce' and name=='parts':return 'R34_SOURCE_BOUND_GROUP_REQUIRES_2D05_RUNTIME_TILE_INTEGRATION'
    if kind=='explicit_auxiliary_provider':return 'IMAGE_BOUND' if str(op['pc'])+'/'+b['_template']+'/'+name in manifest.get('view_bindings',{}) else 'UNBOUND_AUXILIARY'
    if kind in ('immutable_weight_provider','immutable_parameter_provider'):return 'RELEASED_CHECKPOINT_SOURCE_DECLARED_READ_NOT_YET_EXECUTED'
    if kind=='versioned_operand':return 'DYNAMIC_SOURCE_VERSION_REQUIRES_ACTUAL_PRODUCER'
    return 'UNSUPPORTED_KIND'
def prepare(native,dispatch,manifest,native_hash,dispatch_hash):
    if (len(native['instructions']),len(native['coverage']['families']))!=(2213,30):raise ValueError('complete native scope required')
    if native_hash!=manifest['native_program_sha256'] or native_hash!=manifest['query_field_homes']['source_native_sha256']:raise ValueError('actual native/home pin mismatch')
    if len(dispatch['PC_dispatch'])!=2213:raise ValueError('full native dispatch coverage')
    rows=[]
    for op,d in zip(native['instructions'],dispatch['PC_dispatch']):
        if (op['pc'],op['family'])!=(d['pc'],d['family']):raise ValueError('versioned dispatch identity')
        for template,bindings in op['provider_bindings'].items():
            for name,b in bindings.items():
                record=dict(b,_template=template);status=classify(op,name,record,manifest)
                rows.append(dict(PC=op['pc'],family=op['family'],template=template,name=name,status=status,source_binding=b,LOAD=native['templates'][template]['providers'][name]))
    out=copy.deepcopy(manifest);out['provider_module']='tools/h3_ds_connected_provider_r37.py';out['provider_module_sha256']=sha(ROOT/out['provider_module'])
    for flag in ('full_token_launch_ready','full_token_inputs_bound','full_token_GO','hardware_admitted'):out[flag]=False
    out['source_dispatch_sha256']=dispatch_hash
    out['connected_provider_scope']='r36 query/history over exact6924 sparse/route/expert source views; source arithmetic remains native driver only'
    out['remaining_bindings_require_runtime_or_materialization']=True
    return out,rows

def main():
    p=argparse.ArgumentParser()
    for n in ('native','dispatch','manifest','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output directory required')
    out,rows=prepare(load(a.native),load(a.dispatch),load(a.manifest),sha(a.native),sha(a.dispatch))
    a.out.mkdir();out['journal_root']=str((a.out/'actual-execution-journal').resolve())
    (a.out/'provider_manifest.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
    (a.out/'bindings.json.gz').write_bytes(gzip.compress(json.dumps(rows,sort_keys=True,separators=(',',':')).encode(),mtime=0))
    counts={s:sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})}
    (a.out/'readiness.json').write_text(json.dumps(dict(status='CONNECTED_METADATA_PREPARED_NO_INPUT_GO',native_sha256=sha(a.native),dispatch_sha256=sha(a.dispatch),bindings=counts,distinct_unbound_auxiliary_refs=sorted({str(r['PC'])+'/'+r['name'] for r in rows if r['status']=='UNBOUND_AUXILIARY'}),full_token_GO=False,actual_execution_journal_exists=False,hardware_qualified=False),sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
