"""Compose actual r35 state and charged r36 fields; retain false launch flags."""
import argparse,copy,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIGEST='b59a99c8294625778d28306924067d5bbf706979068579280d6ee40cb24e6782'
def compose(base,state_receipt,state_root,homes,journal_root):
    if state_receipt['status']!='PASS_EXACT_ENTERING_STATE_DIGEST' or state_receipt['actual_state_sha256']!=DIGEST or state_receipt['expected_state_sha256']!=DIGEST:raise ValueError('actual seeded state digest')
    out=copy.deepcopy(base)
    if out['native_program_sha256']!=homes['source_native_sha256']:raise ValueError('query field home native version pin')
    if 'persistent_fragment_extent' not in out or 'checkpoint_initial_embedding' not in out:raise ValueError('rich runtime manifest required')
    records=[]
    for r in load(state_root/'images.json'):
        if r['kind'] not in (1,2):continue
        record=dict(r,path=str((state_root/Path(r['path']).name).resolve()))
        if not Path(record['path']).is_file():raise FileNotFoundError(record['path'])
        records.append(record)
    if {(r['layer'],r['kind']) for r in records}!={(l,k) for l in (2,8,14,20) for k in (1,2)}:raise ValueError('all four actual CKV/index source pairs required')
    out['history_images']=records;out['history_source_receipt']={k:state_receipt[k] for k in ('status','actual_state_sha256','expected_state_sha256')};out['query_field_homes']=homes
    out['provider_module']='tools/h3_ds_query_provider_r36.py';out['provider_module_sha256']=hashlib.sha256((ROOT/out['provider_module']).read_bytes()).hexdigest();out['journal_root']=str(journal_root.resolve())
    for flag in ('full_token_launch_ready','full_token_inputs_bound','full_token_GO','hardware_admitted'):out[flag]=False
    out['source_state_scope']='exact reference seeded entering state, not a decoded million-token prefix'
    return out

def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def main():
    p=argparse.ArgumentParser()
    for key in ('base','state_receipt','state_root','homes','out'):p.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output required')
    out=compose(load(a.base),load(a.state_receipt),a.state_root,load(a.homes),a.out.with_name(a.out.stem+'.journal'))
    a.out.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
