"""Per-port roots of the actual regional LEP interface; legacy roots stay unchanged."""
import copy,re,unittest,json,tempfile
from unittest.mock import patch
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
   **{f'lo{i}.o':{'clock_port':'clk_a' if i<2 else 'clk_b'} for i in range(4)},
   **{f'li{i}.i':{'clock_port':'clk_a' if i<2 else 'clk_b'} for i in range(4)},'ri.o':{}},
   'port_clock_required':['lo0.o','lo2.o','li0.i','li2.i']},
   'legacy':{'module':'legacy','clk':'clk','clock_port':'legacy_override','ports':{'i.i':{},'o.o':{}}}},
   'rtl_widths':{'ot_s81sl_lep_mu_ab_regional':{'clk':1,'clk_a':1,'clk_b':1}},
   'instance_clock_ports':{'lep':{'clk':'ck_C','clk_a':'ck_A','clk_b':'ck_B'}},
   'clock_domains':{n:{'period_ps':833.333} for n in ['ck_C','ck_A','ck_B']}}
 def link(self,port,source=True):
  ends=[[0,port,0,0,'box'],[1,'i',100,0,'box']] if source else [[1,'o',100,0,'box'],[0,port,0,0,'box']]
  return dict(i='clock_probe',e=ends)
 def emitted(self,wrong=False,zero=False,forwarded=False):
  table=copy.deepcopy(self.table)
  table['landing_reset_stages']={'dsfd_dvland_276':2}
  blocks=[dict(name='lep',master='regional',group='clC',x=100,y=100,w=100,h=100),
          dict(name='other',master='legacy',group='clL',x=600,y=100,w=100,h=100)]
  links=[]
  for i in range(4):
   for outgoing in (True,False):
    port=('lo' if outgoing else 'li')+str(i)
    e=[[0,port,200,150,'box'],[1,('i' if outgoing else 'o')+str(i),600,150,'box']]
    if not outgoing:e.reverse()
    links.append(dict(i=port,e=e,b=276,c='unit'))
  links.append(dict(i='ri',e=[[0,'ri',200,150,'box'],[1,'ri',600,150,'box']],b=276,c='unit'))
  for master in table['masters'].values():master['rst']=['rs','low']
  for i in range(4):
   for direction in ('o','i'):
    key=('lo' if direction=='o' else 'li')+str(i)+'.'+direction
    table['masters']['regional']['ports'][key].update(port=('lo' if direction=='o' else 'li')+str(i),lane=276,land=direction=='i')
    table['masters']['legacy']['ports'][('i' if direction=='o' else 'o')+str(i)+'.'+('i' if direction=='o' else 'o')]={'port':('i' if direction=='o' else 'o')+str(i),'lane':276,'land':direction=='o'}
  table['masters']['regional']['ports']['ri.o'].update(port='ri',lane=276,clock_port='clk')
  table['masters']['legacy']['ports']['ri.i']={'port':'ri','lane':276,'land':True}
  table['rtl_widths']['legacy']={}
  if forwarded:table['masters']['regional']['ports']['lo0.o']['ck']='forwarded'
  if zero:
   for i in range(4):
    table['masters']['legacy']['ports'][f'i{i}.i']['ck_in']=f'xk{i}'
  if wrong:table['instance_clock_ports']['lep']['clk_b']='ck_C'
  plan={'facts':{'die_um':[800,400],'cluster_pitch_um':400},'blocks':blocks,'links':links}
  chains={l['i']:([] if zero else [(400,150)]) for l in links};dirs={(n,0):'WE' for n in chains}
  # Fixed tiny reset topology exercises both calendar branches; emit itself builds
  # all port wires, forwarding gates, landing cells and calendar stations.
  reset=dict(verilog=[],depth={'rs0':2,'rs1':6},block_leaf={'lep':'rs0','other':'rs1'},
   block_parent={'lep':'rs0','other':'rs1'},block_pin={'lep':(200,150),'other':(600,150)},
   station_leaf={(n,0):'rs0' for n in chains},place=[],summary={'stations':0,'root_xy':[400,0]})
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);tp=root/'table.json';tp.write_text(json.dumps(table))
   with patch.object(D,'reset_tree',return_value=reset):D.emit(plan,root/'out',tp,dirs,chains,run_bind=False)
   return (root/'out/die.v').read_text()
 def test_production_emission_A_A_B_B_C(self):
  text=self.emitted()
  for i,root in enumerate(('ck_A','ck_A','ck_B','ck_B')):
   self.assertRegex(text,rf'fwd_lo{i} \(\.CLK\({root}\)')
   self.assertRegex(text,rf'ld_li{i} .*\.ck\({root}\)')
  self.assertRegex(text,r'fwd_ri \(\.CLK\(ck_C\)')
  calendars=[line for line in text.splitlines() if '// gate calendar' in line]
  self.assertTrue(any('.ck(ck_A)' in line for line in calendars))
  self.assertTrue(any('.ck(ck_B)' in line for line in calendars))
  self.assertTrue(any('.ck(ck_C)' in line for line in calendars))
 def test_production_zero_hop_forwarding_roots(self):
  text=self.emitted(zero=True)
  for i,root in enumerate(('ck_A','ck_A','ck_B','ck_B')):
   self.assertRegex(text,rf'fwdi_lo{i} \(\.A\({root}\)')
 def test_production_forwarded_and_explicit_clock_refused(self):
  with self.assertRaisesRegex(ValueError,'forwarded-clock output is unsupported'):self.emitted(forwarded=True)
 def test_production_emission_wrong_B_mapping_refused(self):
  with self.assertRaisesRegex(ValueError,'exact distinct'):self.emitted(wrong=True)
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
