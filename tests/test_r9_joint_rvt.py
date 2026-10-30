"""Three tied late paths need coordinated improvement; full FF/slew can veto it."""
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'results/core_lat_r9_1026/joint_rvt.py'
s=importlib.util.spec_from_file_location('joint_rvt',p);J=importlib.util.module_from_spec(s);s.loader.exec_module(J)
TT=dict(e=0.,a=10.,b=9.975,c=9.971);FF=dict(e=0.,a=8.,b=7.975,c=7.971)
PAR=dict(root=None,e='root',a='root',b='root',c='root');CELLS={n:'small'for n in PAR}
def evaluate(mode='normal'):
 def f(changes,need_slew):
  # Each selected late driver is faster, but added pin load also delays the
  # shared upstream driver. Evaluate every endpoint, including the early one.
  load=.1*len(changes);t={k:v+load-(2 if k in changes else 0)for k,v in TT.items()};q={k:v+load-(1.6 if k in changes else 0)for k,v in FF.items()}
  if mode=='FF'and len(changes)>1:q['c']+=8
  sl=dict(TT_in=30.,TT_out=50.,FF_in=20.,FF_out=40.)
  if mode in sl and len(changes)>1:sl[mode]=80.1
  if mode=='nan'and len(changes)>1:sl['TT_in']=float('nan')
  return t,q,sl
 return f
class Joint(unittest.TestCase):
 def test_three_path_plateau_escapes_without_reducing_gain(self):
  f=evaluate();old=J.objective(TT,FF)
  self.assertTrue(all(J.objective(*f({n:'large'},False)[:2])>=old-J.GAIN for n in 'abc'))
  q=J.propose(TT,FF,PAR,CELLS,['small','large'],f)
  self.assertEqual(set(q['assignments']),set('abc'));self.assertLess(q['key'][0],old-J.GAIN)
 def test_full_ff_can_reject(self):self.assertIsNone(J.propose(TT,FF,PAR,CELLS,['small','large'],evaluate('FF')))
 def test_every_corner_input_output_slew_can_reject(self):
  for key in ('TT_in','TT_out','FF_in','FF_out','nan'):
   with self.subTest(key=key):self.assertIsNone(J.propose(TT,FF,PAR,CELLS,['small','large'],evaluate(key)))
 def test_over_three_ties_refused(self):
  t=dict(TT,d=9.99);f=dict(FF,d=7.99)
  self.assertIsNone(J.propose(t,f,dict(PAR,d='root'),dict(CELLS,d='small'),['small','large'],evaluate()))
if __name__=='__main__':unittest.main()
