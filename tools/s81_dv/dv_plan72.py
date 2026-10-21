#!/usr/bin/env python3
"""Build the owner-selected72-frame physical plan from source inventory and placed envelopes.
Preserve logical instance names/masters, bypass deleted frame-chain members, then route
actual die lanes through macro-free channels. Source/view pin reprojection remains the
existing dv_rvcase responsibility; this planner records its endpoint seeds explicitly.
"""
import argparse,copy,collections,hashlib,json,math,re
from pathlib import Path

def build(base,inventory,packing):
 p=copy.deepcopy(base);old={b['name']:b for b in base['blocks']};inv=inventory['frames']
 assert len(inv)==72 and len({f['name']for f in inv})==72
 placed=packing['best']['blocks'];geo={b['name']:b for b in placed}
 pools={k:sorted([b for b in placed if b['name'].startswith(k)],key=lambda b:(b['x'],b['y']))for k in ('h9_','h10_')}
 oldnames={i:b['name']for i,b in enumerate(base['blocks'])};keepnames={f['name']for f in inv}|{b['name']for b in base['blocks']if b['kind']!='frame'}
 new=[];mapping={}
 for f in sorted(inv,key=lambda f:f['name']):
  b=copy.deepcopy(old[f['name']]);g=pools['h9_'if'h9'in f['master']else'h10_'].pop(0)
  b.update({k:g[k]for k in ('x','y','w','h')});b['master']=f['master'];b['group']=f['group'];new.append(b);mapping[b['name']]=g['name']
 mids=iter(sorted([b for b in base['blocks']if b['kind']=='slice'and not re.match(r's_[07][SN]$',b['name'])],key=lambda b:b['name']))
 slices={b['name']:f'slice_{i:02}'for i,b in enumerate(mids)}
 ends={n:f'end_parent_{i}'for i,n in enumerate(('s_0S','s_0N','s_7S','s_7N'))}
 for b0 in base['blocks']:
  if b0['kind']=='frame':continue
  b=copy.deepcopy(b0);n=b['name']
  if n in slices:k=slices[n]
  elif n in ends:k=ends[n]
  elif n.startswith('rsv_'):k='svc_full_'+str(int(n[-2:]))
  elif n.startswith('irg_'):k='idx_'+n[-2:]
  elif n=='iqf':k='iqf_00'
  elif n=='gunit':k='gunit_00'
  elif n=='bk_sel':k='bk_sel_00'
  elif n=='seqhost':k='seqhost_00'
  elif n=='bk_col':k='bk_col_00'
  elif n.startswith('lk_'):
   side=0 if n[3]=='W'else 1;i=(0 if n[4]=='S'else 2)+int(n[-1]);k=f'link_{side}_{i}'
  else:k=n
  g=geo[k];b.update({v:g[v]for v in ('x','y','w','h')});new.append(b);mapping[n]=k
 by={b['name']:b for b in new};ids={b['name']:i for i,b in enumerate(new)}
 incoming=collections.defaultdict(list)
 for l in base['links']:incoming[(oldnames[l['e'][1][0]],l['c'],l['b'],re.search(r'_l(\d+)$',l['i']).group(1)if re.search(r'_l(\d+)$',l['i'])else'')].append(l)
 links=[];bypass=[]
 def move(e,name):
  ob=old[name];nb=by[name];x,y=e[2:4]
  sides=[(abs(x-ob['x']),'W'),(abs(x-ob['x']-ob['w']),'E'),(abs(y-ob['y']),'S'),(abs(y-ob['y']-ob['h']),'N')];face=min(sides)[1]
  t=min(0.98,max(0.02,(y-ob['y'])/ob['h']if face in'WE'else(x-ob['x'])/ob['w']))
  px=nb['x']+(0 if face=='W'else nb['w']if face=='E'else t*nb['w']);py=nb['y']+(0 if face=='S'else nb['h']if face=='N'else t*nb['h'])
  return [ids[name],e[1],round(px,4),round(py,4),e[4]],face
 for l0 in base['links']:
  dst=oldnames[l0['e'][1][0]]
  if dst not in keepnames:continue
  l=copy.deepcopy(l0);src=oldnames[l['e'][0][0]];seen=[]
  if src not in keepnames and l['c']=='ret':continue
  while src not in keepnames:
   if l['c']!='x_frame':raise ValueError(('removed non-chain source',l['i'],src))
   lane=re.search(r'_l(\d+)$',l['i']).group(1);opts=incoming[(src,l['c'],l['b'],lane)]
   if len(opts)!=1:raise ValueError(('ambiguous bypass',src,lane,len(opts)))
   seen.append(src);l['e'][0]=copy.deepcopy(opts[0]['e'][0]);src=oldnames[l['e'][0][0]]
   if len(seen)>16:raise ValueError('cycle')
  if seen:bypass.append(dict(link=l['i'],removed=seen,source=src,destination=dst))
  e0,f0=move(l['e'][0],src);e1,f1=move(l['e'][1],dst);l['e']=[e0,e1];l['endpoint_faces']=[f0,f1]
  for k in ('sp','h','s','L'):l.pop(k,None)
  links.append(l)
 p['blocks']=new;p['links']=links
 # S81-LINKS gap reserves: geometry-only blockages (no master, no pins, never bound); router + die case obstacles
 p['blockages']=[dict(name=r['name'],kind='reserve',x=r['x'],y=r['y'],w=r['w'],h=r['h'],scope=r.get('scope',''))for r in packing.get('reserves',[])];p['facts'].update(die_um=[32000,25000],die_mm2=800,n_frames=72,rom_slots=660,reticle_margin_um=[500,500],hop_um=405)
 p['facts']['physical72']=dict(owner_adopted=True,inventory_sha=inventory.get('inventory_sha256'),geometry_ref='5678a1aa8',block_mapping=mapping,frame_chain_bypass=bypass,endpoint_geometry='plan face seeds; existing rvcase kit/view pin reprojection required',routing='PENDING',calendar='PENDING currentGU/DENSE2 exact map; no inherited old release ages',end_parent_source='real6739.2slice reassembly required',service_source='current target envelope; parent source/views open')
 return p

def main():
 a=argparse.ArgumentParser();a.add_argument('--base',required=True);a.add_argument('--inventory',required=True);a.add_argument('--packing',required=True);a.add_argument('--out',required=True);v=a.parse_args()
 p=build(*[json.load(open(x))for x in(v.base,v.inventory,v.packing)]);Path(v.out).write_text(json.dumps(p,indent=1));print(json.dumps(dict(blocks=len(p['blocks']),links=len(p['links']),frames=p['facts']['n_frames'],bypasses=len(p['facts']['physical72']['frame_chain_bypass']))))
if __name__=='__main__':main()
