"""Per-port roots of the actual regional LEP interface; legacy roots stay unchanged."""
import copy,re,unittest
from pathlib import Path
import dv_bind as D

class PortClockBind(unittest.TestCase):
 def setUp(self):
  source=(Path(__file__).resolve().parents[2]/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_lep_mu_ab_regional.sv').read_text()
  header=source.split(');',1)[0]
  for clock in ('clk','clk_a','clk_b'):
   self.assertRegex(header,r'input\s+wire\s+'+clock+r'\s*[,\n]')
  self.blocks=[dict(name='lep',master='regional'),dict(name='other',master='legacy')]
  self.regions={'lep':'C','other':'legacy'}
  self.table={'masters':{'regional':{'module':'ot_s81sl_lep_mu_ab_regional','clk':'clk',
   'clock_ports':['clk','clk_a','clk_b'],'ports':{
   'lo0.o':{'clock_port':'clk_a'},'lo2.o':{'clock_port':'clk_b'},
   'li0.i':{'clock_port':'clk_a'},'li2.i':{'clock_port':'clk_b'},'ri.o':{}},
   'port_clock_required':['lo0.o','lo2.o','li0.i','li2.i']},
   'legacy':{'module':'legacy','clk':'clk','clock_port':'legacy_override','ports':{'i.i':{},'o.o':{}}}},
   'rtl_widths':{'ot_s81sl_lep_mu_ab_regional':{'clk':1,'clk_a':1,'clk_b':1}},
   'instance_clock_ports':{'lep':{'clk':'ck_C','clk_a':'ck_A','clk_b':'ck_B'}},
   'clock_domains':{n:{'period_ps':833.333} for n in ['ck_C','ck_A','ck_B']}}
 def link(self,port,source=True):
  ends=[[0,port,0,0,'box'],[1,'i',100,0,'box']] if source else [[1,'o',100,0,'box'],[0,port,0,0,'box']]
  return dict(i='clock_probe',e=ends)
 def test_actual_A_B_source_and_receiver_roots(self):
  for source,names in [(True,('lo0','lo2')),(False,('li0','li2'))]:
   for name,net in zip(names,['ck_A','ck_B']):
    self.assertEqual(D.endpoint_clock(self.table,self.blocks,self.regions,self.link(name,source),source),net)
  self.assertEqual(D.endpoint_clock(self.table,self.blocks,self.regions,self.link('ri'),True),'ck_C')
 def test_default_keeps_legacy_regional_rule(self):
  self.assertEqual(D.endpoint_clock(self.table,self.blocks,self.regions,self.link('li0',False),True),'ck_legacy')
 def test_unsupported_actual_output_is_not_a_clock(self):
  self.table['masters']['regional']['ports']['lo0.o']['clock_port']='lo0_v'
  with self.assertRaisesRegex(ValueError,'unsupported clock_port'):D.endpoint_clock(self.table,self.blocks,self.regions,self.link('lo0'),True)
 def test_required_port_cannot_fall_back_to_C(self):
  del self.table['masters']['regional']['ports']['lo0.o']['clock_port']
  with self.assertRaisesRegex(ValueError,'explicit clock_port required'):D.endpoint_clock(self.table,self.blocks,self.regions,self.link('lo0'),True)
 def test_missing_instance_mapping_is_refused(self):
  del self.table['instance_clock_ports']['lep']
  with self.assertRaisesRegex(ValueError,'explicit distinct'):D.endpoint_clock(self.table,self.blocks,self.regions,self.link('lo0'),True)
 def test_wide_clock_is_refused(self):
  self.table['rtl_widths']['ot_s81sl_lep_mu_ab_regional']['clk_a']=2
  with self.assertRaisesRegex(ValueError,'declared scalar'):D.endpoint_clock(self.table,self.blocks,self.regions,self.link('lo0'),True)
 def test_tied_A_C_clock_mapping_is_refused(self):
  self.table['instance_clock_ports']['lep']['clk_a']='ck_C'
  with self.assertRaisesRegex(ValueError,'exact distinct'):D.endpoint_clock(self.table,self.blocks,self.regions,self.link('lo0'),True)
if __name__=='__main__':unittest.main()
