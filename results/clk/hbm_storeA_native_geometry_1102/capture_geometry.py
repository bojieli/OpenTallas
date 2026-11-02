from pathlib import Path
import json,re,math,collections,hashlib
R=Path.cwd();binding=json.load(open(R/'native_macro_binding.json'));rows={r['actual_native_name']:r for r in binding['rows']};freeze=json.load(open(R/'freeze.json'));W,H=freeze['outline_um'];frame=(4.32,4.32,W-4.32,H-4.32);halo=4.32;rp=.27;cp=.054;EPS=1e-8
lef=(R/'sram.lef').read_text();mw,mh=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups());pins={}
for m in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*\n',lef,re.S):
 rects=[list(map(float,x))for x in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;',m[2])]
 pins[m[1]]=rects
std=(R/'std.lef').read_text();clock=json.load(open(R/'clock_roots.json'));ffmaster={p['inst']:p['master']for q in clock for p in q['FF_CLK']};masters={}
for name in set(ffmaster.values()):
 m=re.search(r'\bMACRO\s+'+re.escape(name)+r'\s*\n(.*?)\nEND\s+'+re.escape(name)+r'\s*\n',std,re.S);assert m,name
 cw,ch=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',m[1]).groups());p=re.search(r'\bPIN\s+D\s*\n(.*?)\n\s*END\s+D\s*\n',m[1],re.S);assert p,name
 rects=[list(map(float,x))for x in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;',p[1])];assert rects
 masters[name]=dict(width=cw,height=ch,D_rects=rects,D_bbox=[min(q[0]for q in rects),min(q[1]for q in rects),max(q[2]for q in rects),max(q[3]for q in rects)])
print('LEF',mw,mh,masters,flush=True)
# Retain exact per-read-pin -> mapped FF.D frontier; no source synthesizer XY.
macros=json.load(open(R/'macro_ownership.json'));ff_sources=collections.defaultdict(list);macro_boxes=[]
for q in macros:
 b=rows[q['instance']];assert b['planned_orient']=='R0';ox,oy=b['planned_xy_um'];macro_boxes.append((ox,oy,ox+mw,oy+mh));g=q['pin_groups']['rd_out'];assert g['direction']=='OUTPUT'
 for p in g['pins']:
  ps=pins[p['pin']];assert len(ps)==1,(p['pin'],ps);a,c,d,e=ps[0];rect=[ox+a,oy+c,ox+d,oy+e]
  for kind,owner,pin in p['frontier']:
   if kind=='ff':assert pin=='D';ff_sources[owner].append(dict(macro=q['instance'],pin=p['pin'],rect_um=rect))
del macros
assert len(ff_sources)==1024,len(ff_sources)
def extremes(rects):
 return dict(umax=max(a+b for a,b,c,d in rects),umin=min(c+d for a,b,c,d in rects),vmax=max(a-d for a,b,c,d in rects),vmin=min(c-b for a,b,c,d in rects),xmax=max(a for a,b,c,d in rects),xmin=min(c for a,b,c,d in rects),ymax=max(b for a,b,c,d in rects),ymin=min(d for a,b,c,d in rects))
def constraints(e,r,C=(0,0,0,0)):
 a,b,c,d=C
 return (e['xmax']-c-r,e['xmin']-a+r,e['ymax']-d-r,e['ymin']-b+r,e['umax']-c-d-r,e['umin']-a-b+r,e['vmax']-c+b-r,e['vmin']-a+d+r)
def y_window(bounds,fxlo=-1e99,fxhi=1e99,fylo=-1e99,fyhi=1e99):
 xl,xh,yl,yh,ul,uh,vl,vh=bounds;xl=max(xl,fxlo);xh=min(xh,fxhi)
 if xl>xh+EPS or ul>uh+EPS or vl>vh+EPS:return None
 lo=max(yl,fylo,xl-vh,ul-xh,(ul-vh)/2);hi=min(yh,fyhi,uh-xl,xh-vl,(uh-vl)/2)
 return None if lo>hi+EPS else(lo,hi,xl,xh,ul,uh,vl,vh)
def continuous_min(e):
 lo=0.;hi=W+H
 for _ in range(45):
  mid=(lo+hi)/2
  if y_window(constraints(e,mid))is None:lo=mid
  else:hi=mid
 return hi
interval_cache={}
def free_rows(master):
 if master in interval_cache:return interval_cache[master]
 cw,ch=masters[master]['width'],masters[master]['height'];out=[]
 for iy in range(math.floor((frame[3]-frame[1]-ch)/rp+EPS)+1):
  y=frame[1]+iy*rp;blocked=[]
  for a,b,c,d in macro_boxes:
   if y<d+halo-EPS and y+ch>b-halo+EPS:blocked.append((a-halo-cw,c+halo))
  spans=[];start=frame[0]
  for a,b in sorted(blocked):
   if b<=start+EPS:continue
   if a>start+EPS:spans.append((start,min(a,frame[2]-cw)))
   start=max(start,b)
  if start<=frame[2]-cw+EPS:spans.append((start,frame[2]-cw))
  out.append((y,[(a,b)for a,b in spans if b>=a-EPS]))
 interval_cache[master]=out;return out
def candidate(e,master,r):
 model=masters[master];cw,ch=model['width'],model['height'];base=model['D_bbox']
 for orient in ['R0','MX']:
  C=base if orient=='R0'else[base[0],ch-base[3],base[2],ch-base[1]]
  bounds=constraints(e,r,C);win=y_window(bounds,frame[0],frame[2]-cw,frame[1],frame[3]-ch)
  if win is None:continue
  yl,yh,xl,xh,ul,uh,vl,vh=win
  ilo=max(0,math.ceil((yl-frame[1])/rp-EPS));ihi=min(len(free_rows(master))-1,math.floor((yh-frame[1])/rp+EPS))
  for iy in range(ilo,ihi+1):
   y,intervals=free_rows(master)[iy];lo=max(xl,ul-y,vl+y);hi=min(xh,uh-y,vh+y)
   if lo>hi+EPS:continue
   for a,b in intervals:
    low=max(a,lo);high=min(b,hi)
    x=frame[0]+math.ceil((low-frame[0])/cp-EPS)*cp
    if x<=high+EPS:return dict(origin_um=[round(x,9),round(y,9)],orient=orient,D_bbox_um=[x+C[0],y+C[1],x+C[2],y+C[3]],row_index=iy)
 return None
out=[]
for i,(ff,src)in enumerate(sorted(ff_sources.items())):
 rects=[q['rect_um']for q in src];e=extremes(rects);centres=[((a+c)/2,(b+d)/2)for a,b,c,d in rects];us=[x+y for x,y in centres];vs=[x-y for x,y in centres];centre_lb=max(max(us)-min(us),max(vs)-min(vs))/2;rect_lb=continuous_min(e);master=ffmaster[ff];c=candidate(e,master,405)
 q=dict(FF=ff,master=master,source_pins=src,source_macros=sorted({x['macro']for x in src}),pin_centre_continuous_minimax_um=centre_lb,pin_rectangle_continuous_minimax_um=rect_lb,optimistic_legal_row_405_candidate=c,verdict='NECESSARY_GEOMETRY_CANDIDATE_ONLY'if c else'FAIL_EVEN_OPTIMISTIC_LEGAL_ROW_405')
 if c is None:
  lo=405.;hi=W+H
  for _ in range(23):
   mid=(lo+hi)/2
   if candidate(e,master,mid)is None:lo=mid
   else:hi=mid
  q['optimistic_min_legal_radius_um']=hi;q['nearest_legal_row_candidate']=candidate(e,master,hi+1e-5)
 out.append(q)
 if (i+1)%64==0:print('FF',i+1,'fails',sum(x['optimistic_legal_row_405_candidate']is None for x in out),flush=True)
fails=[q for q in out if q['optimistic_legal_row_405_candidate']is None]
res=dict(status='FAIL_CURRENT_PLANNED_CAPTURE_ROW_GEOMETRY'if fails else'NECESSARY_CAPTURE_GEOMETRY_ONLY',source_odb_sha256=binding['source_odb_sha256'],SRAM_LEF_sha256=hashlib.sha256(lef.encode()).hexdigest(),std_LEF_sha256=hashlib.sha256(std.encode()).hexdigest(),outline_um=[W,H],core_frame_um=list(frame),SRAM_size_um=[mw,mh],macro_halo_um=halo,site_pitch_um=cp,row_pitch_um=rp,FF_masters=masters,capture_FF_count=len(out),FF_with_no_optimistic_405_row_candidate=len(fails),max_continuous_pin_centre_minimax_um=max(q['pin_centre_continuous_minimax_um']for q in out),max_continuous_pin_rectangle_minimax_um=max(q['pin_rectangle_continuous_minimax_um']for q in out),max_optimistic_min_legal_radius_um=max((q.get('optimistic_min_legal_radius_um',0)for q in out),default=0),rows=out,scope='necessary source-pin to capture geometry before PLACE; no synthesis XY, no actual routed hop/timing claim',optimism=['CaptureD union bounding rectangle includes inaccessible gaps, making FAIL conservative','Either R0/MX allowed at every row because native floorplan rows do not exist yet','No other stdcell occupancy, PG obstruction or global capture capacity constraints','Combinational connectivity frontiers are conservative structural reach, not Boolean sensitization','Candidate existence is never full405 reach or source/timing/placement PASS'])
(R/'capture_geometry.json').write_text(json.dumps(res,indent=2)+'\n');print('FINAL',res['status'],'fails',len(fails),'maxlegal',res['max_optimistic_min_legal_radius_um'],flush=True)
