#!/usr/bin/env python3
"""Select exact physical SRAM synthesis interfaces after checking them against selected functional ports."""
import hashlib,json,re,shutil,sys
from pathlib import Path
src,dst,tools=map(Path,sys.argv[1:4]);assert not dst.exists(),dst
def parse_ports(text,name):
 text=re.sub(r"//[^\n]*", "", text)
 m=re.search(r"\bmodule\s+"+re.escape(name)+r"\b(.*?)\);",text,re.S)
 assert m,'Missing module '+name
 out={}
 for direction,width,pin in re.findall(r"\b(input|output|inout)\s+(?:(?:wire|reg|logic)\s+)?(\[[^]]+\]\s*)?([A-Za-z_][A-Za-z_0-9]*)",m.group(1)):
  assert pin not in out,('Duplicate port',name,pin)
  out[pin]=(direction,re.sub(r"\s+","",width))
 return out
shutil.copytree(src/'rtl',dst/'rtl');shutil.copyfile(src/'sources.f',dst/'sources.f');d=json.load(open(src/'sources.json'));changes=[]
for name,m in d['macros'].items():
 model=Path(m['source']);bb=model.parent/(name+'_bb.v');assert bb.is_file(),bb
 mp=parse_ports(model.read_text(),name);bp=parse_ports(bb.read_text(),name)
 assert mp and bp and mp==bp,'Physical interface mismatch: '+name
 rows=[r for r in d['files'] if r['path']==str(model)];assert len(rows)==1,(name,rows)
 r=rows[0];f=dst/r['snapshot'];f.write_bytes(bb.read_bytes());r['sha256']=hashlib.sha256(f.read_bytes()).hexdigest();r['bytes']=f.stat().st_size
 changes.append(dict(module=name,selected_functional_model=str(model),physical_synthesis_interface=str(bb),interface_sha256=r['sha256'],ports='EXACT_MATCH',actual_lef=m['lef'],actual_tt_liberty=m['liberty_tt']))
d['physical_synthesis_interfaces']=changes;(dst/'sources.json').write_text(json.dumps(d,indent=1)+'\n');print(json.dumps(dict(interfaces=len(changes),models=[r['module'] for r in changes],port_match=True)))
