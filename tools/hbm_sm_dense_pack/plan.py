#!/usr/bin/env python3
"""Source-based dense compute packing feasibility; never claims hardleaf closure."""
import argparse, pathlib, re, json, hashlib, collections
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();root=pathlib.Path(a.source)
kits={'xs':'smh_xs_ref_p45m','bdc':'smh_bdc_ref_p50','tcl':'smh_tcl_ref_p45','tct':'smh_tct_ref_p45'}
models={}
for kind,kit in kits.items():
 path=next((root/'physical/ref_tile'/kit/'views').glob('*/*.lef'));t=path.read_text();w,h=map(float,re.search(r'SIZE (\S+) BY (\S+)',t).groups()); pins={};obs=collections.Counter()
 for name,body in re.findall(r'  PIN (\S+)\n(.*?)  END \S+\n',t,re.S):
  m=re.search(r'RECT\s+(\S+) (\S+) (\S+) (\S+)',body)
  if not m:continue
  x0,y0,x1,y1=map(float,m.groups());x=(x0+x1)/2;y=(y0+y1)/2
  face=min([('W',x),('E',w-x),('S',y),('N',h-y)],key=lambda v:v[1])[0]
  pins[name]={'x':x,'y':y,'face':face,'layer':re.search(r'LAYER (\S+)',body)[1]}
 layer=None
 for line in t.split('  OBS')[1].splitlines():
  if 'LAYER ' in line:layer=line.split()[1]
  if 'RECT ' in line:obs[layer]+=1
 models[kind]={'source':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'w':w,'h':h,'pin_census':dict(collections.Counter(q['face']+':'+q['layer'] for q in pins.values())),'obstruction_rects':dict(obs),'pins':pins}
# All10 are actual unchanged LEFs. Only R0. Closed masters' abstract dimensions, no 43.2um origin lattice required.
W,H=693.44,501.92;blocks=[]
for lf,x in enumerate([10,356.72]):
 for kind,name,dx,y in [('xs','xs',0,102),('bdc','bdc',0,279.68),('tct','tct',132.32,279.68),('tcl','tcl0',132.32,370.96),('tcl','tcl1',238.72,370.96)]:
  m=models[kind]; blocks.append(dict(name=f'leaf{lf}_{name}',kind=kind,x=x+dx,y=y,w=m['w'],h=m['h'],orient='R0'))
violations=[];mingap=1e9
for i,b in enumerate(blocks):
 assert b['x']>=0 and b['y']>=0 and b['x']+b['w']<=W+.0001 and b['y']+b['h']<=H+.0001
 for c in blocks[:i]:
  dx=max(c['x']-b['x']-b['w'],b['x']-c['x']-c['w']);dy=max(c['y']-b['y']-b['h'],b['y']-c['y']-c['h']);gap=max(dx,dy)
  mingap=min(mingap,gap)
  if gap<20-.0001:violations.append([b['name'],c['name'],gap])
assert not violations
rowbits,beatbits=1636,2069
out={'verdict':'DENSE_COMPUTE_PACK_PASS_TRANSPORT_UNQUALIFIED','source_root':str(root),'tile':{'width_um':W,'height_um':H,'area_um2':W*H,'replicas':32,'aggregate_mm2':W*H*32/1e6},'compute_children':blocks,'min_child_gap_um':mingap,'compute_area_um2':sum(b['w']*b['h'] for b in blocks),'source_models':models,'transport':{'row_bits':rowbits,'beat_bits':beatbits,'logical_slices':96,'transit_cycles':4,'landing_cycles':1,'bottom_corridor':[10,0,680.24,102],'hardleaf_placement':None,'status':'Needs actual96slice hardened dimensions and leaf clock pins; no invented replacement hardleaf dimensions.'},'ew_cut':{'demand_bits':rowbits+beatbits,'M8_macro_obstructions':sum(m['obstruction_rects'].get('M8',0) for m in models.values()),'M6_available_only_in_empty_bottom_corridor_um':102,'M8_full_height_um':H,'gross_tracks':H/.08+102/.064,'demand_over_gross':(rowbits+beatbits)/(H/.08+102/.064),'capacity_at_60percent':.6*(H/.08+102/.064),'two_pitch_face_slots':int(H/.16)+int(102/.128),'assumptions':['M8 over macro is unobstructed in actual sourceLEFs.','M6 above compute is NOT assumed free; sourceLEFs contain real detailed M6 OBS.','Top-level PG clock via keepouts and landing detours still need route measurement.','A 20um channel alone cannot carry3705EW bits; upperM8 overmacro is essential.']},'clock_plan':{'roots':['one root per compute child','one real root per transport slice or bounded child group','separate pin/gather/control roots'],'masking':False,'qualification':'No clock-skew or timing claim until hardleafCTS and tileTT/FF closure.'},'open':['actual96transport leaf origins and shapes','existing tile input receiver/gather/xrel cells and clock roots must be placed in remaining area','actual net-by-net registered <=500um reach through legal routing corridors','M8/PG reservation in die context','TTsetup FFhold and DRC0']}
out['re_cut_group_candidate']={'qualification':'UNBUILT: dimensions area-price actual oldgroup outlines; noCTS or access claim. Not R90rotation.','old_group_outline_sum_um2':79501.8,'groups':[{'name':'rowW0','x':10,'y':422.24,'w':112.32,'h':70},{'name':'rowW1','x':356.72,'y':422.24,'w':112.32,'h':70},{'name':'beatW','x':10,'y':1,'w':466.56,'h':100},{'name':'beatE','x':486.56,'y':1,'w':93.312,'h':100},{'name':'rowE0','x':589.872,'y':1,'w':39.192,'h':100},{'name':'rowE1','x':639.064,'y':1,'w':39.192,'h':100}],'logical_slices':96,'real_child_clock_roots':6,'new_outline_sum_um2':2*112.32*70+(466.56+93.312+2*39.192)*100,'caveats':['rowW abuts bdc north face: routed macro halos and PG access not proven.','Bottom strips have10um intergroup channels and1um clearance to xs.','20um every transportmacro-to-compute clearance is NOT met. Compute-to-compute remains20um.','Old area may change with sourcekeepq1 and newaspectratio, so re-synthesis/CTS/route required.','BeatW466.56um width requires actual clockroot partition if measuredspread fails.','Pin placement must derive each sourcebit and destinationface; no artificial clock masks.']}
pathlib.Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['verdict','tile','min_child_gap_um','compute_area_um2','ew_cut']},indent=2))
