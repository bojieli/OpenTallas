"""Post-only trained KV hash comparison; never reruns or writes native execution."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
import torch
ROOT=Path('/home/ubuntu/OpenTallas-qwen-trained-native-execution');sys.path.insert(0,str(ROOT/'tools'))
import qwen_trained_byte_provider as B,qwen_trained_native_run as R
from qwen_hbm_complete_executor import CheckpointWeights
from qwen_hbm_complete_reference import PostExecutionReference
import qwen3_deployment_quality as G
NATIVE_JOB=Path('/home/ubuntu/otjobs/qwen-trained-native-token-pve1-20261002-r1')
def source_retention_proof(n):
 groups={};by_rank={}
 for op in n['operations']:
  if op['opcode']in('KV_WRITE','KV_FENCE','KV_READ'):
   key=(op['attributes']['layer'],op['attributes']['die']);groups.setdefault(key,[]).append(op)
 assert len(groups)==72
 for key,ops in groups.items():assert [x['opcode']for x in ops]==['KV_WRITE','KV_FENCE','KV_READ'] and [x['pc']for x in ops]==sorted(x['pc']for x in ops)
 for allocation in n['provider_binding']['allocation']:
  rank=allocation['rank'] if 'rank'in allocation else allocation.get('die')
  for e in allocation['extents']:
   if e['role']in {'persistent_FP8_K','persistent_FP8_V','software_KV_publication_and_reader_lease_state'}:
    # r17 provider_ref carries rank identity independently of checkpoint homes.
    rank=int(e['provider_ref'].split('.')[1][4:]);by_rank.setdefault(rank,[]).append((e['base'],e['base']+e['bytes'],e['provider_ref']))
 for rank,items in by_rank.items():
  items.sort();assert all(a[1]<=b[0]for a,b in zip(items,items[1:])),(rank,items)
 assert sum(len(x)for x in by_rank.values())==146
 return groups
def run(out,admission,go_commit):
 R.validate_admission(admission,go_commit)
 for name,want in admission['runtime_package_versions'].items():assert B.version(name)==want
 assert admission['post_native_reference_only'] and not admission['native_execution'];start=time.monotonic();out=Path(out);assert out.is_dir()
 t=json.loads((NATIVE_JOB/'terminal.json').read_text());nt=json.loads((NATIVE_JOB/'native/terminal.json').read_text());assert t['verdict']==nt['verdict']=='PASS_TRAINED_NATIVE_TOKEN_POSTCHECKED' and t['exit_code']==0 and nt['native']['PCs']==1737
 assert B.sha(NATIVE_JOB/'terminal.json')==admission['native_terminal_sha256'];assert B.sha(NATIVE_JOB/'native/native_progress.jsonl')==admission['native_progress_sha256'];assert nt['input_token']==9707 and nt['position']==0
 prior=json.loads((NATIVE_JOB/'native/post_execution_comparisons.json').read_text());assert len(prior)==39 and all(r['bit_mismatches']==r['actual_nonfinite']==r['reference_nonfinite']==0 for r in prior)
 n=B.native();groups=source_retention_proof(n);trace=[json.loads(x)for x in(NATIVE_JOB/'native/native_progress.jsonl').read_text().splitlines()];assert [x['pc']for x in trace]==list(range(1737));actual={op['pc']:{o['version']:o for o in row['outputs']}for op,row in zip(n['operations'],trace)}
 weights=CheckpointWeights(n['source_program'],admission['checkpoint_snapshot'],row_batch=128);ref=PostExecutionReference(n['source_program'],weights);c=n['source_program']['config'];nh=c['num_attention_heads']//2;kv=c['num_key_value_heads']//2;hd=c['head_dim'];cos,sin=G.rope_tables_g([0],hd,c['rope_theta'],'cpu');results=[]
 # Native already retired and independentfullreference validated every capturedX.
 # Reuse those bitvalidated predecessor arrays only as postcheck inputs.
 x=torch.from_numpy(weights.embedding(9707).copy())[None,:]
 try:
  for layer in range(36):
   if layer:x=torch.from_numpy(np.load(NATIVE_JOB/'native'/f'L{layer-1}.X.npy',allow_pickle=False).copy())[None,:]
   r=G.rstd_g(x,c['rms_norm_eps'])[:,None]
   for die in range(2):
    qkv=G.mul(ref.scaled_matrix(f'L{layer}.qkv.d{die}',x),r);q,k,v=qkv.split([nh*hd,kv*hd,kv*hd],-1)
    k=G.rmsnorm_g(k.reshape(kv,hd),torch.from_numpy(weights.constant(layer,'k').copy()),c['rms_norm_eps']);k=G.to_fp8(G.rope_g(k,cos,sin))[:,None,:];v=G.to_fp8(v.reshape(kv,hd))[:,None,:]
    op=groups[layer,die][-1];assert len(op['writes'])==2
    for kind,version,value in zip(('K','V'),op['writes'],(k,v)):
     a=value.detach().numpy().astype(np.float32);h=hashlib.sha256(a.view(np.uint32).tobytes()).hexdigest();row=actual[op['pc']][version];match=h==row['sha256'] and list(a.shape)==row['shape'];record=dict(layer=layer,die=die,kind=kind,pc=op['pc'],version=version,shape=list(a.shape),values=a.size,native_read_sha256=row['sha256'],reference_read_sha256=h,reference_nonfinite=int(np.count_nonzero(~np.isfinite(a))),exact=match,elapsed_s=time.monotonic()-start);results.append(record)
     with(out/'comparisons.jsonl').open('a')as f:f.write(json.dumps(record,sort_keys=True)+'\n');f.flush()
     if not match or record['reference_nonfinite']:raise ValueError('KV finalread exactness '+str(record))
    print(json.dumps(dict(event='POST_NATIVE_KV_REFERENCE',layer=layer,die=die,matched=True,elapsed_s=time.monotonic()-start)),flush=True)
   R.guard(admission,out)
  assert len(results)==144 and sum(x['values']for x in results)==73728
  result=dict(schema='opentallas.Qwen.post-native-final-KV-reference.v1',verdict='PASS_FINAL_KV_READ_VISIBILITY_AND_RETIREMENT',source_commit=admission['source_commit'],GO_commit=go_commit,native_GO='026847e37d735d7dcdc1d0bda8bb332d9dfd233d',native_terminal_sha256=admission['native_terminal_sha256'],native_progress_sha256=admission['native_progress_sha256'],comparison_groups=72,comparison_hashes=144,decoded_FP8_values=73728,all_hashes_equal=True,reference_nonfinite=0,one_write_then_read_per_layer_rank=True,source_mutable_extents_disjoint=True,lease_retirement_basis='PASS_BOUNDED_TILED_SOFTWARE rejects pendingwriters,readers,kvleases before return; SCORES/PV completion bothrequired; existing39fullreferencechecks PASS',final_raw_byte_snapshot_exported=False,scope='Actual lastreaddecodedK/V hash plus sourcepersistent/nooverwrite/nonalias invariants, notindependentphysicalmemorysnapshot',oracle_callbacks_into_DUT=0,native_execution=False,actual_RTL=False,physical_credit=False,rate_credit=False,elapsed_s=time.monotonic()-start,checkpoint_provenance=weights.provenance())
 except BaseException as e:
  result=dict(schema='opentallas.Qwen.post-native-final-KV-reference.v1',verdict='FAIL_INCOMPLETE',error=repr(e),completed_hashes=len(results),native_execution=False,no_automatic_retry=True,elapsed_s=time.monotonic()-start)
  (out/'terminal.json').write_bytes(B.canonical(result));raise
 (out/'terminal.json').write_bytes(B.canonical(result));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--admission',type=Path,required=True);p.add_argument('--go-commit',required=True);a=p.parse_args();print(json.dumps(run(a.out,json.loads(a.admission.read_text()),a.go_commit),sort_keys=True))
