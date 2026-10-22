import re
import dv_bind as D

def tree():
 return dict(depth={'block':50,'west':4,'east':6},net_clocks={'block':'ck_S','west':'ck_g0','east':'ck_g3'},
  endpoint_leaf={('a',True):'west',('b',True):'east'},verilog=[],place=[],summary=dict(stations=0,release_crossings=0,crossings=[],max_release_depth=50))

def test_opposite_body_ends_get_local_branches_and_same_safe_boot_epoch():
 rst=tree();master=D.RST_RLY['EW']
 a=D.reset_endpoint_leaf(rst,'block','ck_S',[0,0],master,'fwd_a',('a',True))
 b=D.reset_endpoint_leaf(rst,'block','ck_S',[10000,0],master,'fwd_b',('b',True))
 assert a!=b and rst['depth'][a]==rst['depth'][b]==50
 xy={'west':(0,0),'east':(10000,0)}
 xy.update({p['inst'][3:]:p['xy'] for p in rst['place']})
 for line in rst['verilog']:
  m=re.search(r'\.i\((\w+)\), \.o\((\w+)\)',line)
  if m:
   source,sink=m.groups()
   assert abs(xy[source][0]-xy[sink][0])+abs(xy[source][1]-xy[sink][1])<=405
 before=len(rst['verilog'])
 assert D.reset_endpoint_leaf(rst,'block','ck_S',[0,0],master,'fwd_a',('a',True))==a
 assert len(rst['verilog'])==before

def test_extending_a_local_boot_epoch_reuses_prefix_without_duplicate_cells():
 rst=tree();master=D.RST_RLY['EW']
 D.reset_endpoint_leaf(rst,'block','ck_S',[0,0],master,'fwd_a',('a',True))
 rst['depth']['later_block']=53;rst['net_clocks']['later_block']='ck_S'
 net=D.reset_endpoint_leaf(rst,'later_block','ck_S',[0,0],master,'fwd_a',('a',True))
 assert rst['depth'][net]==53
 names=[p['inst'] for p in rst['place']]
 assert len(names)==len(set(names))
