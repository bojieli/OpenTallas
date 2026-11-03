import csv,json,collections
from pathlib import Path
rows=list(csv.DictReader(open('assignment.tsv'),delimiter='\t'));a=collections.defaultdict(list)
for r in rows:a[r['leaf']].append(r['instance'])
assert len(rows)==42665 and len({r['instance'] for r in rows})==42665 and max(map(len,a.values()))<=42
j=dict(scope='PLANNED_FF_CENTRES_NOT_NATIVE_PIN_REACH_OR_TIMING',ff=len(rows),existing_leaf_count=1024,used_leaves=len(a),empty_leaves=1024-len(a),max_fanout=max(map(len,a.values())),load_histogram=dict(collections.Counter(map(len,a.values()))),max_centre_reach_um=max(float(r['centre_reach_um']) for r in rows),mean_centre_reach_um=sum(float(r['centre_reach_um']) for r in rows)/len(rows),new_ff=0,new_clock_nodes=0,new_cycles=0,clock_depth=7)
Path('leaf_sinks.json').write_text(json.dumps(a,separators=(',',':'))+'\n');Path('summary.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
