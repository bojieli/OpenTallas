"""Map real macro data pins to first/last mapped FF cones and site those FFs without altering RTL edges."""
import json,re,math,hashlib,argparse
from pathlib import Path
from collections import defaultdict

def intersect(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
def run(mapped,lef,geo,placement,out,fflef):
 d=json.loads(mapped.read_text())['modules']['qkd_kvs_emb_rope'];g=json.loads(geo.read_text());p=json.loads(placement.read_text());cells=d['cells'];txt=lef.read_text();pins={}
 for n,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1',txt,re.S):
  rects=[tuple(map(float,x)) for x in re.findall(r'RECT\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)',body)]
  if rects:pins[n]=[(a+c)/2 for a,b,c,e in rects[:1]]+[(b+e)/2 for a,b,c,e in rects[:1]]
 assert 'R90' not in p['macro_LEF_symmetry'];assert all(m['orientation']=='R0' for m in p['macros'])
 drivers={};sinks=defaultdict(list);outpins={};ff=set()
 for n,c in cells.items():
  con=c.get('connections',{});typ=c['type']
  if not con:continue
  outs={'rd_out'} if typ.startswith('ot_sram_') else {'QN'} if typ.startswith('DFF') else {'Y'}
  assert outs<=set(con),(n,typ)
  outpins[n]=outs
  if typ.startswith('DFF'):ff.add(n)
  for port,bits in con.items():
   for b in bits:
    if not isinstance(b,int):continue
    if port in outs:drivers[b]=n
    else:sinks[b].append((n,port))
 def walk(bit,forward):
  todo=[bit];seen=set();found=set();pi=set()
  while todo:
   b=todo.pop()
   if b in seen:continue
   seen.add(b)
   cs=sinks.get(b,[]) if forward else [(drivers[b],None)] if b in drivers else []
   if not cs:pi.add(b)
   for n,port in cs:
    if n in ff:
     if not forward or port=='D':found.add(n)
     continue
    if cells[n]['type'].startswith('ot_sram_'):continue
    for q,bits in cells[n].get('connections',{}).items():
     if (q in outpins.get(n,set()))==forward:todo += [x for x in bits if isinstance(x,int)]
  return found,pi
 fflib=json.loads(fflef.read_text())
 constraints=defaultdict(list);unmapped=[];n_pin=0
 for m in p['macros']:
  inst=m['inst'];c=cells[inst];x,y=m['body_rect_um'][:2]
  for port,bits in c['connections'].items():
   if port in ['clk','rr_en','rr_addr','cr_en','cr_sel','w_mask_in']:continue
   for i,b in enumerate(bits):
    if not isinstance(b,int):continue
    pn=port if len(bits)==1 else f'{port}[{i}]';assert pn in pins,pn
    a,e=pins[pn];pt=[x+a,y+e];found,pi=walk(b,port=='rd_out');n_pin+=1
    for f in found:constraints[f].append(dict(macro=inst,pin=pn,xy_um=pt,direction='macro_to_D' if port=='rd_out' else 'QN_to_macro'))
    if not found:unmapped.append(dict(macro=inst,pin=pn,net=b,primary_or_open_nets=sorted(pi)))
 obs=[]
 for c in g['cores']:
  a,b=c['origin_um'];w,h=c['outline_um'];obs.append((a-10.8,b-10.8,a+w+10.8,b+h+10.8))
 obs += [tuple(r['rect_um']) for r in g['reserved']]
 for f in g['ft']:
  for st in f.get('bit_sites_um',[]):
   xs=[s[0] for s in st];ys=[s[1] for s in st];obs.append((min(xs)-2.16,min(ys)-2.16,max(xs)+2.16,max(ys)+2.16))
 obs += [tuple(m['halo_rect_um']) for m in p['macros']]
 # Every chosen FF occupies one legal ASAP7 site. Preserve exact FF count and every original source edge.
 rows=[];occupied=[];failed=[]
 for f,cs in sorted(constraints.items(),key=lambda x:-len(x[1])):
  xs=[c['xy_um'][0] for c in cs];ys=[c['xy_um'][1] for c in cs];cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2;ix=round(cx/1.08);iy=round(cy/.27)
  found=None
  for radius in range(0,502):
   cand=[]
   for dx in range(-radius,radius+1):
    dy=radius-abs(dx)
    for sign in ({1,-1} if dy else {1}):
     a,b=ix+dx,iy+sign*dy
     x=a*1.08;y=b*.27;fw,fh=fflib['cells'][cells[f]['type']]['size'];box=(x,y,x+fw,y+fh)
     if x<2.16 or y<2.16 or box[2]>g['outline_um'][0]-2.16 or box[3]>g['outline_um'][1]-2.16:continue
     loc=[x+fw/2,y+fh/2];orient='R0' if b%2==0 else 'MX';pinmax=0
     for c in cs:
      pn='D' if c['direction']=='macro_to_D' else 'QN'
      for pr in fflib['cells'][cells[f]['type']]['pins'][pn]:
       for px in [pr[0],pr[2]]:
        for py in [pr[1],pr[3]]:
         yy=py if orient=='R0' else fh-py
         pinmax=max(pinmax,abs(x+px-c['xy_um'][0])+abs(y+yy-c['xy_um'][1])+.024)
     mx=pinmax
     if mx>405 or any(intersect(box,r) for r in obs) or any(intersect(box,r) for r in occupied):continue
     cand.append((mx,a,b,loc,box))
   if cand:
    found=min(cand);break
  if found is None:failed.append(dict(cell=f,constraints=cs));continue
  mx,a,b,loc,box=found;occupied.append(box);rows.append(dict(cell=f,master=cells[f]['type'],orientation='R0' if b%2==0 else 'MX',rect_um=box,QN_D_site_centre_um=loc,macro_pin_direct_max_um=mx,macro_pin_constraints=cs))
 result=dict(schema='opentallas.qwen-kv-context-macro-ff-sites.v1',state='MAPPED_DQ_CONE_SITE_CANDIDATE_ONLY',FF_LEF_source=fflib['source'],FF_LEF_sha256=fflib['sha256'],endpoint_model='all FF D/QN pin-rectangle corners with R0/MX row orientation; macro pin centre plus24nm conservative rectangle envelope',mapped_sha256=hashlib.sha256(mapped.read_bytes()).hexdigest(),LEF_sha256=hashlib.sha256(lef.read_bytes()).hexdigest(),macro_pins_traced=n_pin,FFs_constrained=len(constraints),FFs_sited=len(rows),failed_FF_count=len(failed),unmatched_macro_pin_cones=unmapped,
 macro_pin_DQ_direct_max_um=max((r['macro_pin_direct_max_um'] for r in rows),default=0),added_data_cycles=0,added_FF=0,RTL_changed=False,route_qualified=False,STA_qualified=False,
 scope='Real LEF pin rectangles and actual mapped first/last FF cone endpoints. Candidate FF centres retain source graph edges. All intervening combinational cells are unplaced; direct reach is not routed delay.',rows=rows,failed_FFs=failed,
 open_requirements=['Site the intervening actual combinational cones without stretching the pin-to-FF paths; run endpoint-specific path reach before build.',
 'Place all unconstrained mapped cells in the common logic region and compose exact six added-clock tap sinks from full FF positions.',
 'No claim about shared routing channel demand, clock/PG continuity, or post-route timing.'])
 out.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:result[k] for k in ['state','macro_pins_traced','FFs_constrained','FFs_sited','failed_FF_count','macro_pin_DQ_direct_max_um']}));print('unmatched',len(unmapped))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--mapped',type=Path,required=True);a.add_argument('--lef',type=Path,required=True);a.add_argument('--geometry',type=Path,required=True);a.add_argument('--placement',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--ff-lef',type=Path,required=True);p=a.parse_args();run(p.mapped,p.lef,p.geometry,p.placement,p.out,p.ff_lef)
