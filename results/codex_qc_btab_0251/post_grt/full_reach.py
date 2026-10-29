import sys,inspect,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import geom_rules as R
D=R.Design(sys.argv[1]); memories=[]
for k,c in list(D.cells.items()):
 if c[0]=='M':
  assert c[1]=='ot_sram_1r1w_128x256_m1_r2c2',c
  D.cells[k]=('S',)+c[1:];memories.append(c[6])
assert len(memories)==4
src=inspect.getsource(R.r2r_metrics).replace('def r2r_metrics(D):','def btab_full_bbox_reach(D):')
a='''        x, y = ctr(c)
        u, v = x + y, x - y'''
b='''        u0,u1,v0,v1 = c[2]+c[3], c[4]+c[5], c[2]-c[5], c[4]-c[3]'''
assert src.count(a)==1;src=src.replace(a,b)
src=src.replace('(u, u, v, v, cid, cid, cid, cid)','(u0, u1, v0, v1, cid, cid, cid, cid)').replace('merge(s[1], u, u, v, v, cid, cid, cid, cid)','merge(s[1], u0, u1, v0, v1, cid, cid, cid, cid)')
a='''        x, y = ctr(D.cells[cap])
        u, v = x + y, x - y'''
b='''        c = D.cells[cap]
        u0,u1,v0,v1 = c[2]+c[3], c[4]+c[5], c[2]-c[5], c[4]-c[3]'''
assert src.count(a)==1;src=src.replace(a,b).replace('((u - e[0], e[4]), (e[1] - u, e[5]), (v - e[2], e[6]), (e[3] - v, e[7]))','((u1 - e[0], e[4]), (e[1] - u0, e[5]), (v1 - e[2], e[6]), (e[3] - v0, e[7]))')
exec(src,R.__dict__)
x=dict(scope='Conservative complete registered-hop bbox pin bound; all std sequential +4known synchronous SRAM macros, every combinational data/reset path,clock pins excluded',source=sys.argv[1],memory_names=memories,centroid_macro_inclusive=R.r2r_metrics(D),conservative_all_pin_bbox=R.btab_full_bbox_reach(D))
print(json.dumps(x,indent=1))
