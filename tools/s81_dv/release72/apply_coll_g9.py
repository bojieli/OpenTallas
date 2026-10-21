#!/usr/bin/env python3
"""Select actual source-qualified native32/OFF COLL configuration for G9 only."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
MODEL=ROOT/'results/arch/s81_die72_1021/g9_assembly/coll_config/MODEL.json'
def apply(table,source_ref,model,read_source):
    assert not table.get('configured_coll_g9'),'COLL configuration overlay already applied'
    paths=dict(model['source_hashes']);paths[model['mem_path']]=model['mem_sha256']
    for path,h in paths.items():assert hashlib.sha256(read_source(path)).hexdigest()==h,'exact configured COLL/source API mismatch: '+path
    defines=table.setdefault('defines',[])
    for d in model['defines']:
        if d not in defines:defines.append(d)
    refs=table.setdefault('rtl_refs',{}).setdefault(source_ref,[]);prefer=table.setdefault('prefer',[])
    for path in paths:
        if path not in refs:refs.append(path)
        p=source_ref+'/'+path
        if p not in prefer:prefer.append(p)
    table['configured_coll_g9']={'source_ref':source_ref,'defines':model['defines'],'source_sha256':paths,'closed_W_record':model['closed_record'],'module':model['module'],'params':{},'scope':'G9configuredsourcecontract only, notPQ-onlyshippingG8equivalence; Ephysicalviews/CRED12remainseparate','mem_selection':'Exact151canonicalWREG/rst_nAPI; explicitsourcepreference, originalargvpriorityrecorded','runtime_status':'NOTRUN; aggregate rebuild requires exactsource/config closure review'}
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--table',required=True,type=Path);ap.add_argument('--source-ref',required=True);a=ap.parse_args();table=json.loads(a.table.read_text());model=json.loads(MODEL.read_text());apply(table,a.source_ref,model,lambda p:subprocess.check_output(['git','-C',str(ROOT),'show',a.source_ref+':'+p]));a.table.write_text(json.dumps(table,indent=1)+'\n');print('G9_COLL_SOURCE_CONFIG native32+OFF, exact11sourcehashes/mem151; runtime NOTRUN')
if __name__=='__main__':main()
