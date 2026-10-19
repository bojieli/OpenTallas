import sys,pathlib,json,collections,re
p=pathlib.Path('/srv/opentallas-scratch/claude/ref_gate/dsdv_gunit_l5-20261019-121901')
sys.path.insert(0,str(p/'src/tools'));import textbook_lint as T
v=next((p/'routes/gate/work/orfs/results').glob('asap7/*/base/1_2_yosys.v'))
g,top=T.flatten(T.parse_verilog(v.read_text()),'dsdv_gunit_l5')
def key(s):return s.replace('\\','').replace('/','.')
native={};nativePins=collections.Counter()
for line in open('native_pins.tsv'):
 a=line.rstrip('\n').split('\t')
 if a[0]=='CELL':native[key(a[1])]=a[2]
 elif a[0]=='PIN' and (a[4]=='CLOCK' or re.fullmatch(r'(?:CLK|CK|RCLK|WCLK|RD_CLK|WR_CLK)',a[2],re.I)):nativePins[a[1]]+=1
parsed={key(n):m for m,n,p in g.cells}
shared=native.keys()&parsed.keys();onlyn=native.keys()-parsed.keys();onlyp=parsed.keys()-native.keys()
rows=dict(native_count=len(native),parsed_unique_count=len(parsed),parsed_flat_count=len(g.cells),shared=len(shared),native_clocked_instances=len(nativePins),native_only_count=len(onlyn),parsed_only_count=len(onlyp),native_only_by_master=dict(collections.Counter(native[n] for n in onlyn)),parsed_only_by_master=dict(collections.Counter(parsed[n] for n in onlyp)),master_mismatch=[(n,native[n],parsed[n]) for n in shared if native[n]!=parsed[n]],native_only_sample=sorted(onlyn)[:30],parsed_only_sample=sorted(onlyp)[:30],parsed_master_counts=dict(collections.Counter(m for m,n,p in g.cells)),native_master_counts=dict(collections.Counter(native.values())),duplicate_names=len(g.cells)-len(parsed))
json.dump(rows,open('reconcile.json','w'),indent=2)
print(json.dumps({k:v for k,v in rows.items() if k not in ('parsed_master_counts','native_master_counts','master_mismatch')},indent=2))
