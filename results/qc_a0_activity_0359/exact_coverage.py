import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('activity');p.add_argument('inventory');p.add_argument('out');a=p.parse_args()
A={}
for line in Path(a.activity).read_text().splitlines():
 k,v=line.rsplit(' ',1);A[k.replace(chr(92),'')]=float(v)
hit={};miss=[];other=[]
for row in Path(a.inventory).read_text().splitlines():
 n=row.split(',')[0].rsplit('/',1)[0]
 if chr(36)+'_' not in n:other.append(n);continue
 k=n.partition(chr(36)+'_')[0].replace('/','.').replace(chr(92),'')
 if k in A:hit[k]=A[k]
 else:miss.append(k)
out=Path(a.out);out.mkdir(exist_ok=True)
x=dict(scope='diagnostic correctness-stress activity; not production programme',register_inventory=a.inventory,registers=len(hit)+len(miss),exact_name_matched=len(hit),unmatched=len(miss),nonregister_clocked_instances=other,matched_mean_toggles_per_cycle=sum(hit.values())/max(1,len(hit)),unmatched_names=miss)
(out/'register_coverage.json').write_text(json.dumps(x,indent=2)+'\n');(out/'act_registers_exact.txt').write_text(''.join(k+' '+str(v)+'\n' for k,v in sorted(hit.items())))
print(json.dumps({k:v for k,v in x.items() if k!='unmatched_names'},indent=2))
