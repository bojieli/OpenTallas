#!/usr/bin/env python3
"""Fail-closed artifact selector. This is not a production compiler binding."""
import argparse
import hashlib
import json
import re
from pathlib import Path
TOP='dsdv_gunit_l5_fs_guarded_1019'
EXPECTED_DIGEST='0307d1fa83fd9bb83e04e650113a456a0ee4d6592f2d331a22380b60652e18df'
def clean(s):
    return re.sub(r'//[^\n]*|/\*[\s\S]*?\*/','',s)
def select(root, top, parameters, sources=None):
    root=Path(root).resolve()
    m=json.loads((root/'results/rtl/s81_gunit_guarded_package_1019/source_manifest.json').read_text())
    if top!=TOP or m['top']!=TOP:raise ValueError('wrong top: public and ancestor aliases refused')
    if parameters!={'MUT':0}:raise ValueError('wrong specialized parameters')
    rows=m['sources']
    digest=hashlib.sha256('\n'.join(x['path']+' '+x['sha256'] for x in rows).encode()).hexdigest()
    if digest!=EXPECTED_DIGEST or m['ordered_source_sha256']!=EXPECTED_DIGEST:raise ValueError('source manifest digest')
    if sources is not None and sources!=[x['path'] for x in rows]:raise ValueError('ordered source selection mismatch')
    modules={}
    for x in rows:
        p=root/x['path']
        if not p.resolve().is_relative_to(root):raise ValueError('source outside root')
        b=p.read_bytes()
        if hashlib.sha256(b).hexdigest()!=x['sha256']:raise ValueError('source hash '+x['path'])
        defined=re.findall(r'\bmodule\s+(\w+)',clean(b.decode()))
        if defined!=x['modules']:raise ValueError('module ownership mismatch')
        for name in defined:
            if name in modules:raise ValueError('duplicate module '+name)
            modules[name]=x['path']
    if TOP not in modules:raise ValueError('missing private top')
    if 'dsdv_gunit_l5' in modules or 'dsdv_gunit_tail' in modules:raise ValueError('generic fallback')
    macro='physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v'
    if macro not in [x['path'] for x in rows]:raise ValueError('missing behavioral native view')
    return [root/x['path'] for x in rows]
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=Path(__file__).resolve().parents[3]);p.add_argument('--top',required=True);p.add_argument('--parameters',default='{"MUT":0}');p.add_argument('--sources-json')
    a=p.parse_args()
    try:
        sources=None if a.sources_json is None else json.loads(Path(a.sources_json).read_text())
        result=select(a.root,a.top,json.loads(a.parameters),sources)
    except (ValueError,OSError,KeyError) as e:p.exit(2,'GUARDED_SELECTION_FAIL '+str(e)+'\n')
    print('\n'.join(map(str,result)))
if __name__=='__main__':main()
