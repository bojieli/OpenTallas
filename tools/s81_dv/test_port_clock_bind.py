"""Per-port roots of the actual regional LEP interface; legacy roots stay unchanged."""
import copy,re,unittest,json,tempfile
from unittest.mock import patch
from pathlib import Path
import dv_bind as D

class PortClockBind(unittest.TestCase):
 def setUp(self):
  source=(Path(__file__).resolve().parent/'fixtures/regional_lep_ports.svh').read_text()
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
 def emitted(self,wrong=False,zero=False,forwarded=False,prune=None,force_zero=False,quantized=False,kit_rl=None):
  table=copy.deepcopy(self.table)
  if kit_rl is not None:table['kit_reset_landing_stages']=kit_rl
  table.setdefault('clock_regions', {'mode':'logical'})
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
  if quantized:
   table['masters']['regional']['ports']['lo0.o']['lanes']=[{'split':[['lo0',0,0,237]]}]
   table['masters']['legacy']['ports']['i0.i']['lanes']=[{'split':[['i0',0,0,237]]}]
  if forwarded:table['masters']['regional']['ports']['lo0.o']['ck']='forwarded'
  if zero:
   for i in range(4):
    table['masters']['legacy']['ports'][f'i{i}.i']['ck_in']=f'xk{i}'
  if wrong:table['instance_clock_ports']['lep']['clk_b']='ck_C'
  plan={'facts':{'die_um':[800,400],'cluster_pitch_um':400},'blocks':blocks,'links':links}
  chains={l['i']:([] if zero else [(400,150)]) for l in links};dirs={(n,0):'WE' for n in chains}
  # Fixed tiny reset topology exercises both calendar branches; emit itself builds
  # all port wires, forwarding gates, landing cells and calendar stations.
  reset=dict(verilog=[],depth={'rs0':2,'rs1':6},net_clocks={'rs0':'ck_C','rs1':'ck_g0_0'},block_leaf={'lep':'rs0','other':'rs1'},
   block_parent={'lep':'rs0','other':'rs1'},block_pin={'lep':(200,150),'other':(600,150)},
   station_leaf={(n,0):'rs0' for n in chains},place=[],summary={'stations':0,'root_xy':[400,0], 'release_crossings':0, 'crossings':[],
    'max_release_depth':6, 'block_release_depth':{'lep':3,'other':7}})
  if prune is not None:
   table['prune_unused_reset_leaves']=prune
   reset['verilog']=[
    '  wire rs_9_0;', '  reset_relay st_rs_9_0 (.ck(ck_clC), .rs(rs0), .i(rs0), .o(rs_9_0));',
    '  wire rs_9_1;', '  reset_relay st_rs_9_1 (.ck(ck_clC), .rs(rs_9_0), .i(rs_9_0), .o(rs_9_1));',
    '  wire rs_9_2;', '  reset_relay st_rs_9_2 (.ck(ck_clC), .rs(rs0), .i(rs0), .o(rs_9_2));']
   reset['place']=[dict(inst=f'st_rs_9_{i}',master='reset_relay',orient='R0',xy=[100,100],kind='street') for i in range(3)]
   reset['summary']['stations']=3
   reset['block_leaf']['lep']='rs_9_2'
   reset['depth']['rs_9_2']=2
  self.last_reset=reset
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);tp=root/'table.json';tp.write_text(json.dumps(table))
   lp=None
   if force_zero:
    lp=root/'land.json';lp.write_text(json.dumps({'links':[{'link':l['i'],'E':2,'K':2,'D':4,'force_landing':True} for l in links]}))
   with patch.object(D,'reset_tree',return_value=reset):D.emit(plan,root/'out',tp,dirs,chains,run_bind=False,land_plan=lp)
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
 def test_zero_station_real_landing_uses_source_wire_and_gated_source_root(self):
  text=self.emitted(zero=True,force_zero=True)
  for i,root in enumerate(('ck_A','ck_A','ck_B','ck_B')):
   self.assertRegex(text,rf'dsfd_dvland_276 ld_lo{i} .*\.i\(w_lo{i}_src\)')
   self.assertRegex(text,rf'dsfd_dvland_276 ld_li{i} .*\.ck\({root}\)')
   self.assertRegex(text,rf'fwd_lo{i} \(\.CLK\({root}\)')
   self.assertIn(f'wire [0:0] nlo{i}_fck;',text)
 def test_explicit_xc_lane_identity_is_invariant_under_physical_projection(self):
  rule={'kind':'xc','port':'xc','lane':276,'ck':'ck_xc','lane_by_link':{'x_f_1L02_l0':8}}
  e=('xf','o',276,'x_f_1L02_l0',10,5,'f_1L02')
  for y in (0,10000):
   moved=(*e[:5],y,e[6])
   self.assertEqual(D.place_lane(rule,moved,[],{'y':0,'h':100}), (8,'xc',276,('ck_xc',8)))
  with self.assertRaises(KeyError):D.place_lane(rule,(*e[:3],'missing',*e[4:]),[],{'y':0,'h':100})
 def test_zero_station_quantized_payload_pads_ring_only_and_never_indexes_a_relay(self):
  text=self.emitted(zero=True,force_zero=True,quantized=True)
  self.assertIn(".i({39'd0, w_lo0_src[236:0]})",text)
  self.assertNotIn('st_lo0_0 (',text)
 def test_unhardened_landing_reset_contract_is_source_bound_and_cannot_alias_view(self):
  import hashlib
  body=(Path(__file__).resolve().parents[2]/'rtl/dsrom_sys/s81_dv/land/dsdv_svc_busland.sv').read_text()
  name='dsdv_svc_busland_16'
  row=dict(ref='source',path='rtl/dsrom_sys/s81_dv/land/dsdv_svc_busland.sv',sha256=hashlib.sha256(body.encode()).hexdigest(),reset_stages=0)
  table={'landing_assemblies':{name:row},'landing_reset_stages':{name:0}}
  good=D.landing_reset_check(table,{name},read=lambda ref,path:body)
  self.assertEqual(good['verdict'],'PASS')
  self.assertEqual(good['rows'][0]['qualification'],'UNHARDENED_RTL_ASSEMBLY')
  self.assertEqual(D.landing_reset_check(table,{name},read=lambda ref,path:body+'//changed')['verdict'],'FAIL')
  table['land_views']={name:{'ref':'fake'}}
  with self.assertRaisesRegex(ValueError,'cannot alias'):D.landing_reset_check(table,{name},read=lambda ref,path:body)
 def test_production_zero_hop_forwarding_roots(self):
  text=self.emitted(zero=True)
  for i,root in enumerate(('ck_A','ck_A','ck_B','ck_B')):
   self.assertRegex(text,rf'fwdi_lo{i} \(\.A\({root}\)')
 def test_production_forwarded_and_explicit_clock_refused(self):
  with self.assertRaisesRegex(ValueError,'forwarded-clock output is unsupported'):self.emitted(forwarded=True)
 def test_kit_reset_landing_books_block_release_depth(self):
  self.emitted()
  self.assertEqual(self.last_reset['summary']['block_release_depth'],{'lep':3,'other':7})
  self.assertNotIn('kit_reset_landing',self.last_reset['summary'])
  self.emitted(kit_rl={'legacy':2})
  s=self.last_reset['summary']
  self.assertEqual(s['block_release_depth'],{'lep':3,'other':9})
  self.assertEqual(s['kit_reset_landing'],{'other':2})
  self.assertEqual(s['max_release_depth'],9)
  with self.assertRaisesRegex(SystemExit,'use landing_reset_stages'):self.emitted(kit_rl={'dsfd_dvland_276':2})
 def test_production_unused_reset_pruning_is_opt_in(self):
  text=self.emitted(prune=False)
  self.assertIn('reset_relay st_rs_9_0 (',text)
  self.assertIn('reset_relay st_rs_9_1 (',text)
  self.assertIn('reset_relay st_rs_9_2 (',text)
  self.assertEqual(self.last_reset['summary']['stations'],3)
 def test_production_unused_reset_multilevel_twig_pruned_live_sibling_kept(self):
  text=self.emitted(prune=True)
  self.assertNotIn('st_rs_9_0 (',text)
  self.assertNotIn('st_rs_9_1 (',text)
  self.assertNotIn('wire rs_9_0;',text)
  self.assertNotIn('wire rs_9_1;',text)
  self.assertIn('reset_relay st_rs_9_2 (.ck(ck_clC), .rs(rs0), .i(rs0), .o(rs_9_2));',text)
  self.assertEqual(self.last_reset['depth']['rs_9_2'],2)
  self.assertEqual(self.last_reset['summary']['stations'],1)
  self.assertEqual(set(self.last_reset['summary']['pruned_unused_reset_stations']),{'st_rs_9_0','st_rs_9_1'})
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
