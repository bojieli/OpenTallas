import inspect,json,sys,math,re,collections
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));import geom_rules as G
D=G.Design(P/'geom.tsv');src=inspect.getsource(G.r2r_metrics).replace('best, arg, n_gt = 0.0, None, 0','details=[]; best, arg, n_gt = 0.0, None, 0').replace('        if mx > R2R_MAX:','        details.append((cap,mx,src))\n        if mx > R2R_MAX:').replace('return dict(r2r_memory_instances','return dict(details=details,r2r_memory_instances');n=dict(G.__dict__);exec(src,n);base=n['r2r_metrics'](D);bad=[t for t in base['details']if t[1]>405];groups=collections.Counter((D.cells[s][6].split('.')[0],D.cells[c][6].split('.')[0])for c,_,s in bad);original=dict(D.cells);moves={};skipped=[]
def relocate(cid,dx):
 c=D.cells[cid];D.cells[cid]=c[:2]+(c[2]+dx,c[3],c[4]+dx,c[5],c[6]);moves[cid]=dict(name=c[6],old=G.ctr(original[cid]),new=G.ctr(D.cells[cid]))
for cap,dist,launch in bad:
 a=D.cells[launch];b=D.cells[cap]
 if '.s' not in a[6] or '.s' not in b[6] or a[6].split('.')[0]!=b[6].split('.')[0]:skipped.append((a[6],b[6],dist));continue
 ax,ay=G.ctr(a);bx,by=G.ctr(b);need=dist-395
 if abs(bx-ax)<need:skipped.append((a[6],b[6],dist));continue
 sign=1 if ax>bx else -1
 if need<=40:
  relocate(cap,sign*need/2);relocate(launch,-sign*need/2)
 else:relocate(cap,sign*need)
res=n['r2r_metrics'](D);base.pop('details');res.pop('details');pm=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT));out=dict(scope='One bounded analytic EXISTING relay FF rebalance; no ODBwrite/P&R; unchanged pins/RTL/cycles; cornerfacehook repair NOT applied; frozen partial N-face remains',baseline=base,candidate=res,bad_groups={str(k):v for k,v in groups.items()},original_gt435=sum(t[1]>435 for t in bad),pin_reg={k:pm[k]for k in ['pin_reg_max','pin_reg_p90','pin_reg_worst']},moved_flops=len(moves),skipped_nonrelay=skipped[:12],moves=list(moves.values()),outline_um=[345.6,302.4],partial_N=dict(pins=546,occupied_windows=11,total_windows=35,minimum_occupied_windows=18,min_pin_moves_needed=7),clock='W oldM4(.042,118.62), no legal internal family tree yet')
(P/'estimate.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k not in ['moves','skipped_nonrelay']},indent=2))
