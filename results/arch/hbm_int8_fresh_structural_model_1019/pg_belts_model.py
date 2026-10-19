import json,gzip,hashlib,math,csv,os,collections,re,resource
from pathlib import Path
P=Path('input');O=Path('pg_output');O.mkdir(exist_ok=True)
x=json.load(gzip.open(P/'metal.json.gz','rt')); U=x['units']; assert U==1000
# Adaptation of canonical HIDX projection method, geometry/native track grid
# only. No HIDX PG shapes, source placement, clocks or phase are inherited.
low,high=2160,235440
def positions(offset,pitch,lo,hi):
 return list(range(offset+math.ceil((lo-offset)/pitch)*pitch,hi,pitch))
native_tracks={'M2':sorted(set(t for o in [45,81,117,153,189,225,270] for t in positions(o,270,2160,127440))),
 'M3':positions(9,36,2160,235440),'M4':positions(12,48,2160,127440),'M5':positions(12,48,2160,235440)}
# Same-layer conservative isotropic separation: half signal extent + maximum
# applicable min/wide/EOL/end-to-end/corner envelope from this tech LEF.
# M4/5 wide PG requires72nm; EOL/corner max48nm, therefore72nm dominates.
# M2/3 EOL/end-to-end31nm dominates18nm min and20nm corner.
margin={'M2':40,'M3':40,'M4':84,'M5':84}
via_margin={'M2':45,'M3':48,'M4':95,'M5':95}
regions={'south_belt':(30780,55620),'band':(55620,73980),'north_belt':(73980,98820),'all':(2160,127440)}
pg=[s for s in x['shapes'] if s[2] in ('POWER','GROUND')]
stats=collections.Counter((s[0],s[2]) for s in pg)
ledgers=[];summary={}
for layer in ['M2','M3','M4','M5']:
 horizontal=layer in ['M2','M4']; axis=1 if horizontal else 0; other=0 if horizontal else 1
 shapes=[s for s in pg if s[0]==layer]
 for policy,mg in [('wire',margin[layer]),('via_landing',via_margin[layer])]:
  for region,(rlo,rhi) in regions.items():
   # H: y region and x fullcore. V: x fullcore and y region.
   rtracks=[t for t in native_tracks[layer] if (rlo<=t<rhi if horizontal else True)]
   spanlo,spanhi=(low,high) if horizontal else (rlo,rhi)
   intervals=[];roles=collections.Counter(); origins=collections.Counter()
   cut_layers={'M2':['V1','V2'],'M3':['V2','V3'],'M4':['V3','V4'],'M5':['V4']}[layer]
   considered=shapes+([s for s in pg if s[0] in cut_layers] if policy=='via_landing' else [])
   for lay,rect,role,origin in considered:
    mg_actual=mg if lay==layer else 46
    if rect[other]-mg_actual <=spanhi and rect[other+2]+mg_actual>=spanlo:
     a,b=rect[axis]-mg_actual,rect[axis+2]+mg_actual
     intervals.append((a,b));roles[role]+=1;origins[origin.split(':')[0]]+=1
   intervals.sort(); merged=[]
   for a,b in intervals:
    if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
    else:merged.append([a,b])
   j=0;free=[]
   for t in rtracks:
    while j<len(merged) and merged[j][1]<t:j+=1
    blocked=j<len(merged) and merged[j][0]<=t<=merged[j][1]
    ledgers.append([layer,policy,region,t,int(not blocked)])
    if not blocked:free.append(t)
   summary[f'{layer}:{policy}:{region}']={'gross':len(rtracks),'pg_clear':len(free),'blocked':len(rtracks)-len(free),'clear_track_nm':free,'obstacle_rectangles_considered':len(intervals),'roles':dict(roles),'origins':dict(origins),'margin_nm':mg,'span_nm':[spanlo,spanhi]}
res={'status':'SOURCE_MODEL_ONLY_NOT_ROUTED','units':1000,'native_make_tracks':True,'core_nm':[2160,2160,235440,127440],'band_nm':[55620,73980],'pg_shapes':len(pg),'shape_inventory':{f'{a}:{b}':c for (a,b),c in stats.items()},'all_input_shapes':len(x['shapes']),'input_vias':len(x['vias']),'native_pg_pin_entries':len(x['pins']),'summary':summary,'maxrss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'qualifications':{'clock_track_reserve':None,'new_cell_PG_contacts':None,'signal_signal_vias':None,'actual_DRC':None,'fresh_PG_contact_PASS':False,'capacity_PASS':False},'baseline_policy':'Retain immutable original PG shapes as obstacles; new cell contacts may add obstacles. No old terminal contact qualification transfers.'}
res['hashes']={f:hashlib.sha256((P/f).read_bytes()).hexdigest() for f in ['metal.json.gz','tech.lef','cells.lef','setRC.tcl']}
json.dump(res,open(O/'ledger.json','w'),indent=2)
with open(O/'tracks.csv','w') as f:
 w=csv.writer(f);w.writerow(['layer','envelope','region','coordinate_nm','pg_clear']);w.writerows(ledgers)
for k,v in summary.items():print(k,v['gross'],v['pg_clear'],v['blocked'])
print('MAXRSS_KB',res['maxrss_kb'])
