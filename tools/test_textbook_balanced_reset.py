"""Explicit balanced-profile proof; no generic reset threshold changes."""
import copy
import textbook_lint as T

def graph(first=3,last=6,loads=10):
 s='module top(clk,rst_n,d); input clk,rst_n,d;\n'
 s+='wire '+','.join([f'f{i}' for i in range(first)]+[f'fn{i}' for i in range(first)]+[f'l{i}' for i in range(last)]+[f'ln{i}' for i in range(last)]+[f'x{i}_{j}' for i in range(last) for j in range(loads)])+';\n'
 for i in range(first):s+=f'DFFHQNx1_ASAP7_75t_R a{i}(.CLK(clk),.D(rst_n),.QN(fn{i}));\nINVx1_ASAP7_75t_R ai{i}(.A(fn{i}),.Y(f{i}));\n'
 for i in range(last):
  s+=f'DFFHQNx1_ASAP7_75t_R b{i}(.CLK(clk),.D(f{i%first}),.QN(ln{i}));\nINVx1_ASAP7_75t_R bi{i}(.A(ln{i}),.Y(l{i}));\n'
  for j in range(loads):s+=f'DFFHQNx1_ASAP7_75t_R c{i}_{j}(.CLK(clk),.D(l{i}),.QN(x{i}_{j}));\n'
 s+='endmodule'
 return T.flatten(T.parse_verilog(s),None)[0]
def profile(first=3,last=6):
 return dict(schema='opentallas.ref_tile.reset_landing.v1',top='top',enable=True,stages=2,clock='clk',first_copies=dict(rst_n=first),copies=dict(rst_n=last))
def proof(g,p=None):
 a=T.build(g,None);return T.balanced_reset_proof(g,a,'rst_n',g.ports['rst_n'][1],p or profile())
def test_exact():
 r=proof(graph());assert r['pass'] and r['edges']==2 and r['first_max_loads']==2 and r['final_max_loads']==10

def test_missing_and_stale_profile():
 g=graph()
 for p in [dict(schema='bad'),profile(4,6),profile(3,7),dict(profile(),stages=3),dict(profile(),clock='foreign')]:assert not proof(g,p)['pass']

def test_crossclock_and_tie():
 for cell,pin,n in [('a1','CLK',1),('b1','CLK',1),('b1','D',0),('a1','D',0)]:
  g=graph();ci=next(i for i,c in enumerate(g.cells) if c[1]==cell);g.cells[ci][2][pin]=[n]
  assert not proof(g)['pass']

def test_first_and_final_overload():
 assert not proof(graph(first=1,last=33),profile(1,33))['pass']
 assert not proof(graph(loads=33))['pass']

def test_no_profile_legacy_refusal_unchanged():
 g=graph();r=T.analyse(g,None,dict(T.THRESHOLDS));assert 'reset_landing' in r['refuse']
 r=T.analyse(g,None,dict(T.THRESHOLDS,_balanced_reset_profile=profile()));assert 'reset_landing' not in r['refuse']

def test_async_or_extra_root_dependency_refuses():
 g=graph();ci=next(i for i,c in enumerate(g.cells) if c[1]=='a1');g.cells[ci][2]['RESETN']=[g.ports['rst_n'][1]]
 assert not proof(g)['pass']
