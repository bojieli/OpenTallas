"""Failclosed composition from rich r30 runtime manifest and r34/r35 data patches."""
import argparse,copy,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def compose(base,patch,payloads,journal_root):
    required={'persistent_fragment_extent','provider_module_sha256','journal_capacity_bytes','checkpoint_initial_embedding','journal_root','full_token_launch_ready'}
    if not required<=base.keys():raise ValueError('rich source runtime manifest required; minimal checkpoint manifest is data inventory only')
    for k in ('checkpoint_revision','checkpoint_index_sha256','checkpoint_path','generation'):
        if base[k]!=patch[k]:raise ValueError('checkpoint/generation manifest mismatch')
    out=copy.deepcopy(base);out['initial_versions']=patch['initial_versions'];out['view_bindings']=dict(base.get('view_bindings',{}))
    for collection in (patch['view_bindings'],payloads):
        for key,r in collection.items():
            if key in out['view_bindings'] and out['view_bindings'][key]!=r:raise ValueError('immutable provider binding collision')
            out['view_bindings'][key]=r
    out['native_program_sha256']=patch['native_program_sha256']
    recipe=out['checkpoint_initial_embedding'];inputs=ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/inputs'
    for path_key,hash_key,name in [('initializer_source','initializer_sha256','initializer.py.snapshot'),('token_history_source','token_history_sha256','initial_token_history.json')]:
        p=inputs/name
        if sha(p)!=recipe[hash_key]:raise ValueError('committed source initial embedding/history pin')
        recipe[path_key]=str(p.resolve())
    for flag in ('full_token_launch_ready','full_token_inputs_bound','full_token_GO','hardware_admitted'):out[flag]=False
    out['provider_module_sha256']=sha(ROOT/'tools/h3_ds_checkpoint_provider_r34.py')
    out['provider_module']='tools/h3_ds_checkpoint_provider_r34.py';out['journal_root']=str(journal_root.resolve())
    out['source_manifest_provenance']='rich r30 runtime manifest plus explicit r34 data patch and r35 checkpoint payloads; all admission flags false'
    return out

def main():
    p=argparse.ArgumentParser()
    for name in ('base','patch','payloads','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh manifest output')
    base=json.loads(a.base.read_bytes());patch=json.loads(gzip.decompress(a.patch.read_bytes()));payloads=json.loads(a.payloads.read_bytes())
    out=compose(base,patch,payloads,a.out.with_name(a.out.stem+'.journal'));a.out.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
