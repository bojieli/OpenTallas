import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import geom_rules as g

class ClockTransportContract(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.k=Path(self.tmp.name)
  self.arc=dict(source='ft_ck_i_0',sink='ft_ck_o_0',kind='clock',role='tree_node',master='BUF',rect_um=[1,2,3,4],cells=[dict(name='island')])
  self.D=SimpleNamespace(pins=[dict(name='ft_ck_i_0',k=1,io='INPUT'),dict(name='ft_ck_o_0',k=2,io='OUTPUT')],cells={3:('B','BUF',1,2,3,4,'island')},pin_net={1:0,2:1},nets=[('SIGNAL',('p',1,False),[('i',3,False)]),('SIGNAL',('i',3,False),[('p',2,False)])])
  self.write()
 def tearDown(self):self.tmp.cleanup()
 def write(self,interface=None):
  (self.k/'island_ft.json').write_text(json.dumps(dict(arcs=[self.arc])))
  (self.k/'ft_interface.json').write_text(json.dumps(dict(arcs=[self.arc] if interface is None else interface)))
 def check(self):return g.declared_clock_transport_pins(self.D,self.k)
 def test_exact_dedicated_buffer(self):self.assertEqual(self.check(),{'ft_ck_i_0','ft_ck_o_0'})
 def test_unknown_contract_pair(self):self.write([]);self.assertFalse(self.check())
 def test_wrong_declared_kind(self):self.arc['kind']='data';self.write();self.assertFalse(self.check())
 def test_stale_master(self):self.arc['master']='WRONG';self.write();self.assertFalse(self.check())
 def test_stale_location(self):self.arc['rect_um']=[9,2,3,4];self.write();self.assertFalse(self.check())
 def test_unrelated_or_shared_connectivity(self):self.D.nets[0][2].append(('i',4,False));self.assertFalse(self.check())
 def test_reversed_clock_connection(self):self.D.nets[0]=('SIGNAL',('p',2,False),[('i',3,False)]);self.assertFalse(self.check())
 def test_no_contract(self):(self.k/'island_ft.json').unlink();self.assertFalse(self.check())

if __name__=='__main__':unittest.main()
