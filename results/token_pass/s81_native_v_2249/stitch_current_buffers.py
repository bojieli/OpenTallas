"""Prove current-source $buf identity from streamed Yosys metadata, then stitch.

Requires ijson (runtime scratch dependency); never treats a named Y/A pair as
identity without finding the actual $buf cell, equal widths and exact directions.
"""
import json
import re
import sys
from functools import lru_cache
from collections import Counter
from pathlib import Path
import ijson
from bound_die import file_sha

bound=Path(sys.argv[1]);cached=Path(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
cache=json.loads(cached.read_text())
if file_sha(bound/'bind_sinks.json')!=cache['bind_sinks_sha256']:raise ValueError('cache source differs')
if json.loads((bound/'bind_report.json').read_text()).get('parent_variants'):
    raise ValueError('source parent variants require explicit hierarchy traversal support')
index={};orig={}
with (bound/'asbuilt.json').open('rb')as f:
    for name,m in ijson.kvitems(f,'modules'):
        orig[name]=m.get('attributes',{}).get('hdlname',name)
        cells={}
        for n,c in m.get('cells',{}).items():
            rec={'type':c['type']}
            if c['type'].startswith('$'):
                rec['ports']={p:{'dir':c.get('port_directions',{}).get(p),
                                  'width':len(b)}for p,b in c.get('connections',{}).items()}
            cells[n]=rec
        index[name]=cells

@lru_cache(maxsize=None)
def actual(path):
    module='dv_die';remaining=path
    while remaining:
        names=[n for n in index.get(module,{})if remaining==n or remaining.startswith(n+'.')]
        if not names:raise ValueError('source cell absent '+path+' at '+module+'/'+remaining)
        n=max(names,key=len);cell=index[module][n];remaining=remaining[len(n):].lstrip('.')
        if not remaining:return cell
        module=cell['type']
    raise ValueError('empty path')

# Capture exact source A input descriptions once. Parsing is C-streamed; no
# repeated3GB Python JSON object construction or whole-die flatten is needed.
raw={}
with (bound/'bind_sinks.json').open('rb')as f:
    for key,d in ijson.kvitems(f,''):
        if key.startswith('u_s_')and re.fullmatch(r'.+\.A\[\d+\]',key):raw[key]=d
interfaces={};proofs=Counter();memo={};active=set()
def resolve(key,d):
    if key in memo:return memo[key]
    if key in active:raise ValueError('buffer cycle '+key)
    if isinstance(d,list)and len(d)==4 and d[0]=='pin':
        m=re.fullmatch(r'(.+)\.Y\[(\d+)\]',d[1])
        if m and d[3]is True:
            node,bit=m[1],int(m[2]);cell=actual(node);ports=cell.get('ports',{})
            interfaces[node]={'module':cell['type'],'ports':ports}
            if cell['type']=='$buf':
                if(set(ports)!={'A','Y'}or ports['A']['dir']!='input'or ports['Y']['dir']!='output'
                   or ports['A']['width']!=ports['Y']['width']or not 0<=bit<ports['A']['width']):
                    raise ValueError('actual $buf interface differs '+node)
                pin=node+'.A['+str(bit)+']'
                if pin not in raw:raise ValueError('actual $buf input absent '+pin)
                active.add(key)
                try:up=resolve(pin,raw[pin])
                finally:active.remove(key)
                if not isinstance(up,list)or len(up)!=4 or up[0]!='pin':
                    raise ValueError('actual $buf root is not a source pin '+pin)
                if any(type(x)is not int or x<0 for x in (d[2],up[2])):raise ValueError('missing stage age')
                # Keep the proven TERMINAL source's glue role. The original
                # intermediate glue role remains in interfaces and proof counts.
                d=['pin',up[1],d[2]+up[2],up[3]];proofs[node]+=1
    memo[key]=d;return d

for section in ('groups','rb'):
    for row in cache[section]:
        for bit,d in row['bits'].items():
            key=row['unit']+'.'+row['port']+'['+str(bit)+']'
            row['bits'][bit]=resolve(key,d)
cache['verified_buffer_stitching']={'asbuilt_sha256':file_sha(bound/'asbuilt.json'),
    'interfaces':interfaces,'proved_bit_paths':dict(proofs),'runtime_ijson':ijson.__version__}
(out/'raw_stitched.json').write_text(json.dumps(cache))
(out/'buffer_summary.json').write_text(json.dumps(cache['verified_buffer_stitching'],indent=2)+'\n')
print(json.dumps({'modules':len(index),'buffer_instances':len(proofs),'proved_bit_paths':sum(proofs.values())}))
