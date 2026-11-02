from pathlib import Path
import json,collections
P=Path('/home/ubuntu/coord/tmp/codex-hist-anchor-2100');C=json.load(open(P/'fresh_fp_pre_constraints.json'));T=json.load(open(P/'physical_prep/allFF_target_recipe.json'))['targets'];rows=collections.defaultdict(list);fixedrow=collections.defaultdict(list)
for r in C['rows']:rows[r['bbox_dbu'][1]].append(r)
for f in C['fixed']:
 b=f['bbox_dbu'];h=4320 if f['master'].startswith(('ot_sram','ot_s81ph_native_sel_hist_bank'))else 0
 for y in rows:
  if y<b[3]+h and y+270>b[1]-h:fixedrow[y].append((b[0]-h,b[2]+h,f))
errors=[]
for t in T:
 x,y=[round(v*1000)for v in t['origin_um']];w,h=[round(v*1000)for v in t['size_um']];rr=[r for r in rows[y]if r['bbox_dbu'][0]<=x and x+w<=r['bbox_dbu'][2]and(x-r['origin'][0])%r['site_width']==0 and t['row_orient']==r['orient']];hits=[f for a,b,f in fixedrow[y]if x<b and x+w>a]
 if len(rr)!=1 or hits:errors.append(dict(name=t['name'],fixed_face=t['fixed_face'],row_legal=len(rr)==1,hits=[dict(name=f['name'],master=f['master'],bbox_dbu=f['bbox_dbu'])for f in hits]))
a=dict(FF=len(T),errors=len(errors),fixed_face_errors=sum(e['fixed_face']for e in errors),row_errors=sum(not e['row_legal']for e in errors),hits=errors);(P/'fresh_target_audit.json').write_text(json.dumps(a,indent=1));print({k:v for k,v in a.items()if k!='hits'});print(collections.Counter(h['master']for e in errors for h in e['hits']))
