from pathlib import Path
import re,sys,json
src,names,out=map(Path,sys.argv[1:]);keep={n.replace('\\','') for n in names.read_text().splitlines()};text=src.read_text();head,body=text.split('*D_NET',1);nm={}
for l in head.splitlines():
 m=re.match(r'^(\*\d+)\s+(\S+)$',l)
 if m:nm[m[1]]=m[2].replace('\\','')
selected=[];seen=set()
for b in ('*D_NET'+body).split('*D_NET')[1:]:
 key=b.split()[0];name=nm.get(key,key).replace('\\','')
 if name in keep:selected.append(b);seen.add(name)
assert seen==keep,(len(seen),len(keep),list(keep-seen)[:5])
out.write_text(head+''.join('*D_NET'+b for b in selected));print('CLOCK_SPEF_SELECT',len(seen))
