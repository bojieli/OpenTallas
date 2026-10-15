import unittest
from static_vm_engine import sparse_arm_arg,sparse_check_arg,validate
BASES=[6000,6321,6642,6963,7312,7633,7954]
def commands():
 return [dict(cycle=10+s,kind='sparse_arm',slot=s,base_row=b,nrows=80) for s,b in enumerate(BASES)]+[dict(cycle=200+s,kind='sparse_check',slot=s) for s in range(7)]
class SparseVm(unittest.TestCase):
 def test_abi(self):
  for s,b in enumerate(BASES):
   a=sparse_arm_arg(s,b,80)
   self.assertEqual(a>>21,5 if s<4 else 7)
   self.assertEqual((a>>19)&3,s%4)
   self.assertEqual(((a>>9)&1023)*16+((a>>7)&3),b)
   self.assertEqual(a&127,79)
   self.assertEqual(sparse_check_arg(s)&0x7ffff,0x7ffff)
  for args in [(8,6000,80),(0,6004,80),(0,16368,80),(0,6000,129)]:
   with self.assertRaises(ValueError):sparse_arm_arg(*args)
 def test_seven_exact_vectors_holes(self):
  actual=[(30+k,b+4*k)for b in BASES for k in range(80)]
  self.assertEqual(len({r for _,r in actual}),560)
  holes=[(150,b+k)for b in BASES for k in (1,2,3)]
  done,errors=validate(commands(),actual+holes,holes)
  self.assertEqual(errors,[])
  self.assertTrue(all(done[i]==c['cycle']+6 for i,c in enumerate(commands())))
  self.assertTrue(any('[1]'in e for e in validate(commands(),actual+[(151,6000)])[1]))
  self.assertTrue(any('[7]'in e for e in validate(commands(),actual,[(151,6000)])[1]))
  actual[30]=(60,6121)
  self.assertTrue(any('[0]'in e for e in validate(commands(),actual)[1]))
 def test_real_intersections(self):
  a=dict(cycle=1,kind='sparse_arm',slot=0,base_row=6000,nrows=2)
  b=dict(cycle=2,kind='sparse_arm',slot=1,base_row=6001,nrows=2)
  e=validate([a,b])[1];self.assertFalse(any('[5]'in x for x in e))
  c=dict(cycle=3,kind='arm',slot=2,client='su',base_row=6000,nrows=1)
  self.assertTrue(any('[5]'in x for x in validate([a,b,c])[1]))
  b['base_row']=6000
  self.assertTrue(any('[5]'in x for x in validate([a,b])[1]))
if __name__=='__main__':unittest.main()
