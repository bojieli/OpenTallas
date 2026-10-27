# Planning-only feasibility probe for missing canonical IDXN quarters, preserving die outline.
import json,sys,pathlib,numpy as np,math
pd,out=sys.argv[1:3];options=set(sys.argv[3:]);pd=pathlib.Path(pd);raw=json.loads((pd/'die_plan.json').read_text());report={}
G=4.32;halo=4.32;cw,ch=218.592,187.488
for tn in ['q_hub_nw','q_hub_ne']:
 t=raw['partition_types'][tn];W,H=t['outline_um'];nx,ny=int(W/G),int(H/G);a=np.zeros((ny,nx),dtype=np.uint8)
 def block(rect,ext=0):
  x0,y0,x1,y1=rect;x0=max(0,int(math.floor((x0-ext)/G)));x1=min(nx,int(math.ceil((x1+ext)/G)));y0=max(0,int(math.floor((y0-ext)/G)));y1=min(ny,int(math.ceil((y1+ext)/G)));a[y0:y1,x0:x1]=1
 def rect(c):x,y=c['origin_um'];w,h=c['outline_um'];return [x,y,x+w,y+h]
 for h in t.get('hard_cores',[]):
  if '--native-keybuf' not in options or 'keybuf' not in h['module']:block(rect(h),halo)
 for c in t.get('contents',[]):
  if 'origin_um' in c and 'outline_um' in c and '--repack-soft' not in options and ('--native-keybuf' not in options or 'keybuf' not in c['inst']):block(rect(c),halo)
 for s in t.get('internal_stations',[]):
  for x,y in (s.get('regs_um',[]) if '--move-stations' not in options else []):block([x-G/2,y-G/2,x+G/2,y+G/2],G/2)
 for s in t.get('ft_slots',[]):
  for x,y in (s.get('regs_um',[]) if '--move-stations' not in options else []):block([x-G/2,y-G/2,x+G/2,y+G/2],G/2)
 block([0,0,W,4.32]);block([0,H-4.32,W,H]);block([0,0,4.32,H]);block([W-4.32,0,W,H])
 initial=int((a==0).sum())*G*G;placements=[];clusters=[]
 svg=[c for c in t.get('hard_cores',[]) if c['inst'].startswith('u_svg_')]
 for p in range(66):
  # Include clock/PG access streets inside every planned core pitch.
  bw,bh=math.ceil((cw+2*halo)/G),math.ceil((ch+2*halo)/G)
  cs=np.pad(a.cumsum(0,dtype=np.int64).cumsum(1),( (1,0),(1,0)))
  sums=cs[bh:,bw:]-cs[:-bh,bw:]-cs[bh:,:-bw]+cs[:-bh,:-bw]
  ys,xs=np.where(sums==0)
  if not len(xs):break
  owner=svg[min(p//16,len(svg)-1)] if svg else None
  tx,ty=(owner['origin_um'][0]+owner['outline_um'][0]/2,owner['origin_um'][1]+owner['outline_um'][1]/2) if owner else (W/2,H/2)
  score=abs(xs*G+halo+cw/2-tx)+abs(ys*G+halo+ch/2-ty)
  k=int(np.argmin(score));x,y=xs[k]*G+halo,ys[k]*G+halo;block([x-halo,y-halo,x+cw+halo,y+ch+halo])
  placements.append(dict(index=p,kind='hcol' if p<64 else 'tail',origin_um=[round(x,4),round(y,4)],outline_um=[cw,ch],producer=owner['inst'] if owner else None,manhattan_to_producer_um=round(float(score[k]),3)))
 report[tn]=dict(status='GEOMETRY_PROBE_ONLY',options=sorted(options),requested=66,placed=len(placements),lot_um=[cw,ch],halo_um=halo,free_area_initial_mm2=round(initial/1e6,4),placements=placements,unhandled='native source key/control bundles, FT per-bit sites, cuts, clock lattice, reset/start, and token pricing still required')
 print(tn,'free',round(initial/1e6,4),'placed',len(placements),'of66',flush=True)
pathlib.Path(out).write_text(json.dumps(report,indent=1)+'\n')
