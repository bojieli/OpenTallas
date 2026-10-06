#!/usr/bin/env python3
"""Attribute exact frozen mapped paths through a diagnostic pre-purge alias map.
All nonassign bytes and the complete assign multiset must match the frozen map. No timing or
functional verdict is reproduced here; this reads retained netlist evidence.
"""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--frozen',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--lib-dir',type=Path,required=True);a=p.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(text):
 lines=text.splitlines(True)
 assignments=[line for line in lines if re.match(r'  assign ',line)]
 rest=[line for line in lines if not re.match(r'  assign ',line)]
 return ''.join(rest),sorted(assignments)
assert canonical((a.trace/'mapped.raw.v').read_text())==canonical(a.frozen.read_text()),'Diagnostic cells/attributes/nets/ports/assignments differ: no exact attribution permitted'
raw=(a.trace/'mapped.raw.v').read_text();named=(a.trace/'mapped.named.v').read_text()
def instances(text):
 text=re.search(r'module ot_hbm_native_frame_station\b.*?endmodule',text,re.S).group(0)
 return [(m.group(1),m.group(2).lstrip('\\')) for m in re.finditer(r'^  (\S+)[ \t]+(\S+)[ \t]+\(',text,re.M)]
x,y=instances(raw),instances(named);assert len(x)==len(y)
assert [v[0] for v in x]==[v[0] for v in y]
renames={v[1]:w[1] for v,w in zip(x,y)}
pre=json.loads((a.trace/'before_purge.json').read_text())['modules']['ot_hbm_native_frame_station']
post=json.loads((a.trace/'after_purge.json').read_text())['modules']['ot_hbm_native_frame_station']
assert set(renames.values()) <= set(post['cells'])
aliases={}
for name,n in pre['netnames'].items():
 if n.get('hide_name'):continue
 for i,bit in enumerate(n['bits']):
  if isinstance(bit,int):aliases.setdefault(bit,[]).append(name+(f'[{i+n.get("offset",0)}]' if len(n['bits'])>1 else ''))
def cell(name):
 orig=renames[name];c=pre['cells'][orig]
 return dict(mapped=name,original=orig,type=c['type'],attributes=c.get('attributes',{}),ports={pin:dict(bits=bits,aliases=[aliases.get(b,[]) for b in bits]) for pin,bits in c['connections'].items()})
rpt=a.report.read_text()
paths=[]
for section in re.split(r'(?m)(?=^Startpoint:)',rpt):
 start=re.search(r'^Startpoint: (_\d+_).*?Endpoint: (_\d+_)',section,re.S)
 slack=re.search(r'(-?\d+(?:\.\d+)?)\s+slack \(VIOLATED\)',section)
 if start and slack:paths.append((float(slack.group(1)),section,start))
assert paths,'No violated mapped reg-to-reg path in retained report'
_,path,start=min(paths,key=lambda v:v[0]);nodes=list(dict.fromkeys(re.findall(r'(_\d+_)/\w+',path)))
records=[cell(n) for n in nodes if n in renames]
directions={};lib_hashes={}
for lib in sorted(a.lib_dir.glob('*RVT_TT*.lib')):
 lib_hashes[str(lib)]=sha(lib)
 for match in re.finditer(r'cell\s*\(\s*([^\s)]+)\s*\)\s*\{(.*?)(?=\bcell\s*\(|\Z)',lib.read_text(),re.S):
  directions[match[1].strip('"')]={pin:direction for pin,direction in re.findall(r'\bpin\s*\(\s*([^\s)]+)\s*\)\s*\{(?:(?!\bpin\s*\().)*?direction\s*:\s*(input|output)',match[2],re.S)}
for name,module in json.loads((a.trace/'before_purge.json').read_text())['modules'].items():
 directions[name]={pin:port['direction'] for pin,port in module.get('ports',{}).items()}
for c in pre['cells'].values():
 c['port_directions']=directions[c['type']] if c['connections'] else {}
 assert set(c['connections']) <= set(c['port_directions']),('Unknown library pin',c['type'])
fanout={}
for c in pre['cells'].values():
 for pin,bits in c['connections'].items():
  if c['port_directions'].get(pin)=='input':
   for bit in bits:
    if isinstance(bit,int):fanout[bit]=fanout.get(bit,0)+1
inversions={}
for name,c in pre['cells'].items():
 if not c['type'].startswith('INV'):continue
 ins=[bits[0] for pin,bits in c['connections'].items() if c['port_directions'].get(pin)=='input' and len(bits)==1]
 outs=[bits[0] for pin,bits in c['connections'].items() if c['port_directions'].get(pin)=='output' and len(bits)==1]
 if len(ins)==len(outs)==1:inversions.setdefault(ins[0],[]).append(dict(cell=name,aliases=aliases.get(outs[0],[])))
for record in records:
 for pin,port in record['ports'].items():
  port['mapped_sink_pin_count']=[fanout.get(b,0) for b in port['bits']]
  port['one_inversion_aliases']=[inversions.get(b,[]) for b in port['bits']]
result=dict(status='EXACT_FROZEN_MAP_SOURCE_ATTRIBUTION',mapping_identity=dict(all_nonassign_bytes_equal=True,complete_assign_multiset_equal=True,assign_count=len(canonical(raw)[1]),raw_bytes_equal=sha(a.trace/'mapped.raw.v')==sha(a.frozen),difference='write_json changes only order of complete identical assign statements; all cell/nets/ports/attributes nonassign bytes match'),frozen_sha256=sha(a.frozen),diagnostic_sha256=sha(a.trace/'mapped.raw.v'),before_purge_sha256=sha(a.trace/'before_purge.json'),after_purge_sha256=sha(a.trace/'after_purge.json'),report_sha256=sha(a.report),pin_direction_libraries_sha256=lib_hashes,startpoint=next(r for r in records if r['mapped']==start.group(1)),endpoint=next(r for r in records if r['mapped']==start.group(2)),path_nodes=records,limits='Mapped sink counts are pre-placement connectivity; actual path report fanout includes placed buffers. Source attribution is not a new functional/timing qualification.')
a.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','frozen_sha256','startpoint','endpoint']}))
