"""Bounded geometry check: exact default and unchanged equalisation stages under pad spacing."""
import ast,math,os,json,sys
from pathlib import Path
assert len(sys.argv) == 3, 'usage: test_reset_pad_gap.py OLD_SOURCE NEW_SOURCE'
old,new=map(Path,sys.argv[1:])
def build(path,gap):
 ns=dict(math=math,os=os,RST_W=12.96,RST_H=6.48,RST_GAP_UM=2.16,RST_NET_UM=380.,RST_PAD_GAP_UM=gap,RST_REP='qfd_rst_rep',RST_PAD='qfd_rst_rep_p8',RST_PAD_LV=5,RST_PITCH_UM=220.,RST_LEAF_UM=200.,_rst_pad_cluster=True,_rst_pad_street=False,RST_PAD64='qfd_rst_rep_p62',RST_PAD64_VARIANT='',RST_PAD64_MIXED=False)
 tree=ast.parse(path.read_text()); defs=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ('_rst_frame','_rst_cycles','_hp','_RstOcc','_rst_tree_build')]
 exec(compile(ast.Module(body=defs,type_ignores=[]),str(path),'exec'),ns)
 nets=[dict(bid='rst_long',dom='field',drv=('a','q',(80.,100.)),sinks=[('s1','rst',(2600.,1500.)),('s2','rst',(2500.,200.))]),dict(bid='rst_short',dom='field',drv=('b','q',(100.,800.)),sinks=[('s3','rst',(600.,900.))])]
 return ns['_rst_tree_build'](nets,[],3000.,1800.,2.16,2.16)
a=build(old,2.16)
b=build(new,2.16)
for x in b[2].values():x.pop('pad_gap_um');x.pop('pad_p62',None)
assert a==b,'default changed'
for gap in (8.64,12.96):
 c=build(new,gap)
 assert not c[3],c[3]
 for key,stats in c[2].items():
  for f in ('sinks','repeaters','pad_rep','pad_p8','depth_cycles','levels','nets'):
   assert stats[f]==a[2][key][f],(gap,key,f)
  assert stats['max_net_um']<=380,stats
 assert c[0]!=a[0],'spacing did not move pads'
 print('PASS gap',gap,'cells',len(c[0]),'depths',{k:v['depth_cycles'] for k,v in c[2].items()})
print('PASS default exact tuple and gap variants preserve every master/stage/net/depth count')
