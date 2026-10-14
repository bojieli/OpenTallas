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
if __name__=='__main__':unittest.main()
