#!/usr/bin/env python3
"""Prepare actual-native SU pin/macro tables; never adopt or rewrite source calendars."""
import argparse,collections,copy,hashlib,json,math,pathlib,re,shutil
M={'ot_hbm_su_static_pgslice_lg__lane_exp0_id':'ot_hnx_su_exp__rst3','ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691':'ot_hnx_su_exp__rst3','ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77':'ot_hnx_su_plain4__lid9_rst3','ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526':'ot_hnx_su_plain4__lid9_rst3'}
MACRO='ot_sram_1r1w_128x256_m1_r2c2';MW,MH=94.824,41.064
ROOT=pathlib.Path(__file__).resolve().parents[2]
PACK=ROOT/'physical/die_plan/hbm_arch_cores/native_1030'
def ports(top):
 s=(PACK/(top+'.sv')).read_text().split(');',1)[0]
 return [(d,n,int(a)+1) for d,a,n in re.findall(r'(input|output) wire \[(\d+):0\] (\w+)',s)]
def snap(v):return round(.024+round((v-.024)/.048)*.048,6)
def centred(count,pitch,centre):return [round(snap(centre-(count-1)*pitch/2)+i*pitch,6) for i in range(count)]
def named(n,w,i):return n if w==1 else n+'['+str(i)+']'
def build(module,W,H):
 top=M[module];P=ports(top);banks=1 if top=='ot_hnx_su_exp__rst3' else 4;cx,cy=W/2,H/2
 gx=round(((W-310.824)/2)/4.32)*4.32
 if banks==1:ys=[53.73,118.8]
 else:
  height=8*MH+6*12.984+24.024;start=(H-height)/2
  ys=[start+i*54.048+(11.04 if i>=4 else 0) for i in range(8)]
 macros=[]
 for b in range(banks):
  for r in range(6):
   row=2*b+r//3;col=r%3
   macros.append(dict(inst='u_native.m'+str(2*b)+'.u_data.g_read['+str(r)+'].u_m',macro=MACRO,xy_um=[round(gx+108*col,6),round(ys[row],6)],orient='MY' if col==2 else 'R0',bank=b,reader=r,read_face='E' if col==2 else 'W'))
 pts=[]
 def add(n,face,x,y,layer=None,**kw):
  layer=layer or ('M4' if face in ('W','E') else 'M5')
  pts.append(dict(name=n,face=face,layer=layer,x=round(x,6),y=round(y,6),**kw))
 for d,n,w in P:
  if n=='bank_clk':add(n,'C',snap(cx),cy,w=.048,h=.48)
  elif n in ('rst_n','rst_bcast_n'):
   add(n,'C',snap(cx+(-4.32 if n=='rst_n' else 4.32)),cy+7.344)
  elif n=='rst_lane_n':
   for b in range(w):
    yy=cy+7.344 if banks==1 else (ys[2*b]+ys[2*b+1]+MH)/2
    add(named(n,w,b),'C',snap(cx),yy)
  elif n=='lane_lane_id':
   for i,x in enumerate(centred(w,1.056,cx-110)):
    add(named('strap_lane_lane_id',w,i),'S',x,.096)
  elif n=='cmd0_D':
   for i,x in enumerate(centred(w,.192,cx)):add(named(n,w,i),'N',x,H-.096)
 # All ordinary miscellaneous inputs stay one coherent S group, no hidden constants.
 misc=[(n,w) for d,n,w in P if d=='input'and n not in ('bank_clk','rst_n','rst_lane_n','rst_bcast_n','lane_lane_id','cmd0_D')]
 xx=iter(centred(sum(w for n,w in misc),.192,cx))
 for n,w in misc:
  for i in range(w):add(named(n,w,i),'S',next(xx),.096)
 # Actual output-bank and output-lane ownership is checked by topology.json before use.
 for b in range(banks):
  for r in range(6):
   row=2*b+r//3;col=r%3;face='E' if col==2 else 'W'
   count=32 if face=='E' else 64;offset=0 if face=='E' else col*32
   yy=centred(count,.192,ys[row]+MH/2)
   for j in range(32):add('bank_read_data['+str(b*192+r*32+j)+']',face,W-.096 if face=='E' else .096,yy[offset+j])
  other=[(n,w) for d,n,w in P if d=='output'and n!='bank_read_data']
  assert sum(w//banks for n,w in other)==193
  yy=iter(centred(193,.192,(ys[2*b]+ys[2*b+1]+MH)/2))
  for n,w in other:
   per=w//banks;assert per*banks==w
   for j in range(per):add(named(n,w,b*per+j),'E',W-.096,next(yy))
 expected={named('strap_lane_lane_id' if n=='lane_lane_id'else n,w,i) for d,n,w in P for i in range(w)}
 assert len(pts)==sum(w for d,n,w in P)and{p['name']for p in pts}==expected
 assert len({(p['layer'],p['x'],p['y'])for p in pts})==len(pts),'overlapping pin points'
 for p in pts:assert 0<=p['x']<=W and 0<=p['y']<=H,p
 for m in macros:
  x,y=m['xy_um'];assert min(x,y,W-x-MW,H-y-MH)>=4.32-1e-6,m
 density={}
 for face in ('N','S','W','E'):
  vals=sorted(p['x']if face in ('N','S')else p['y']for p in pts if p['face']==face)
  density[face]=max((sum(1 for v in vals if x-1e-6<=v<x+10-1e-6)/10 for x in vals),default=0)
 assert max(density.values())<=6,density
 # Conservative full SRAM read box -> planned boundary FF; all possible256sourcebits bound the selected32word.
 reach=[]
 for m in macros:
  b,r=m['bank'],m['reader'];targets=[p for p in pts if p['name'].startswith('bank_read_data[')and b*192+r*32<=int(p['name'].split('[')[1][:-1])<b*192+r*32+32]
  x,y=m['xy_um'];sx=x+MW if m['orient']=='MY'else x
  longest=max(abs(sx-(W-4.32 if p['face']=='E' else 4.32))+max(abs(y-p['y']),abs(y+MH-p['y']))for p in targets)
  reach.append(dict(bank=b,reader=r,macro=m['inst'],read_face=m['read_face'],planned_upper_bound_um=round(longest+.05,3)))
 assert max(q['planned_upper_bound_um']for q in reach)<=405,reach
 return pts,macros,dict(module=module,native=top,outline_um=[W,H],pins=len(pts),banks=banks,face_peak_per_um=density,macro_read_to_planned_boundary_ff_upper_bound_um=max(q['planned_upper_bound_um']for q in reach),reach=reach,source_component_added_cycles=0,physical_face_shell_cycles='in1/out1, must be priced in native calendar before adoption',holds=['Native ID capture R7 bypass not yet qualified','Exact native topology ownership receipt required','New station/pin-interface reconciliation and actual placement review required'])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('base');ap.add_argument('out');a=ap.parse_args();base=pathlib.Path(a.base);out=pathlib.Path(a.out);assert not out.exists();shutil.copytree(base,out)
 p=out/'die_plan.json';D=json.load(open(p));reports={};changed=[];pf={};macro_rows={}
 for tn,t in D['partition_types'].items():
  for kind in ('hard_cores','contents'):
   for c in t.get(kind,[]):
    m=c.get('module')
    if m not in M:continue
    W,H=map(float,c['outline_um'])
    if m not in reports:
     pins,macros,report=build(m,W,H);reports[m]=report
     name='cores/'+m+'__current_native_r7_PREP.json';(out/name).write_text(json.dumps(pins,indent=1)+'\n');pf[m]=name;macro_rows[m]=macros
    assert reports[m]['outline_um']==[W,H]
    old=c.get('parent_id_straps',{}).get('lane_lane_id')
    if old is None:
     s=c.get('straps',[]);assert len(s)==1 and s[0]['port']=='strap_lane_lane_id';old=dict(width=s[0]['width'],value=s[0]['value'])
    assert old['width']==(11 if M[m]=='ot_hnx_su_exp__rst3' else 9)
    c['pins_file']=pf[m];c.pop('parent_id_straps',None);c['straps']=[dict(port='strap_lane_lane_id',**old,note='R7 PREP only: exact current native ID; no adoption before bypass proof')];c['physical_id_alias']={'strap_lane_lane_id':'lane_lane_id'}
    c['note']=c.get('note','')+' | SOURCE PREP actual native ABI; legacy decoded interface replaced, same outline; unadopted.'
    changed.append(dict(type=tn,kind=kind,inst=c['inst'],module=m,id=old))
 p.write_text(json.dumps(D,indent=1)+'\n')
 ce=out/'clock_entries.json';C=json.load(open(ce))
 for entries in C.values():
  if not isinstance(entries,dict):continue
  for inst,e in entries.items():
   if not isinstance(e,dict)or e.get('module')not in reports:continue
   W,H=reports[e['module']]['outline_um'];cx,cy=W/2,H/2;e.update(port='bank_clk',merged_clock_ports=[],tap=inst+'.bank_clk',xy_um=[cx,cy],island_um=[cx-4.32,cy-4.32,cx+4.32,cy+4.32],source='PREP actual native bank_clk, same current clock domain; no adoption')
 ce.write_text(json.dumps(C,indent=1)+'\n')
 (out/'native_su_macro_placement.json').write_text(json.dumps(macro_rows,indent=1)+'\n')
 report=dict(status='PREP_UNADOPTED_NOT_PNR',base=str(base),base_plan_sha256=hashlib.sha256((base/'die_plan.json').read_bytes()).hexdigest(),changed=changed,modules=reports,remaining=['Rebuild core_macros and clock core_islands from native hierarchy before G0C','Reconcile all native interface/station endpoints; old decoded-port station data is stale','Finish typed-ID capture bypass proof, no new masks','Independent actual placement GEOM reply and all physical gates before route'])
 (out/'native_su_pinplan_report.json').write_text(json.dumps(report,indent=2)+'\n');print('PREP',len(changed),'descriptors',[(k,v['pins'],v['macro_read_to_planned_boundary_ff_upper_bound_um'])for k,v in reports.items()])
if __name__=='__main__':main()
