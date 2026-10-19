import json,gzip,hashlib,math,csv,os,collections,re,resource
from pathlib import Path
P=Path('input');O=Path('output');O.mkdir(exist_ok=True)
x=json.load(gzip.open(P/'metal.json.gz','rt')); U=x['units']; assert U==1000
# Every track remains exactly 24+48*k nm. No native finer pitch substitution.
tracks=list(range(2184,138240,48)); low,high=2160,138240
# Same-layer conservative isotropic separation: half signal extent + maximum
# applicable min/wide/EOL/end-to-end/corner envelope from this tech LEF.
# M4/5 wide PG requires72nm; EOL/corner max48nm, therefore72nm dominates.
# M2/3 EOL/end-to-end31nm dominates18nm min and20nm corner.
margin={'M2':40,'M3':40,'M4':84,'M5':84}
via_margin={'M2':45,'M3':48,'M4':95,'M5':95}
regions={'south':(2160,56160),'band':(56160,84240),'north':(84240,138240),'all':(2160,138240)}
pg=[s for s in x['shapes'] if s[2] in ('POWER','GROUND')]
stats=collections.Counter((s[0],s[2]) for s in pg)
ledgers=[];summary={}
for layer in ['M2','M3','M4','M5']:
 horizontal=layer in ['M2','M4']; axis=1 if horizontal else 0; other=0 if horizontal else 1
 shapes=[s for s in pg if s[0]==layer]
 for policy,mg in [('wire',margin[layer]),('via_landing',via_margin[layer])]:
  for region,(rlo,rhi) in regions.items():
   # H: y region and x fullcore. V: x fullcore and y region.
   rtracks=[t for t in tracks if (rlo<=t<rhi if horizontal else True)]
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
res={'status':'SOURCE_MODEL_ONLY_NOT_ROUTED','units':1000,'track_offset_nm':24,'track_pitch_nm':48,'core_nm':[2160,2160,138240,138240],'band_nm':[56160,84240],'pg_shapes':len(pg),'shape_inventory':{f'{a}:{b}':c for (a,b),c in stats.items()},'all_input_shapes':len(x['shapes']),'input_vias':len(x['vias']),'native_pg_pin_entries':len(x['pins']),'summary':summary,'maxrss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
res['hashes']={f:hashlib.sha256((P/f).read_bytes()).hexdigest() for f in ['metal.json.gz','native_pin_geometry.json.gz','tech.lef','cells.lef','setRC.tcl']}
json.dump(res,open(O/'ledger.json','w'),indent=2)
with open(O/'tracks.csv','w') as f:
 w=csv.writer(f);w.writerow(['layer','envelope','region','coordinate_nm','pg_clear']);w.writerows(ledgers)
for k,v in summary.items():print(k,v['gross'],v['pg_clear'],v['blocked'])
print('MAXRSS_KB',res['maxrss_kb'])
