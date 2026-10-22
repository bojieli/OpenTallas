import importlib.util,json
from pathlib import Path
root=Path.cwd()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
T=load('fixture',root/'paired3/base/tools/ref_tile/tests/test_ot_rst_copies.py')
mods={s:load(s,root/f'paired3/{s}/physical/common_flow/ot_rst_copies.py') for s in ('base','cand')}
t=T.T(); cases={
 'supported_and2':t.leaf_nl(),
 'undriven_output':t.leaf_nl(leaf_cells={}),
 'combinational_cycle':t.leaf_nl(leaf_cells={'u':{'type':'$not','connections':{'A':[4],'Y':[4]}}}),
 'x_input':t.leaf_nl(leaf_cells={'u':{'type':'$and','connections':{'A':[2],'B':['x'],'Y':[4]}}}),
 'multiple_drivers':t.leaf_nl(leaf_cells={'u':{'type':'$and','connections':{'A':[2],'B':[3],'Y':[4]}},'v':{'type':'$not','connections':{'A':[2],'Y':[4]}}}),
 'pmux_multihot':t.leaf_nl(leaf_cells={'u':{'type':'$pmux','connections':{'A':['0'],'B':['0','1'],'S':['1','1'],'Y':[4]}}}),
 'bmux_out_of_range':t.leaf_nl(leaf_cells={'u':{'type':'$bmux','connections':{'A':['0'],'B':['1'],'Y':[4]}}}),
 'shiftx_out_of_range':t.leaf_nl(leaf_cells={'u':{'type':'$shiftx','connections':{'A':['0'],'B':['1'],'Y':[4]}}}),
}
x=t.leaf_nl(leaf_cells={});x['modules']['ot_kvpc5_and2']['ports']['y']['bits']=['x'];cases['x_output']=x
result={}
for name,nl in cases.items():
 row={}
 for side,m in mods.items():
  _,rs=m.analyse(nl,100,m.DEFAULT_RE);r=next(x for x in rs if x['family']=='u_m.hgo_qv')
  row[side]={k:r[k] for k in ('status','moves','leaf_equiv')}
 assert row['base']['status']=='OK' and row['base']['moves']==300
 if name=='supported_and2': assert row['cand']==row['base']
 else: assert row['cand']['status'].startswith('REFUSED') and row['cand']['moves']==0
 result[name]=row
Path('negative_compare.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
