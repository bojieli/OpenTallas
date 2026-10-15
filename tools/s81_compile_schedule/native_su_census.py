#!/usr/bin/env python3
"""Count the actually elaborated Verilator module DAG without flattening it."""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path

CUT={'ot_s81_su_swe','ot_s81_su_qbe','ot_s81_su_qne','ot_s81_su_qnh','ot_s81_su_qnr','ot_s81_su_qnt',
 'ot_s81_su_qnq','ot_s81_su_kve','ot_s81_su_kvt','ot_s81_su_kvq','ot_s81_su_cn_norm_write','ot_s81_su_cn_write',
 'ot_s81_su_ik_reduce','ot_s81_su_smt','ot_s81_su_sml','ot_s81_su_smc','ot_s81_su_smr','ot_s81_su_smd',
 'ot_s81_su_rxt','ot_s81_su_pin','ot_s81_su_moe_add_leaf','ot_s81_su_calendar_ctl','ot_hdc_delay',
 'ot_sram_1r1w_64x512_m1_r2c2','ot_sram_1r1w_128x256_m1_r2c2'}

def census(tree):
    modules={m['addr']:m for m in tree['modulesp'] if m['type']=='MODULE'}
    byname={m['name']:m for m in modules.values()}
    def children(node,path=''):
        if isinstance(node,list):
            for child in node:yield from children(child,path)
        elif isinstance(node,dict):
            kind=node.get('type')
            if kind=='CELL':
                yield (path+'.' if path else '')+node['name'],node['modp'];return
            if kind=='GENBLOCK' and node.get('name'):
                path=(path+'.' if path else '')+node['name']
            for value in node.values():
                if isinstance(value,(dict,list)):yield from children(value,path)
    cells={addr:list(children(m['stmtsp'])) for addr,m in modules.items()}
    @lru_cache(None)
    def totals(addr):
        m=modules[addr];counts=Counter({m.get('origName',m['name']):1})
        for _,child in cells[addr]:counts.update(totals(child))
        return counts
    top=byname['ot_s81_su_canonical_candidate'];counts=totals(top['addr'])
    assert counts['ot_s81_su_swe']==144,counts['ot_s81_su_swe']
    assert counts['ot_s81_su_qbe']==14,counts['ot_s81_su_qbe']
    assert counts['ot_s81_su_moe_add_leaf']==6,counts['ot_s81_su_moe_add_leaf']
    stores=[m for m in modules.values() if m.get('origName')=='ot_s81_su_calendar_store']
    assert len(stores)==1
    assert totals(stores[0]['addr'])['ot_sram_1r1w_64x512_m1_r2c2']==128
    # Dtype records may be nested. Resolve only actual top ABI bit widths.
    types={}
    def collect(x):
        if isinstance(x,dict):
            if x.get('type','').endswith('DTYPE'):types[x['addr']]=x
            for v in x.values():
                if isinstance(v,(dict,list)):collect(v)
        elif isinstance(x,list):
            for v in x:collect(v)
    collect(tree['typeTablep'] if isinstance(tree.get('typeTablep'),dict) else tree)
    ports={}
    for v in top['stmtsp']:
        if v.get('type')=='VAR' and v.get('direction') in ('INPUT','OUTPUT','INOUT'):
            dtype=types[v['dtypep']];r=dtype.get('range')
            if r:
                hi,lo=map(int,r.split(':'));width=abs(hi-lo)+1
            else:width=1
            ports[v['name']]=dict(direction=v['direction'],bits=width)
    assert ports['ck']['bits']==159,ports['ck']
    inventory=[]
    def expand(addr,path):
        m=modules[addr];kind=m.get('origName',m['name'])
        if kind in CUT:
            inventory.append(dict(source_instance=path,module=kind,elaborated_module=m['name'],
                                  physical_instance=None,clock_qualified=False));return
        for name,child in cells[addr]:expand(child,path+'.'+name)
    expand(top['addr'],top['name'])
    return dict(schema='opentallas.s81.elaborated-source-instances.v1',actual_GEN_instances=False,
        physical_leaf_qualified=False,native_programmes_bound=False,top=top['name'],ports=ports,
        module_counts=dict(counts),cut_source_instances=inventory,actual_calendar_64x512_macros=128,
        actual_SW576_SWE=144,actual_SW576_QBE=6,actual_independent_QB_QBE=8,actual_MOE_add_leaves=6)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--tree',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();r=census(json.loads(a.tree.read_text()));r['frontend_tree_sha256']=hashlib.sha256(a.tree.read_bytes()).hexdigest()
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('cut_source_instances','module_counts','ports')}))
if __name__=='__main__':main()
