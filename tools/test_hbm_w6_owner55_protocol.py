import copy, unittest
import hbm_w6_owner55_protocol as P
OWNER=(127<<39)|(5<<36)|(0xfedcba98<<4)|15
class ProtocolTests(unittest.TestCase):
 def setUp(self):
  self.rows=[]
  for i,k in enumerate(P.ORDER):
   r=dict(event=k,edge=0 if i<3 else 2*(i-2),owner=OWNER,slot=511)
   if k=='drain_response':r.update(has_owner=True,reset_scope=False,levels=[True]*9)
   self.rows.append(r)
 def verify(self,r=None):return P.verify(self.rows if r is None else r,expected_owner=OWNER,expected_slot=511)
 def test_complete(self):self.assertTrue(self.verify()['numerical_retirement'])
 def test_field_aliases(self):
  for bit in [39,36,4,0]:
   with self.subTest(bit=bit):
    r=copy.deepcopy(self.rows);r[4]['owner']^=1<<bit
    with self.assertRaises(ValueError):self.verify(r)
  r=copy.deepcopy(self.rows);r[4]['slot']^=1
  with self.assertRaises(ValueError):self.verify(r)
 def test_duplicate_ACK(self):
  with self.assertRaises(ValueError):self.verify(self.rows[:5]+[self.rows[4]]+self.rows[5:])
 def test_missing_or_reversed_consumer(self):
  with self.assertRaises(ValueError):self.verify(self.rows[:6]+self.rows[7:])
  r=copy.deepcopy(self.rows);r[6],r[7]=r[7],r[6]
  with self.assertRaises(ValueError):self.verify(r)
 def test_one_copy_missing(self):
  with self.assertRaises(ValueError):self.verify(self.rows[:2]+self.rows[3:])
 def test_late_mirror(self):
  r=copy.deepcopy(self.rows);r[2]['edge']=1
  with self.assertRaises(ValueError):self.verify(r)
 def test_same_edge_ACK(self):
  r=copy.deepcopy(self.rows);r[3]['edge']=0
  with self.assertRaises(ValueError):self.verify(r)
 def test_each_debt_blocks(self):
  for i in range(9):
   with self.subTest(debt=i):
    r=copy.deepcopy(self.rows);r[-2]['levels'][i]=False
    with self.assertRaises(ValueError):self.verify(r)
 def reset_trace(self):
  r=copy.deepcopy(self.rows[:4]);r.append(dict(event='runtime_reset',edge=3,owner=OWNER,slot=511))
  for i,k in enumerate(('RF_reset_abort','reset_drain_request','reset_drain_response','reset_release')):
   t=dict(event=k,edge=4+i,owner=OWNER,slot=511)
   if k=='reset_drain_response':t.update(has_owner=True,reset_scope=True,levels=[True]*9)
   r.append(t)
  return r
 def test_reset_closes_without_retirement(self):
  r=self.verify(self.reset_trace());self.assertTrue(r['reset_aborted']);self.assertFalse(r['numerical_retirement'])
 def test_old_ACK_after_reset(self):
  r=self.reset_trace();r[5]=copy.deepcopy(self.rows[4]);r[5]['edge']=4
  with self.assertRaises(ValueError):self.verify(r)
 def test_normal_drain_cannot_release_reset(self):
  r=self.reset_trace();r[-2]['reset_scope']=False
  with self.assertRaises(ValueError):self.verify(r)
 def test_stale_reset_scope_tuple(self):
  r=self.reset_trace();r[-2]['owner']^=1
  with self.assertRaises(ValueError):self.verify(r)
 def test_integer_debt_is_not_bool(self):
  r=copy.deepcopy(self.rows);r[-2]['levels']=[1]*9
  with self.assertRaises(ValueError):self.verify(r)
 def test_no_partial_PASS(self):
  with self.assertRaises(ValueError):self.verify(self.rows[:-1])
if __name__=='__main__':unittest.main()
