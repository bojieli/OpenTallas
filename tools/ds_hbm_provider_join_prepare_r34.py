"""Join source windows/static images and all40 independent-group programs.
Fresh output metadata preparation; never launches a numerical token.
"""
import argparse,copy,gzip,hashlib,json,math
from collections import Counter
from pathlib import Path
from ds_hbm_group_provider_r34 import canonical,lower_native
from ds_hbm_source_inputs_r34 import sha

def prepare(native_path,dispatch_path,inputs,manifest_path,output):
    if output.exists():raise ValueError('fresh immutable provider join output')
    native=json.loads(gzip.decompress(native_path.read_bytes()));dispatch=json.loads(gzip.decompress(dispatch_path.read_bytes()))
    if dispatch['source_program_sha256']!=sha(native_path):raise ValueError('native/dispatch source hash')
    lowered,witness=lower_native(native);raw=gzip.compress(canonical(lowered),mtime=0)
    joined=copy.deepcopy(dispatch);joined['source_program_sha256']=hashlib.sha256(raw).hexdigest()
    for row in witness:
        old,new=row['old_template'],row['new_template'];entry=joined['PC_dispatch'][row['PC']]
        model=copy.deepcopy(dispatch['templates'][old]);counts=Counter()
        for n in lowered['templates'][new]['code']:counts[n['op']]+=max(1,math.prod(n['shape']))
        for field in ('baseline_once_scalar_evaluations','executed_primitive_scalar_projection'):model[field]=dict(counts)
        model['baseline_once_total']=sum(counts.values());model['forward_total']=sum(counts.values())
        model['group_dimension_correction']=row;model['finite_schedule_hardware_admitted']=False
        joined['templates'][new]=model
        for call in entry['calls']:
            if call['template']==old:call['template']=new
        source=lowered['instructions'][row['PC']]
        entry['rank_bindings']=source['rank_bindings'];entry['provider_bindings']=source['provider_bindings']
        for field in ('baseline_once_scalars','projected_executed_primitive_scalars'):
            if field in entry:entry[field]={op:count*len(entry['calls']) for op,count in counts.items()}
        entry['provider_transfer_reprice_required']=dict(parts_words_per_call=65536,source_fragment_ranks=64,output_words_per_call=8192,source_rank_order='8*group+contributor',calendar_admitted=False)
    manifest=json.loads(manifest_path.read_bytes());initial=json.loads(gzip.decompress((inputs/'initial_versions.json.gz').read_bytes()))
    existing={(r['version'],r['rank']) for r in manifest.get('initial_versions',[])}
    if any((r['version'],r['rank']) in existing for r in initial):raise ValueError('source initial version collision')
    manifest['initial_versions']=manifest.get('initial_versions',[])+initial
    root=Path(__file__).resolve().parents[1]
    rope=json.loads(gzip.decompress((root/'results/uarch/ds_hbm_window_retirement_r33_20261002/source_owned_rope_bindings.json.gz').read_bytes()))
    if any(k in manifest.get('view_bindings',{}) and manifest['view_bindings'][k]!=r for k,r in rope.items()):raise ValueError('source RoPE binding collision')
    manifest['view_bindings']=dict(manifest.get('view_bindings',{}),**rope)
    static=json.loads((inputs/'static_auxiliary_bindings.json').read_bytes());overlap=set(static)&set(manifest.get('view_bindings',{}))
    if overlap:raise ValueError('auxiliary source binding collision')
    manifest['view_bindings']=dict(manifest.get('view_bindings',{}),**static)
    manifest['full_token_inputs_bound']=False
    manifest['r34_scope']='data input patch; compose original finite-home bridge and runtime journal reservation before use; no launch'
    manifest['native_program_sha256']=hashlib.sha256(raw).hexdigest()
    # Remap any immutable refs affected by the source group-template identity.
    for row in witness:
        old_prefix=f"{row['PC']}/{row['old_template']}/";new_prefix=f"{row['PC']}/{row['new_template']}/"
        for key in list(manifest['view_bindings']):
            if key.startswith(old_prefix):manifest['view_bindings'][new_prefix+key[len(old_prefix):]]=manifest['view_bindings'].pop(key)
    output.mkdir();(output/'native.json.gz').write_bytes(raw);(output/'dispatch.json.gz').write_bytes(gzip.compress(canonical(joined),mtime=0))
    (output/'provider_manifest.json.gz').write_bytes(gzip.compress(canonical(manifest),mtime=0))
    record=dict(schema='opentallas.ds.hbm.source-input-group-join.r34',native_input_sha256=sha(native_path),dispatch_input_sha256=sha(dispatch_path),native_output_sha256=sha(output/'native.json.gz'),dispatch_output_sha256=sha(output/'dispatch.json.gz'),PCs=len(lowered['instructions']),group_PCs=witness,initial_windows=40,initial_home_refs=len(initial),static_auxiliary_refs=len(static),inherited_source_RoPE_refs=len(rope),source_declared_window_payload_bytes_per_rank=10403840,group_parts_bytes_per_call=262144,group_output_bytes_per_call=32768,materialized_group_workspace_bytes_conservative=524288,software_scratch_capacity_per_rank=33554432,initial_state_provenance='seeded source reference state with released checkpoint gains, not decoded prefix',whole_state_digest_verified=False,full_token_GO=False,hardware_admitted=False,remaining='347 other auxiliary refs plus version slices/compound/persistent historical state; finite calendar must reprice eight independent group trees and address copies')
    (output/'join.json').write_bytes(canonical(record)+b'\n');return record

def main():
    p=argparse.ArgumentParser()
    for name in ('native','dispatch','inputs','manifest','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prepare(a.native,a.dispatch,a.inputs,a.manifest,a.out)
if __name__=='__main__':main()
