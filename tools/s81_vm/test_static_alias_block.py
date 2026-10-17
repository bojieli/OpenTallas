import unittest
from static_alias_block import evaluate

def v(name,w=1):return dict(type='VARREF',varp=name,w=w)
def c(value,w=32):return dict(type='CONST',v=value,w=w)
def sel(base,offset,w=1):return dict(type='SEL',fromp=[base],lsbp=[offset],widthConst=w,w=w)
def assign(lhs,rhs):return dict(type='ASSIGN',lhsp=[lhs],rhsp=[rhs])
def add(a,b):return dict(type='ADD',lhsp=[a],rhsp=[b],w=32)
class StaticAliases(unittest.TestCase):
 def evaluate(self,stmt):return evaluate(dict(type='ALWAYS',stmtsp=stmt),'p',{},lambda n:n['w'],lambda n:n['v'])
 def test_overrides_preserve_last_blocking_assignment(self):
  result=self.evaluate([assign(v('out',2),c(0,2)),assign(sel(v('out',2),c(0)),v('in'))])
  self.assertEqual(result[('p','out',0)],('p','in',0));self.assertEqual(result[('p','out',1)],('CONST','0',0))
 def test_static_loop_wires_each_distinct_bit(self):
  block=dict(type='BEGIN',declsp=[dict(type='VAR',addr='i',dtypeName='integer')],stmtsp=[assign(v('i',32),c(0)),dict(type='LOOP',stmtsp=[dict(type='LOOPTEST',condp=[dict(type='GTS',lhsp=[c(2)],rhsp=[v('i',32)])]),assign(sel(v('out',2),v('i',32)),sel(v('in',2),v('i',32))),assign(v('i',32),add(v('i',32),c(1)))])])
  self.assertEqual(self.evaluate([block]),{('p','out',i):('p','in',i)for i in range(2)})
 def test_runtime_control_fails_closed(self):
  condition=dict(type='COND',condp=[v('runtime')],thenp=[c(0)],elsep=[c(1)],w=1)
  with self.assertRaisesRegex(ValueError,'Non-static'):self.evaluate([assign(v('out'),condition)])
if __name__=='__main__':unittest.main()
