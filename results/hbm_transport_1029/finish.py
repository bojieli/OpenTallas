#!/usr/bin/env python3
"""Make typed metadata agree with already allocated canonical die-frame pins.
Does not move, renumber or reallocate a physical bit/site. Rehashes the complete
physical type identity after descriptor normalization. Fail-closed on any shared
hardened type whose copies would require different physical bus contracts.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('allocated');ap.add_argument('out');ap.add_argument('--tools',required=True);a=ap.parse_args();sys.path.insert(0,a.tools);import schema as S
src=Path(a.allocated);out=Path(a.out);out.mkdir(parents=True,exist_ok=False);P=json.loads((src/'die_plan.json').read_text());R=json.loads((src/'report.json').read_text());m=S.Plan(P);contracts={};fixes=[]
try:
 if R['status'] not in ('ACTUAL_FT_SITES_ALLOCATED_PENDING_CURRENT_SOURCE_BITMAP_AND_G0_G1','ACTUAL_FT_SITES_ALLOCATED_PENDING_G0_G1'):
  raise RuntimeError('input is not a complete allocated candidate')
 for pr in P['ports']:
  for side in ('src','dst'):
   ep=pr[side];pn=ep['part']
   if pn not in R['changed_types']:continue
   tn=m.parts[pn]['type'];t=m.types[tn];df=pr['face'] if side=='src' else S.OPP[pr['face']];tf=m.type_face(pn,df);axis=1 if tf in 'EW' else 0;lo,hi=pr['window_um'];base=m.parts[pn]['origin_um'][axis];lo-=base;hi-=base;order=pr.get('order','lsb_low');ori=m.orient(pn)
   if ori in (('MX','R180') if tf in 'EW' else ('MY','R180')):lo,hi=t['outline_um'][axis]-hi,t['outline_um'][axis]-lo;order='lsb_high' if order=='lsb_low' else 'lsb_low'
   con=dict(face=tf,window_um=[round(lo,6),round(hi,6)],layers=pr['layers'],order=order,width=pr['width']);key=(tn,ep['bus'])
   if key in contracts and contracts[key]!=con:raise RuntimeError(f'shared type incompatible contracts {tn}/{ep["bus"]}')
   contracts[key]=con;b=next((b for b in t.get('buses',[]) if b['name']==ep['bus']),None)
   if b is not None:
    if any(b.get(k)!=v for k,v in con.items()):fixes.append(dict(part=pn,bus=ep['bus'],old_order=b.get('order'),new_order=order));b.update(con)
   else:
    sl=next((s for s in t.get('ft_slots',[]) if ep['bus'] in (s['name']+'_i',s['name']+'_o')),None)
    if sl is None:raise RuntimeError(f'missing declared bus {tn}/{ep["bus"]}')
    stem='in' if ep['bus'].endswith('_i') else 'out'
    if sl.get(stem+'_order')!=order:fixes.append(dict(part=pn,bus=ep['bus'],old_order=sl.get(stem+'_order'),new_order=order))
    for k,v in con.items():sl[k if k=='width' else stem+'_'+k]=v
 renamed={}
 for pn,info in R['changed_types'].items():
  tn=m.parts[pn]['type'];t=m.types[tn];identity=copy.deepcopy(t);identity.pop('module',None);identity.pop('note',None);digest=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:10];nn=info['old']+'__tr_'+digest;nt=copy.deepcopy(t);nt['module']='hbm_arch_'+nn
  if nn in P['partition_types'] and P['partition_types'][nn]!=nt:raise RuntimeError('interface hash collision')
  P['partition_types'][nn]=nt;m.parts[pn]['type']=nn;info['new']=nn;renamed[tn]=nn
 used={p['type'] for p in P['partitions']}
 for tn in renamed:
  if tn not in used:P['partition_types'].pop(tn,None)
 R['typed_metadata_normalization']=dict(changed=len(fixes),entries=fixes,physical_sites_changed=False);(out/'die_plan.json').write_text(json.dumps(P,separators=(',',':'))+'\n');R['status']='ACTUAL_FT_SITES_AND_TYPED_PINS_PENDING_G0_G1'
except Exception as e:R['status']='FAIL';R['failures'].append(f'{type(e).__name__}: {e}');raise
finally:(out/'report.json').write_text(json.dumps(R,indent=1)+'\n')
