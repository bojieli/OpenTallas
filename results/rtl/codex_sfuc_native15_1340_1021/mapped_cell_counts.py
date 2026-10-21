"""Read-only cell inventory of an existing mapped artifact, not synthesis or qualification."""
import argparse, collections, functools, hashlib, importlib.util, json, re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--helper',required=True);p.add_argument('--netlist',required=True);p.add_argument('--top',required=True);p.add_argument('--liberty',action='append',required=True);p.add_argument('--out',required=True);a=p.parse_args()
s=importlib.util.spec_from_file_location('native_census_reader',a.helper);nc=importlib.util.module_from_spec(s);s.loader.exec_module(nc)
roles,receipts=nc.liberty_roles(a.liberty);areas={}
for f in a.liberty:
 text=Path(f).read_text();text=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
 for kind,name,body in nc.groups(text):
  if kind!='library':continue
  for k,n,b in nc.groups(body):
   if k=='cell':
    m=re.search(r'(?m)^\s*area\s*:\s*([0-9.eE+-]+)',b)
    if not m:raise ValueError('missing actual Liberty area '+n)
    areas[n]=float(m.group(1))
mods={};module=None
with open(a.netlist) as f:
 for line in f:
  m=re.match(r'\s*module\s+(\S+)\s*\(',line)
  if m:module=m[1].removeprefix('\\');mods[module]=collections.Counter();continue
  if line.strip()=='endmodule':module=None;continue
  m=re.match(r'\s+(\S+)\s+(\S+)\s*\(\s*$',line)
  if m and module is not None:mods[module][m[1].removeprefix('\\')]+=1
@functools.lru_cache(None)
def inventory(name):
 out=collections.Counter()
 for typ,n in mods[name].items():
  if typ in roles:out[typ]+=n
  elif typ in mods:
   for leaf,count in inventory(typ).items():out[leaf]+=n*count
  else:raise ValueError('unknown mapped cell '+typ)
 return out
counts=inventory(a.top);missing=set(counts)-set(areas)
if missing:raise ValueError('missing actual Liberty areas '+str(missing))
macros={k:n for k,n in counts.items() if k.startswith('ot_sram_')};std={k:n for k,n in counts.items() if k not in macros}
r={'scope':'Read-only existing mapped cell/loaded Liberty inventory; no functional/native/physical qualification implied','top':a.top,'netlist_sha256':hashlib.sha256(Path(a.netlist).read_bytes()).hexdigest(),'liberty':receipts,'cell_counts':dict(sorted(counts.items())),'stdcell_instances':sum(std.values()),'sequential_stdcell_instances':sum(n for k,n in std.items() if roles[k]['sequential']),'SRAM_instances':macros,'stdcell_raw_liberty_area':sum(n*areas[k] for k,n in std.items()),'SRAM_raw_liberty_area':sum(n*areas[k] for k,n in macros.items()),'area_note':'Sum of actual loaded Liberty cell area attributes, reported raw; not normalized layout area or slot-fit evidence'}
Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k not in ('cell_counts','liberty')},indent=2))
