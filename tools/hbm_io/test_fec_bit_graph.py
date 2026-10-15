import contextlib,io,json,pathlib,subprocess,sys,tempfile,unittest
from fec_bit_graph import CLOCKS
class GraphTest(unittest.TestCase):
 def test_actual_scalar_clock_crossings_and_two_gate_depth(self):
  ports={r:{'direction':'input','bits':[10+i]} for i,r in enumerate(CLOCKS)};ports['data']={'direction':'input','bits':[30]};cells={}
  for i in range(12):
   cells[f'ff{i}']={'type':'$_DFF_P_','connections':{'C':[10+i],'D':[200+i],'Q':[100+i]},'port_directions':{'C':'input','D':'input','Q':'output'}}
   cells[f'xor{i}']={'type':'$_XOR_','connections':{'A':[100+i],'B':[30],'Y':[300+i]},'port_directions':{'A':'input','B':'input','Y':'output'}}
   cells[f'mux{i}']={'type':'$_MUX_','connections':{'A':[300+i],'B':[100+(i+1)%12],'S':[30],'Y':[200+i]},'port_directions':{'A':'input','B':'input','S':'input','Y':'output'}}
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'in.json').write_text(json.dumps({'modules':{'dut':{'ports':ports,'cells':cells}}}))
   cp=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('fec_bit_graph.py')),'--top','dut','--netlist',str(p/'in.json'),'--out',str(p/'out.json')],capture_output=True,text=True);self.assertEqual(cp.returncode,0,cp.stderr);j=json.loads((p/'out.json').read_text())
   self.assertEqual(j['total_flop_bits'],12);self.assertEqual(j['combinational_scalar_cells'],24)
   for i,r in enumerate(CLOCKS):
    row=j['clock_roots'][r];self.assertEqual(row['max_D_logic_levels'],2);self.assertEqual(row['registered_source_Q_bits_exact'],{r:1,CLOCKS[(i+1)%12]:1})
   self.assertEqual(len(j['cross_root_registered_relations']),12)
if __name__=='__main__':unittest.main()
