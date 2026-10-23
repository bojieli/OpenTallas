import ast, math, os, json
from pathlib import Path

def build(path,variant):
 ns=dict(math=math,os=os,RST_W=12.96,RST_H=6.48,RST_GAP_UM=2.16,RST_NET_UM=380.,RST_PAD_GAP_UM=2.16,RST_REP='qfd_rst_rep',RST_PAD='qfd_rst_rep_p8',RST_PAD64='qfd_rst_rep_p62',RST_PAD64_VARIANT=variant,RST_PAD_LV=5,RST_PITCH_UM=220.,RST_LEAF_UM=200.,_rst_pad_cluster=True,_rst_pad_street=True)
 defs=[n for n in ast.parse(Path(path).read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ('_rst_frame','_rst_cycles','_hp','_RstOcc','_rst_tree_build')]
 exec(compile(ast.Module(body=defs,type_ignores=[]),path,'exec'),ns)
 nets=[dict(bid='rst_long',dom='field',drv=('a','q',(80.,100.)),sinks=[('s1','rst',(11600.,1500.)),('s2','rst',(11500.,200.))]),dict(bid='rst_short',dom='field',drv=('b','q',(100.,800.)),sinks=[('s3','rst',(600.,900.))])]
 return ns['_rst_tree_build'](nets,[],12000.,1800.,2.16,2.16)
a=build('old.py','');b=build('new.py','')
for x in b[2].values(): x.pop('pad_p62')
assert a==b,'default exact geometry/master/edge tuple changed'
for v in ('a','b'):
 c=build('new.py',v)
 assert not c[3],c[3]
 assert any(x['pad_p62'] for x in c[2].values())
 for key,row in c[2].items():
  assert row['depth_cycles']==a[2][key]['depth_cycles'],(key,row,a[2][key])
  assert row['max_net_um']<=380,row
 assert len(c[0])<len(a[0]),(len(c[0]),len(a[0]))
 print(json.dumps(dict(variant=v,cells=len(c[0]),original_cells=len(a[0]),stats=c[2]),sort_keys=True))
print('PASS exact default and both compact frames preserve every sink release edge and reach')
