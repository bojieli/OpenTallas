import csv,json,collections
from pathlib import Path
rows=list(csv.DictReader(open('assignment.tsv'),delimiter='\t'));points={};leafs={}
for l in open('points.tsv'):
 t,n,x,y=l.split();(points if t=='S' else leafs)[n]=(float(x),float(y))
counts=collections.Counter(r['leaf'] for r in rows);transfers=[]
for leaf in sorted(set(leafs)-set(counts)):
 x,y=leafs[leaf];dist,r=min((abs(points[r['instance']][0]-x)+abs(points[r['instance']][1]-y),r) for r in rows if counts[r['leaf']]>1)
 if dist>32:raise ValueError((leaf,dist,'no same32um transfer'))
 old=r['leaf'];counts[old]-=1;counts[leaf]+=1;r['leaf']=leaf;r['centre_reach_um']=str(dist);transfers.append(dict(instance=r['instance'],old_leaf=old,new_leaf=leaf,centre_reach_um=dist))
assert len(rows)==42665 and len(counts)==1024 and min(counts.values())>=1 and max(counts.values())<=42
with open('assignment_balanced.tsv','w') as f:
 w=csv.DictWriter(f,fieldnames=['instance','leaf','centre_reach_um'],delimiter='\t');w.writeheader();w.writerows(rows)
a=collections.defaultdict(list)
for r in rows:a[r['leaf']].append(r['instance'])
j=dict(scope='PLANNED_FF_CENTRES_NOT_NATIVE_PIN_REACH_OR_TIMING',ff=len(rows),existing_leaf_count=1024,used_leaves=len(a),empty_leaves=0,max_fanout=max(map(len,a.values())),min_fanout=min(map(len,a.values())),load_histogram=dict(collections.Counter(map(len,a.values()))),max_centre_reach_um=max(float(r['centre_reach_um']) for r in rows),mean_centre_reach_um=sum(float(r['centre_reach_um']) for r in rows)/len(rows),new_ff=0,new_clock_nodes=0,new_cycles=0,clock_depth=7,empty_leaf_transfers=transfers)
Path('leaf_sinks_balanced.json').write_text(json.dumps(a,separators=(',',':'))+'\n');Path('summary_balanced.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
