"""The production budget helper preserves rows and bounds grid geometry work."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

def helper(namespace):
 tree=ast.parse(Path(__file__).with_name('gen_phys.py').read_text())
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='budget_tap_rows')
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(Path(__file__).with_name('gen_phys.py')),'exec'),namespace)
 return namespace['budget_tap_rows']

class BudgetTapsTest(unittest.TestCase):
 def check(self,density,grid,taps):
  calls=[]
  def make_grid(P,tn):calls.append(tn);return grid
  fake=SimpleNamespace(_grid_taps=make_grid,tap_grid=lambda P,tn:taps)
  P=SimpleNamespace(types={'hub':{'density':density}})
  fn=helper({'S':fake,'_density':lambda t:t['density']})
  count,rows=fn(P,'hub')
  expected=[dict(name=n,xy=[x,y],kind='density'if density else 'grid'if i<len(grid)else'sinks')for i,(n,x,y)in enumerate(taps)]
  self.assertEqual(rows,expected);self.assertEqual(count,0 if density else len(grid))
  self.assertEqual(len(calls),0 if density else 1)
 def test_large_grid_avoids_per_output_geometry(self):
  taps=[('clk_t'+str(i),float(i),0.)for i in range(1000)]
  self.check(False,taps[:900],taps)
 def test_density_never_constructs_r4_grid(self):self.check(True,[('clk',0.,0.)],[('clk',1.,2.),('clk_t1',3.,4.)])
 def test_empty_grid_classifies_added_taps(self):self.check(False,[],[('clk',1.,2.)])
 def test_exact_grid_with_no_sink_rows(self):self.check(False,[('clk',1.,2.)],[('clk',1.,2.)])

if __name__=='__main__':unittest.main()
