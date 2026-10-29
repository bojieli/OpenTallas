#!/usr/bin/env python3
"""Align wide EW bank FT windows by translating complete abutment window stacks.
No outline, payload width, bus order or register is removed. Bounded weighted
potential constraints favor the widest flows; exact PG-clear track supply is
rechecked after translation. All affected FT sites are invalidated. Failed
constraints stay visible. Input/output are candidate geometry, never P&R.
"""
import argparse,collections,copy,json,math,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('geometry');ap.add_argument('out');ap.add_argument('--tools',required=True);a=ap.parse_args();sys.path.insert(0,a.tools);import schema as S
src=Path(a.geometry);out=Path(a.out);out.mkdir(parents=True,exist_ok=False);P=json.loads((src/'die_plan.json').read_text());R=json.loads((src/'report.json').read_text());m=S.Plan(P);parts=m.parts;edges=collections.defaultdict(list);locations={}
for pr in P['ports']:
 s,d=pr['src']['part'],pr['dst']['part']
 if s not in parts or d not in parts:continue
 if pr['face'] not in 'EW':continue
 edge=tuple(sorted((s,d)));edges[edge].append(pr)
 for side in ('src','dst'):locations[pr[side]['part'],pr[side]['bus']]=(edge,sum(pr['window_um'])/2)
upper={}
for e,ps in edges.items():
 A,B=m.rect(e[0]),m.rect(e[1]);hi=min(A[3],B[3]);upper[e]=max(0.,hi-.08-max(p['window_um'][1] for p in ps))
# Component potentials d(edge)=component_shift + relative(edge), with legal
# component interval obtained from every edge's remaining physical face space.
par={e:e for e in edges};pot={e:0. for e in edges};bounds={e:(0.,upper[e]) for e in edges}
def root(e):
 if par[e]!=e:
  q=par[e];r,v=root(q);pot[e]+=v;par[e]=r
 return par[e],pot[e]
constraints=[]
for pn,pr in parts.items():
 if '_b' not in pn:continue
 for sl in m.ptype(pn).get('ft_slots',[]):
  if sl['width']<1000 or {sl['in_face'],sl['out_face']}!={'E','W'}:continue
  aa=locations.get((pn,sl['name']+'_i'));bb=locations.get((pn,sl['name']+'_o'))
  if not aa or not bb or aa[0]==bb[0]:continue
  constraints.append((-(sl['width']+1),pn,sl['name'],aa,bb))
choices=[]
for _,pn,sn,(u,cu),(v,cv) in sorted(constraints):
 ru,pu=root(u);rv,pv=root(v);c=cu-cv;needed=c+pu-pv
 if ru==rv:
  choices.append(dict(part=pn,slot=sn,accepted=abs((pv-pu)-c)<1e-5,reason='existing potential cycle',residual_um=round((pv-pu)-c,6)));continue
 # Attach rv to ru: component(rv)=component(ru)+needed.
 lu,hu=bounds[ru];lv,hv=bounds[rv];low,high=max(lu,lv-needed),min(hu,hv-needed)
 accepted=low<=high+1e-7
 choices.append(dict(part=pn,slot=sn,accepted=accepted,old_offset_um=round(cv-cu,6),reason='bounded interface alignment' if accepted else 'insufficient free edge translation range'))
 if accepted:par[rv]=ru;pot[rv]=needed;bounds[ru]=(low,high)
components=collections.defaultdict(list)
for e in edges:r,p=root(e);components[r].append((e,p))
shifts={};phase_fail=[]
def legal_delta(e,delta):
 for pr in edges[e]:
  lo,hi=(x+delta for x in pr['window_um']);n=S.port_pins_count(pr);nl=len(pr['layers'])
  if any(S.usable_tracks(m.layers[ln],ln,lo,hi)*.6+1e-8<len(range(i,n,nl)) for i,ln in enumerate(pr['layers'])):return False
 return True
for r,rows in components.items():
 low,high=bounds[r];candidate=low;found=None
 # Physical PG repeats every 8.64um. Search this phase interval in 16nm steps;
 # this is a technology phase search, not a timing/resource deadline.
 while candidate<=min(high,low+8.64)+1e-7:
  if all(legal_delta(e,candidate+p) for e,p in rows):found=candidate;break
  candidate+=.016
 if found is None:
  phase_fail.append(dict(edges=[list(e) for e,_ in rows],reason='no jointly legal PG-clear pin-window phase'));continue
 for e,p in rows:shifts[e]=round(found+p,6)
if phase_fail:raise RuntimeError('aligned component has no physical PG phase: '+str(phase_fail))
changed=set()
for e,delta in shifts.items():
 if abs(delta)<1e-7:continue
 for pr in edges[e]:
  pr['window_um']=[round(x+delta,6) for x in pr['window_um']]
  for side in ('src','dst'):
   ep=pr[side];pn=ep['part'];t=m.ptype(pn);df=pr['face'] if side=='src' else S.OPP[pr['face']];tf=m.type_face(pn,df);lo,hi=[x-parts[pn]['origin_um'][1] for x in pr['window_um']];order=pr.get('order','lsb_low')
   if m.orient(pn) in ('MX','R180'):lo,hi=t['outline_um'][1]-hi,t['outline_um'][1]-lo;order='lsb_high' if order=='lsb_low' else 'lsb_low'
   b=next((b for b in t.get('buses',[]) if b['name']==ep['bus']),None)
   if b is not None:b.update(window_um=[round(lo,6),round(hi,6)],order=order)
   else:
    sl=next(s for s in t['ft_slots'] if ep['bus'] in (s['name']+'_i',s['name']+'_o'));stem='in' if ep['bus'].endswith('_i') else 'out';sl[stem+'_window_um']=[round(lo,6),round(hi,6)];sl[stem+'_order']=order
    for k in ('bit_sites_um','bit_site_cell_um','regs_um'):sl.pop(k,None)
   changed.add(pn);R['changed_types'][pn]['buses']=sorted(set(R['changed_types'][pn]['buses'])|{ep['bus']})
R['window_alignment']=dict(constraints=choices,edge_shifts=[dict(parts=list(e),delta_um=v) for e,v in shifts.items() if abs(v)>1e-7],parts=sorted(changed),note='Actual technology PG track supply checked after each translated window; no pin-density/capacity relaxation')
R['status']='GEOMETRY_CANDIDATE_ALIGNED_BANK_WINDOWS';(out/'die_plan.json').write_text(json.dumps(P,separators=(',',':'))+'\n');(out/'report.json').write_text(json.dumps(R,indent=1)+'\n');print('ALIGNED',len(changed),'parts',sum(x['accepted'] for x in choices),'of',len(choices),'constraints')
