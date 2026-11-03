from pathlib import Path
from collections import defaultdict,Counter
import json,sys
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/home/ubuntu/coord/tmp/codex-hbm-bfqg-compact-kit-1101/corrected_guide_place/geom.tsv');E=json.load(open('/home/ubuntu/coord/tmp/codex-bfqg-cut-export-0315/collected/guide_pins.json'));proxy=json.load(open(P/'cut_proxy.json'));Y=107.5;L,R=10,17
clean=lambda s:s.replace(chr(92),'')
def ekey(n):return tuple(sorted(set(t['instance_id']for t in n['terms']))),tuple(sorted(clean(t['name'])for t in n['ports']))
def dkey(i):
 sig,dr,sk=D.nets[i];ep=([dr]if dr else[])+sk
 return tuple(sorted(set(e[1]for e in ep if e[0]=='i'))),tuple(sorted(clean(D.pin_by_k[e[1]]['name'])for e in ep if e[0]=='p'))
lookup=defaultdict(list)
for n in E['nets']:lookup[ekey(n)].append(n)
rows=[];fail=[]
for r in proxy['contributions']:
 cand=lookup[dkey(r['net_index'])]
 if len(cand)!=1:fail.append({'net_index':r['net_index'],'matches':len(cand)});continue
 n=cand[0];cross=[q for q in n['guides']if q['box_um'][1]<Y<q['box_um'][3]];inside=[q for q in cross if q['box_um'][0]<R and q['box_um'][2]>L];outside=[q for q in cross if q['box_um'][0]<L or q['box_um'][2]>R]
 over=[]
 for q in cross:
  for m in E['macros']:
   x0,y0,x1,y1=m['box_um']
   if y0<Y<y1 and q['box_um'][0]<x1 and q['box_um'][2]>x0:over.append({'guide':q,'macro':m['instance']})
 pts=[]
 for t in n['terms']:
  if t['macro']:
   for q in t['actual_macro_pin_shapes']:
    x0,y0,x1,y1=q['box_um'];pts.append(((x0+x1)/2,(y0+y1)/2))
  else:pts.append(t['proxy_cell_centre_um'])
 for t in n['ports']:
  for q in t['shapes']:
   x0,y0,x1,y1=q['box_um'];pts.append(((x0+x1)/2,(y0+y1)/2))
 truecross=min(p[1]for p in pts)<Y<max(p[1]for p in pts)
 rows.append(dict(net_index=r['net_index'],name=n['name'],proxy_weight=r['hot_window_weight'],proxy_box=r['box'],unit_weight=r['hot_window_weight']>0.999999,actual_endpoint_crosses_cut=truecross,native_cut_guides=cross,native_inside_hot=inside,native_outside_hot=outside,native_over_macro=over,endpoint_terms=n['terms'],ports=n['ports']))
units=[r for r in rows if r['unit_weight']];allcross=[q for n in E['nets']for q in n['guides']if q['box_um'][1]<Y<q['box_um'][3]]
res=dict(scope='Actual saved native guide+truepin join to exact hot proxy contributors; guides are corridors not detailed wires/access/DRC',source_sha=E['source_odb_sha256'],proxy_contributors=len(proxy['contributions']),joined=len(rows),unresolved=fail,unit_weight_nets=len(units),unit_nets_any_native_cut_guide=sum(bool(r['native_cut_guides'])for r in units),unit_nets_any_guide_outside_hot=sum(bool(r['native_outside_hot'])for r in units),unit_nets_only_outside_hot=sum(bool(r['native_cut_guides'])and not r['native_inside_hot']for r in units),unit_nets_any_guide_over_macro=sum(bool(r['native_over_macro'])for r in units),unit_native_cut_guide_layers=dict(Counter(q['layer']for r in units for q in r['native_cut_guides'])),unit_over_macro_layers=dict(Counter(z['guide']['layer']for r in units for z in r['native_over_macro'])),all_native_cut_guide_layers=dict(Counter(q['layer']for q in allcross)),true_endpoint_crossing_contributors=sum(r['actual_endpoint_crosses_cut']for r in rows),rows=rows)
(P/'native_join.json').write_text(json.dumps(res,indent=1)+'\n');print({k:v for k,v in res.items()if k not in['rows']})
