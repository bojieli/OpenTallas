from pathlib import Path
import sys,json,collections,math
R=Path(__file__).parent;P=R/'inputs';sys.path.insert(0,str(R/'tools'));import geom_rules as G
D=G.Design(P/'geom.tsv');F=json.load(open(P/'FF_targets.json'));T=json.load(open(R/'DATA_targets.json'))
for cid,c in list(D.cells.items()):
 t=T.get(c[6])or F.get(c[6])
 if t:
  a=list(c);a[2:6]=[v/1000 for v in t['bbox_dbu']];D.cells[cid]=tuple(a)
x0,x1,ycut=60,70,1137.5;weights=collections.Counter();drivers=collections.Counter();rows=[];total=0.
def role(c):
 if c[6]in T:return'owned_DATA'
 if c[6]in F:return'fixed_'+F[c[6]]['family']
 return'other_fixed_FF'if c[0]=='S'else'other_held_comb'
for ni,(sig,dr,sk)in enumerate(D.nets):
 if sig=='CLOCK':continue
 pts=[];eps=[]
 for ep in([dr]if dr else[])+sk:
  if ep[0]=='p':
   p=D.pin_by_k.get(ep[1])
   if p:pts.append((p['x'],p['y']));eps.append(dict(name=p['name'],role='fixedPIO',xy=pts[-1]))
  elif ep[1]in D.cells:
   c=D.cells[ep[1]];xy=G.ctr(c);pts.append(xy);eps.append(dict(name=c[6],master=c[1],role=role(c),xy=xy))
 if len(pts)<2 or not min(y for x,y in pts)<ycut<max(y for x,y in pts):continue
 a=math.floor(min(x for x,y in pts));b=math.floor(max(x for x,y in pts));hit=max(0,min(x1-1,b)-max(x0,a)+1)
 if not hit:continue
 w=hit/(b-a+1);total+=w;driver=eps[0]if dr else dict(name='NO_DRIVER',role='unknown');classes=','.join(sorted({x['role']for x in eps}));weights[driver['role']]+=w;drivers[driver['name']]+=w;rows.append(dict(geom_net_index=ni,column_crossing_weight=w,driver=driver,endpoint_classes=classes,endpoints=eps,bbox=[min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)]))
rows.sort(key=lambda x:-x['column_crossing_weight']);cap=10*sum(G.TRACK_DERATE/p for n,(di,p)in D.extra['tech'].items()if di.upper().startswith('V')and 2<=G._layer_idx(n)<=7)
out=dict(scope='exact attribution of already-computed single DATA model new hotcut; no secondplacement/capacitysweep/CAD',x_window_um=[x0,x1],cut_y_um=ycut,weighted_crossings=total,capacity=cap,util=total/cap,net_count=len(rows),weighted_driver_roles=dict(weights),top_driver_cells=drivers.most_common(20),top_native_endpoint_witnesses=rows[:20]);(R/'new_hot_cut_attribution.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items()if k!='top_native_endpoint_witnesses'})
