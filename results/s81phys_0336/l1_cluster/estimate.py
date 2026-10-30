import inspect,json,sys,math,re
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));import geom_rules as G
D=G.Design(P/'geom.tsv');src=inspect.getsource(G.r2r_metrics).replace('best, arg, n_gt = 0.0, None, 0','details=[]; best, arg, n_gt = 0.0, None, 0').replace('        if mx > R2R_MAX:','        details.append((cap,mx,src))\n        if mx > R2R_MAX:').replace('return dict(r2r_memory_instances','return dict(details=details,r2r_memory_instances');n=dict(G.__dict__);exec(src,n);base=n['r2r_metrics'](D);bad=[t for t in base['details'] if t[1]>405];print('baseline',base['r2r_max'],len(bad));print('bad groups',sorted({D.cells[c][6].split('\\')[0] for c,_,_ in bad}))
positions=[]
for i,(cid,dist,launch) in enumerate(sorted(bad,key=lambda x:D.cells[x[0]][6])):
 c=D.cells[cid];old=G.ctr(c);x,y=old
 if c[6].startswith(('ct_b','fault')): x+=70
 elif c[6].startswith('sa_r'): y+=65
 elif c[6].startswith('ra'): y+=40; x-=20
 elif c[6].startswith('we'): x-=25
 else: raise AssertionError(c[6])
 w=c[4]-c[2];h=c[5]-c[3];w=c[4]-c[2];h=c[5]-c[3]
 D.cells[cid]=c[:2]+(x-w/2,y-h/2,x+w/2,y+h/2,c[6]);positions.append(dict(name=c[6],old=old,new=[x,y],original_worst_um=dist))
res=n['r2r_metrics'](D);base.pop('details');res.pop('details');pm=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT))
out=dict(scope='ANALYTIC PLACEMENT ESTIMATE ONLY; no ODB change; no physical legality claim; all external pins unchanged',baseline=base,candidate=res,pin_reg={k:pm[k]for k in ['pin_reg_max','pin_reg_p90','pin_reg_worst']},moved_control_flops=len(positions),added_flops=0,added_cycles=0,moves=positions)
(P/'estimate3.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k!='moves'},indent=2))
