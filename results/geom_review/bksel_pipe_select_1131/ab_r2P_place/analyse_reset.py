from pathlib import Path
import json,sys,statistics
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'geometry_tools_main'))
import geom_rules as g
p=Path(__file__).resolve().parent;D=g.Design(p/'geom.tsv')
srcs=[cid for cid,c in D.cells.items() if c[6]==r'u_c.rst_s\[1\]$_DFF_PN0_'];pres=[cid for cid,c in D.cells.items() if c[6]==r'u_c.rst_s\[0\]$_DFF_PN0_'];assert len(srcs)==len(pres)==1
src=srcs[0];pred=pres[0];caps=set();seen=set();edges=[];stack=[src]
while stack:
 a=stack.pop()
 if a in seen:continue
 seen.add(a)
 for n in D.drives.get(a,[]):
  for s in D.nets[n][2]:
   if s[0]!='i' or s[2]:continue
   b=s[1];edges.append((a,b))
   if D.kind(b)=='S':caps.add(b)
   elif D.kind(b) in 'BLK':stack.append(b)
cs=sorted(caps);xy=lambda i:list(g.ctr(D.cells[i]));srcxy=xy(src)
md=lambda a,b:sum(abs(x-y) for x,y in zip(a,b))
records=[{'id':i,'name':D.cells[i][6],'xy':xy(i)} for i in cs]
def stats(items):
 xs=[z['xy'][0] for z in items];ys=[z['xy'][1] for z in items]
 return {'count':len(items),'bbox':[min(xs),min(ys),max(xs),max(ys)],'centroid':[statistics.mean(xs),statistics.mean(ys)],'median':[statistics.median(xs),statistics.median(ys)]} if items else {'count':0}
over=[z for z in records if md(srcxy,z['xy'])>405]
o={'source':{'id':src,'name':D.cells[src][6],'xy':srcxy,'status':D.extra['status'].get(src)},'predecessor':{'id':pred,'name':D.cells[pred][6],'xy':xy(pred),'status':D.extra['status'].get(pred)},'all_captures':stats(records),'over405':stats(over),'captures':records,'over405_names':[x['name'] for x in over],'comb_count':len(seen)-1,'tree_edges':len(edges),'original_r2r':g.r2r_metrics(D)}
(p/'reset_loads.json').write_text(json.dumps(o,indent=2)+'\n');print(json.dumps({k:v for k,v in o.items() if k not in ['captures','over405_names']},indent=2))
