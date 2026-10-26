import json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'base/tools/ref_tile/tests'))
import test_ot_rst_copies as T
rows={}
def check(name,nl):
 _,records=T.RS.analyse(nl,100,T.RS.DEFAULT_RE)
 r=next(x for x in records if x['family']=='u_m.hgo_qv')
 rows[name]={'status':r['status'],'moves':r['moves'],'leaf_equiv':r['leaf_equiv']}
 assert r['status']=='OK' and r['moves']==300,(name,r)
t=T.T()
check('actual_supported_and2',t.leaf_nl())
check('undriven_output',t.leaf_nl(leaf_cells={}))
check('combinational_cycle',t.leaf_nl(leaf_cells={'loop':{'type':'$not','connections':{'A':[4],'Y':[4]}}}))
x=t.leaf_nl(leaf_cells={});x['modules']['ot_kvpc5_and2']['ports']['y']['bits']=['x'];check('x_output',x)
check('multiple_drivers',t.leaf_nl(leaf_cells={'a':{'type':'$and','connections':{'A':[2],'B':[3],'Y':[4]}},'b':{'type':'$not','connections':{'A':[2],'Y':[4]}}}))
Path('repro.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
