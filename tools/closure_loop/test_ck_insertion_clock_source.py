"""Clock insertion must select one real domain and discard only clock-port data delays."""
import pathlib,subprocess,sys,unittest,tempfile,json
from unittest import mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import ck_insertion as C
MOCK=r'''
proc all_clocks {} {return {core_clk hclk vclk}}
proc get_clocks {args} {set n [lindex $args end];return [expr {$n in {core_clk hclk vclk} ? [list $n] : {}}]}
proc get_property {c p} {return [dict get {core_clk clk hclk hk vclk {}} $c]}
proc get_full_name {o} {return $o}
proc get_ports {args} {set n [lindex $args end];return [expr {$n in {clk hk data} ? [list $n] : {}}]}
proc unset_input_delay {args} {puts "DROP [lindex $args end]"}
'''
class ClockSource(unittest.TestCase):
 def run_setup(self,name,setup=MOCK):
  code=MOCK+'\n'+C.CLOCK_SETUP_TCL.replace('CLOCK_REQUEST',name)
  # Catch Tcl's error explicitly: tclsh on stdin otherwise exits zero.
  code=setup+'\nif {[catch {\n'+C.CLOCK_SETUP_TCL.replace('CLOCK_REQUEST',name)+'\n} e]} {puts stderr $e;exit 1}\n'
  return subprocess.run(['tclsh'],input=code,text=True,capture_output=True)
 def test_port_name_resolves_clock_and_only_clock_ports_lose_data_delays(self):
  r=self.run_setup('clk');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('OT_CK_SELECTED core_clk',r.stdout);self.assertIn('DROP clk',r.stdout);self.assertIn('DROP hk',r.stdout);self.assertNotIn('DROP data',r.stdout)
 def test_explicit_clock_name_keeps_its_own_domain(self):
  r=self.run_setup('hclk');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('OT_CK_SELECTED hclk',r.stdout)
 def test_unknown_clock_cannot_silently_measure_all_domains(self):
  r=self.run_setup('ck');self.assertNotEqual(r.returncode,0);self.assertIn('found 0',r.stderr)
 def test_scalar_vector_source_resolves_base_port(self):
  setup=MOCK.replace('core_clk clk', 'core_clk {clk[0]}').replace('{clk hk data}', '{clk[0] hk data}')
  for name in ('clk', 'clk[0]'):
   r=self.run_setup(name,setup);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('OT_CK_SELECTED core_clk',r.stdout)
 def test_scalar_vector_alias_cannot_choose_between_two_domains(self):
  setup=MOCK.replace('hclk hk', 'hclk {clk[0]}').replace('{clk hk data}', '{clk clk[0] data}')
  r=self.run_setup('clk',setup);self.assertNotEqual(r.returncode,0);self.assertIn('found 2',r.stderr)
 def test_all_clocks_keeps_independent_records_and_ignores_virtual_clock(self):
  with tempfile.TemporaryDirectory() as td:
   base=pathlib.Path(td);out=base/'insertion.json'
   (base/'6_final.sdc').write_text('create_clock -name core_clk -period 833 [get_ports {clk}]\ncreate_clock -name hclk -period 1024 [get_ports {hk[0]}]\ncreate_clock -name vclk -period 833\n')
   seen=[]
   def run(cmd,check):
    name=cmd[cmd.index('--clock')+1];seen.append(name);p=pathlib.Path(cmd[cmd.index('--output')+1]);p.write_text(json.dumps({'clock':name,'tt':{'boundary':{'n':3,'mean':100 if name=='core_clk' else 200}}}))
   argv=['ck_insertion.py','--base',td,'--routed','--all-clocks','--output',str(out)]
   with mock.patch.object(sys,'argv',argv),mock.patch.object(C.subprocess,'run',side_effect=run):C.main()
   j=json.loads(out.read_text());self.assertEqual(seen,['core_clk','hclk']);self.assertEqual(set(j['clock_measurements']),{'clk','hk[0]'})
   self.assertEqual(j['clock_measurements']['hk[0]']['tt']['boundary']['mean'],200)
 def test_cts_all_clocks_uses_actual_multi_domain_sdc(self):
  with tempfile.TemporaryDirectory() as td:
   base=pathlib.Path(td);out=base/'insertion.json'
   (base/'4_cts.sdc').write_text('create_clock -name core_clk -period 1026.6666 [get_ports {ck[0]}]\ncreate_clock -name str_clk -period 770.0000 [get_ports {cks[0]}]\n')
   seen=[]
   def run(cmd,check):
    self.assertNotIn('--routed',cmd)
    name=cmd[cmd.index('--clock')+1];seen.append(name)
    pathlib.Path(cmd[cmd.index('--output')+1]).write_text(json.dumps({'clock':name,'tt':{'all':{'n':17460 if name=='str_clk' else 128,'min':100,'max':190 if name=='str_clk' else 120}}}))
   argv=['ck_insertion.py','--base',td,'--all-clocks','--output',str(out)]
   with mock.patch.object(sys,'argv',argv),mock.patch.object(C.subprocess,'run',side_effect=run):C.main()
   j=json.loads(out.read_text());self.assertEqual(seen,['core_clk','str_clk']);self.assertEqual(set(j['clock_measurements']),{'ck[0]','cks[0]'})
   self.assertIn('4_cts.sdc',j['clock_measurements']['cks[0]']['clock_mapping_basis'])
class ClockRoot(unittest.TestCase):
 """ELEM-GAPS/HBMN2 2026-10-18 (hfd_ckgen): PLL-pin clocks forwarded to ports are measured; an unclocked macro pin is skipped."""
 SDC=('create_clock -name core_clk -period 833.3330 [get_pins {u_pll/clk_stream}]\n'
      'create_clock -name ck_hbm -period 1024.0000 [get_pins {u_pll/clk_hbm}]\n'
      'create_clock -name ck_dead -period 1000 [get_pins {u_pll/clk_dead}]\n'
      'create_generated_clock -name pll_stream_o -source [get_pins {u_pll/clk_stream}] -master_clock [get_clocks {core_clk}] -divide_by 1 [get_ports {pll_stream}]\n'
      'create_generated_clock -name pll_hbm_o -source [get_pins {u_pll/clk_hbm}] -master_clock [get_clocks {ck_hbm}] -divide_by 1 [get_ports {pll_hbm}]\n')
 def test_pin_clocks_map_to_their_forwarded_port(self):
  self.assertEqual(C.pin_sourced_clocks(self.SDC),[('core_clk','pll_stream'),('ck_hbm','pll_hbm')])
 def test_all_clocks_measures_clock_root_domains(self):
  with tempfile.TemporaryDirectory() as td:
   base=pathlib.Path(td);out=base/'insertion.json';(base/'6_final.sdc').write_text(self.SDC);seen=[]
   def run(cmd,check):
    name=cmd[cmd.index('--clock')+1];seen.append(name);pathlib.Path(cmd[cmd.index('--output')+1]).write_text(json.dumps({'clock':name,'tt':{'boundary':{'n':1,'mean':15.3}}}))
   argv=['ck_insertion.py','--base',td,'--routed','--all-clocks','--raw-source','--output',str(out)]
   with mock.patch.object(sys,'argv',argv),mock.patch.object(C.subprocess,'run',side_effect=run):C.main()
   j=json.loads(out.read_text());self.assertEqual(seen,['core_clk','ck_hbm']);self.assertEqual(set(j['clock_measurements']),{'pll_stream','pll_hbm'})
   self.assertIn('clock root',j['clock_measurements']['pll_hbm']['clock_mapping_basis'])
 def test_unclocked_macro_pin_is_skipped_not_fatal(self):
  code=('proc all_clocks {} {return {core_clk}}\nproc get_property {p k} {return [expr {$k eq "sources" ? {u_pll/clk_stream} : {}}]}\n'
        'proc get_full_name {o} {return $o}\n'+C.MACRO_CLOCK_SCOPE_TCL+
        '\nif {[catch {puts "OWNED [ot_ck_macro_owned u_pll/refclk core_clk]"} e]} {puts stderr $e;exit 1}\n')
  r=subprocess.run(['tclsh'],input=code,text=True,capture_output=True)
  self.assertEqual(r.returncode,0,r.stderr);self.assertIn('OT_MC_UNCLOCKED u_pll/refclk (clock source u_pll/clk_stream)',r.stdout);self.assertIn('OWNED 0',r.stdout)
  r=subprocess.run(['tclsh'],input=code.replace('u_pll/refclk','u_sram/clk'),text=True,capture_output=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('requires one timing clock',r.stderr)
class FailedReplay(unittest.TestCase):
 def test_partial_arrivals_do_not_hide_failed_sta(self):
  with tempfile.TemporaryDirectory() as td:
   base=pathlib.Path(td);(base/'4_1_cts.odb').touch();(base/'4_cts.sdc').touch()
   result=subprocess.CompletedProcess([],1,'OT_CK 1 100\n[ERROR] missing macro root','')
   argv=['ck_insertion.py','--base',td,'--output',str(base/'out.json')]
   with mock.patch.object(sys,'argv',argv),mock.patch.object(C.subprocess,'run',return_value=result):
    with self.assertRaisesRegex(SystemExit,'clock insertion replay failed'):C.main()
   self.assertFalse((base/'out.json').exists())

class MacroClockScope(unittest.TestCase):
 def probe(self,owners,selected='ckd'):
  script='proc get_property {p prop} {return {'+owners+'}}\nproc get_full_name {p} {return $p}\n'+C.MACRO_CLOCK_SCOPE_TCL+'\nif {[catch {puts "OWNED [ot_ck_macro_owned macro/clk '+selected+']"} e]} {puts stderr $e;exit 1}\n'
  return subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
 def test_selected_and_other_roots_are_distinct(self):
  for owners,expected in [('ckd',1),('core_clk',0),('ckd ckd',1)]:
   r=self.probe(owners);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('OWNED '+str(expected),r.stdout)
 def test_missing_and_ambiguous_macro_roots_fail(self):
  for owners in ('','ckd core_clk'):
   r=self.probe(owners);self.assertNotEqual(r.returncode,0);self.assertIn('requires one timing clock',r.stderr)

class RawSource(unittest.TestCase):
 """--raw-source publishes the physical tree from the clock pin: every clock with a source pin loses its source latency
 (a compensated entry SDC pulled dsfd_vm_bgl28_mc5_h1pcs core to -12.5 ps against a physical 402.8 ps); virtual
 clocks are untouched and the default (loop calibrate) keeps the SDC's own reference."""
 def test_tcl_zeroes_only_clocks_with_sources_and_only_when_asked(self):
  mock='proc all_clocks {} {return {core_clk vclk}}\nproc get_property {c p} {return [dict get {core_clk ck vclk {}} $c]}\nproc get_full_name {o} {return $o}\nproc set_clock_latency {args} {puts "LAT $args"}\n'
  r=subprocess.run(['tclsh'],input=mock+C.RAW_SOURCE_TCL,text=True,capture_output=True)
  self.assertEqual(r.returncode,0,r.stderr);self.assertIn('LAT -source 0 core_clk',r.stdout);self.assertNotIn('vclk',r.stdout)
  self.assertIn('OT_CK_RAW_SOURCE core_clk',r.stdout)
  self.assertIn(C.RAW_SOURCE_TCL.strip(),C.tcl('tt','6_final.odb','6_final.sdc',True,'ck',(),True))
  self.assertNotIn('OT_CK_RAW_SOURCE',C.tcl('tt','6_final.odb','6_final.sdc',True,'ck'))
 def test_all_clocks_forwards_raw_source(self):
  with tempfile.TemporaryDirectory() as td:
   base=pathlib.Path(td);out=base/'insertion.json'
   (base/'6_final.sdc').write_text('create_clock -name core_clk -period 833 [get_ports {ck}]\ncreate_clock -name req_clk -period 833 [get_ports {ck_req}]\n')
   seen=[]
   def run(cmd,check):
    seen.append('--raw-source' in cmd);pathlib.Path(cmd[cmd.index('--output')+1]).write_text(json.dumps({'clock':'x','tt':{}}))
   argv=['ck_insertion.py','--base',td,'--routed','--all-clocks','--raw-source','--output',str(out)]
   with mock.patch.object(sys,'argv',argv),mock.patch.object(C.subprocess,'run',side_effect=run):C.main()
   self.assertEqual(seen,[True,True]);self.assertTrue(json.loads(out.read_text())['raw_source'])

if __name__=='__main__':unittest.main()
