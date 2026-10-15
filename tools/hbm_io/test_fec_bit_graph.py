import json,pathlib,subprocess,sys,tempfile,unittest
from fec_bit_graph import CLOCKS
class GraphTest(unittest.TestCase):
 def check_graph(self,root_count):
  names=CLOCKS if root_count==12 else [f'root_{i}' for i in range(root_count)]
  ports={r:{'direction':'input','bits':[10+i]} for i,r in enumerate(names)};ports['data']={'direction':'input','bits':[3]};cells={}
  for i in range(root_count):
   cells[f'ff{i}']={'type':'$_DFF_P_','connections':{'C':[10+i],'D':[200+i],'Q':[100+i]},'port_directions':{'C':'input','D':'input','Q':'output'}}
   cells[f'xor{i}']={'type':'$_XOR_','connections':{'A':[100+i],'B':[3],'Y':[300+i]},'port_directions':{'A':'input','B':'input','Y':'output'}}
   cells[f'mux{i}']={'type':'$_MUX_','connections':{'A':[300+i],'B':[100+(i+1)%root_count],'S':[3],'Y':[200+i]},'port_directions':{'A':'input','B':'input','S':'input','Y':'output'}}
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'in.json').write_text(json.dumps({'modules':{'dut':{'ports':ports,'cells':cells}}}));(p/'clocks.json').write_text(json.dumps({'clocks':names}))
   command=[sys.executable,str(pathlib.Path(__file__).with_name('fec_bit_graph.py')),'--top','dut','--netlist',str(p/'in.json'),'--out',str(p/'out.json')]
   if root_count!=12:command+=['--clock-manifest',str(p/'clocks.json')]
   cp=subprocess.run(command,capture_output=True,text=True);self.assertEqual(cp.returncode,0,cp.stderr);j=json.loads((p/'out.json').read_text())
   self.assertEqual(j['total_flop_bits'],root_count);self.assertEqual(j['combinational_scalar_cells'],2*root_count)
   for i,r in enumerate(names):
    row=j['clock_roots'][r];self.assertEqual(row['max_D_logic_levels'],2);self.assertEqual(row['registered_source_Q_bits_exact'],{r:1,names[(i+1)%root_count]:1})
   self.assertEqual(len(j['cross_root_registered_relations']),root_count)
 def test_default_twelve_roots(self):self.check_graph(12)
 def test_manifest_twenty_three_roots(self):self.check_graph(23)
if __name__=='__main__':unittest.main()
