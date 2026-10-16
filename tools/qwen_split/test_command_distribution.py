import copy
from types import SimpleNamespace
import pytest
from qwen_split.command_distribution import apply,FIELDS,MASTER

def model():
 def inst(n,x,y):return SimpleNamespace(name=n,master='source',x=x,y=y,w=43.2,h=43.2,orient='R0',domain='stream_1p2')
 ii=[inst('res_train_issue',900,900)]+[inst(f'sink{i}',100+400*(i%2),100+200*(i//2))for i in range(6)]
 ss=[i.name for i in ii[1:]]
 bb=[('clk','clock_trunk',1,[('pll','o')]+[(i.name,'ck')for i in ii]),
     ('rst','reset',1,[('rstseq','o')]+[(i.name,'rst_n')for i in ii])]
 bb.extend((f'cmd_{p}','spine_local',n,[('res_train_issue',p)]+[(s,p)for s in ss])for p,n in FIELDS)
 return dict(insts=ii,buses=bb,die=dict(w=1500,h=1500)),ss

def test_exact_all_fields_paths_have_same_registered_depth_and_real_unique_outputs():
 m,ss=model();r=apply(m,ss)
 assert r['normal_logic_edges']==3
 assert len(r['nodes'])==7
 # Walk the graph independently from every destination field through real
 # b0/b1 registered outputs; all consumers must see the same source event.
 B={}
 for bid,cl,n,es in m['buses']:
  if cl in ('clock_trunk','reset'):continue
  assert len(es)==2
  assert es[1]not in B
  B[es[1]]=es[0]
 ages=[]
 for s in ss:
  for field,n in FIELDS:
   p=(s,field);depth=0;seen=set()
   while p[0]!='res_train_issue':
    assert p not in seen;seen.add(p)
    p=B[p]
    if p[0]=='res_train_issue':break
    assert p[1].startswith(('b0_','b1_'))
    p=(p[0],'a_'+field);depth+=1
   assert p==('res_train_issue',field)
   ages.append(depth)
 assert set(ages)=={3}
 forks={i.name for i in m['insts']if i.master==MASTER}
 for name,cl,n,es in m['buses']:
  if cl in ('clock_trunk','reset'):
   assert {(i,'ck'if cl=='clock_trunk'else'rst_n')for i in forks}<=set(es)
 for a in m['insts']:
  for b in m['insts']:
   if a.name>=b.name:continue
   assert not(a.x<b.x+b.w and a.x+a.w>b.x and a.y<b.y+b.h and a.y+a.h>b.y)

def test_fail_closed_on_lost_live_consumer_or_missing_root():
 for mutation in ('consumer','clock','width'):
  m,ss=model()
  if mutation=='consumer':m['buses'][2][3].append(('other_live_consumer','train_start'))
  if mutation=='clock':m['buses'][0]=(m['buses'][0][0],'clock_trunk',1,[('pll','o')])
  if mutation=='width':
   b,c,n,es=m['buses'][2];m['buses'][2]=(b,c,n+1,es)
  before=copy.deepcopy(m)
  with pytest.raises(ValueError):apply(m,ss)
  assert m==before

def test_eight_selector_consumers_use_distinct_actual_registered_output_ports():
 m,ss=model()
 for i in range(6,8):
  m['insts'].append(SimpleNamespace(name=f'sink{i}',master='source',x=100+400*(i%2),y=700,w=43.2,h=43.2,orient='R0',domain='stream_1p2'))
  ss.append(f'sink{i}')
 m['buses']=[b for b in m['buses']if b[1]in('clock_trunk','reset')]
 m['buses'].append(('upper_selector','tree_spine',26,[('res_train_issue','sel')]+[(s,'sel')for s in ss]))
 r=apply(m,ss,fielddefs=(('sel',26),),master='qfd_static_selector_fork26',source_file='rtl/qwen_split/qfd_static_selector_fork26.sv',prefix='selector')
 assert r['normal_logic_edges']==3 and len(r['nodes'])==7
 assert len(r['equal_groups']['selector_level_3'])==8
 assert 'selector'in m['distribution_trees'] and 'command_distribution'not in m
 assert len({b[3][0]for b in m['buses']if b[0].startswith('selector_leaf_')})==8
