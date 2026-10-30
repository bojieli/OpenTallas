import argparse,json
from pathlib import Path
import odb
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--tree',required=True);p.add_argument('--out',required=True);a=p.parse_args();o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
d=odb.dbDatabase.create();odb.read_db(d,a.source);b=d.getChip().getBlock();D=b.getDbUnitsPerMicron();t=json.load(open(a.tree));moved=[]
for n,xy in t['sites'].items():
 i=b.findInst('ck_'+n)
 if not i:raise ValueError('missing planned native clock cell '+n)
 old=tuple(i.getLocation());new=tuple(round(v*D) for v in xy)
 if old!=new:i.setLocation(*new);moved.append([i.getName(),list(old),list(new)])
# Reuse the already-reviewed exact clock sites, preserving provider and all nets.
odb.write_db(d,str(o/'provider.odb'));json.dump(dict(source=a.source,tree=a.tree,moved=len(moved),moves=moved,clock_cells=len(t['sites'])),open(o/'source_receipt.json','w'))
print('SOURCE_READY clock cells',len(t['sites']),'moved',len(moved),flush=True)
