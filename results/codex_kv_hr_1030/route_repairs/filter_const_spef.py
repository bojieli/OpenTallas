from pathlib import Path
import re,sys,json
src,names,out=map(Path,sys.argv[1:]);skip={n.replace('\\','') for n in names.read_text().splitlines()};text=src.read_text();head,body=text.split('*D_NET',1);nm={}
for l in head.splitlines():
 m=re.match(r'^(\*\d+)\s+(\S+)$',l)
 if m:nm[m[1]]=m[2].replace('\\','')
kept=[];removed=[]
for b in ('*D_NET'+body).split('*D_NET')[1:]:
 key=b.split()[0];name=nm.get(key,key).replace('\\','')
 if name in skip:removed.append(name)
 else:kept.append(b)
assert set(removed)==skip,(len(removed),len(skip),list(skip-set(removed))[:5])
out.write_text(head+''.join('*D_NET'+b for b in kept));print('CONST_SPEF_FILTER',json.dumps({'skipped_old_constant_nets':len(removed),'kept_old_routed_nets':len(kept)}))
