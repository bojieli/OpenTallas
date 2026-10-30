import json,hashlib,sys,math
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import schema as S
B=Path(__file__).resolve().parent;f=B/'parent_plan.json';D=json.load(open(f));assert hashlib.sha256(f.read_bytes()).hexdigest()=='bcfcb4e1737e8140fab9c94aec6128c4a086ab5fa953e07159813abb11819d10';P=S.Plan(D)
def pt(x,y,w,h,o):return dict(R0=(x,y),MX=(x,h-y),MY=(w-x,y),R180=(w-x,h-y))[o]
def rect(r,w,h,o,ox=0,oy=0):
 q=[pt(x,y,w,h,o)for x in [r[0],r[2]]for y in [r[1],r[3]]];return [round(ox+min(a[0]for a in q),6),round(oy+min(a[1]for a in q),6),round(ox+max(a[0]for a in q),6),round(oy+max(a[1]for a in q),6)]
def dist(a,b):return math.hypot(max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0))
out=[]
for tn,t in P.types.items():
 for c in t.get('hard_cores',[]):
  if 'ot_s81sl_eg_c'not in str(c):continue
  w,h=c['outline_um'];ox,oy=c['origin_um'];dx,dy=c.get('track_offset_um',[0,0]);ox+=dx;oy+=dy;o=c.get('orient','R0');old=[127.104,.0,127.128,.084];new=[127.092,0,127.14,.48]
  a=rect(old,w,h,o,ox,oy);b=rect(new,w,h,o,ox,oy);tw,th=t['outline_um'];cx=(b[0]+b[2])/2
  ns=[]
  for n in t.get('hard_cores',[]):
   if n is c:continue
   nx,ny=n['origin_um'];dd=n.get('track_offset_um',[0,0]);nw,nh=n['outline_um'];bb=[nx+dd[0],ny+dd[1],nx+dd[0]+nw,ny+dd[1]+nh];ns.append((dist(b,bb),n['inst']))
  nn=min(ns)if ns else(None,None)
  inst=[]
  for pn,p in P.parts.items():
   if p['type']!=tn:continue
   px,py=p['origin_um'];po=p.get('orient','R0');bb=rect(b,tw,th,po,px,py);aa=rect(a,tw,th,po,px,py);ll=P.layers['M5'];cc=(bb[0]+bb[2])/2;phase=abs((cc-ll['offset_um'])/ll['pitch_um']-round((cc-ll['offset_um'])/ll['pitch_um']))<1e-6
   inst.append(dict(partition=pn,partition_orient=po,old_clock_rect_die=aa,new_clock_rect_die=bb,M5_track_PASS=phase))
  out.append(dict(type=tn,core_inst=c['inst'],core_orient=o,core_origin_with_track_offset=[ox,oy],old_clock_rect_type=a,new_clock_rect_type=b,contained_in_parent=0<=b[0]<=b[2]<=tw and 0<=b[1]<=b[3]<=th,contained_in_child=True,nearest_other_core=nn[1],nearest_other_core_clearance_um=nn[0],parent_PG_band_blocked_old_and_new=S.pg_blocked('M5',cx),instances=inst))
R=dict(scope='Private unsignedcandidate exactevent3parent-fit only; no sourceadoption/P&R; originalFAILs preserved',plan_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),candidate_source='908787e642a',types=len(out),instances=sum(len(q['instances'])for q in out),all_contained=all(q['contained_in_parent']for q in out),all_die_M5_track_PASS=all(z['M5_track_PASS']for q in out for z in q['instances']),PG='NativechildM5PG startsy4.32 so newrecty0..0.48 clear; parentconservativeM5PGbandblocked alreadyoldclockXunchanged: requires actualparentPDN/accessadjudication, noPGPASSclaim',unchanged=['all other200childpins','parentexternalpins','outline','neighbors','RTL','cycles','clockperiodandcyclecontract'],rows=out)
(B/'parent_fit.json').write_text(json.dumps(R,indent=2));print({k:v for k,v in R.items()if k!='rows'})
