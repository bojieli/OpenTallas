import hashlib,json,pathlib,subprocess,sys,tempfile,unittest
from fec_bit_graph import CLOCKS
from fec_tt_cells import check_lef_areas
class TTAuditTest(unittest.TestCase):
 def run_case(self,defect=None):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);libs=p/'libs';libs.mkdir();mapped=p/'map';mapped.mkdir()
   # Real kit permits missing area semicolon in INVBUF; cover both forms.
   lib=libs/'fixture.lib';lib.write_text('library (test) { cell (ff1) {\narea : 0.2916\nff (IQ, IQN) { }\n} cell (gate) {\narea : 0.1;\n} }')
   ports={r:{'bits':[10+i]} for i,r in enumerate(CLOCKS)}
   cells={r:{'type':'ff1','connections':{'CLK':[10+i]}} for i,r in enumerate(CLOCKS)}
   if defect=='state':cells['extra']={'type':'ff1','connections':{'CLK':[10]}}
   if defect=='residual':cells['bad']={'type':'$_MUX_','connections':{}}
   if defect=='clock':cells[CLOCKS[-1]]['connections']['CLK']=[1000]
   n=mapped/'mapped.json';n.write_text(json.dumps({'modules':{'dut':{'ports':ports,'cells':cells}}}));h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
   graph=p/'graph.json';graph.write_text(json.dumps({'clock_roots':{c:{'flop_bits':1} for c in CLOCKS}}))
   (mapped/'receipt.json').write_text(json.dumps({'yosys_exit':0,'top':'dut','bit_graph_sha256':h(graph),'mapped_json_sha256':h(n),'libraries_sha256':{lib.name:h(lib)}}))
   cp=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('fec_tt_cells.py')),'--map',str(mapped),'--graph',str(graph),'--libs',str(libs),'--out',str(p/'out.json')],text=True,capture_output=True)
   if defect:self.assertNotEqual(cp.returncode,0);self.assertFalse((p/'out.json').exists())
   else:
    self.assertEqual(cp.returncode,0,cp.stderr);r=json.loads((p/'out.json').read_text());self.assertAlmostEqual(r['total_area_library_units'],12*0.2916);self.assertEqual(r['sequential_cells'],12);self.assertFalse(r['physical_qualified'])
 def test_area_and_twelve_direct_roots(self):self.run_case()
 def test_residual_generic_fails(self):self.run_case('residual')
 def test_undeclared_clock_fails(self):self.run_case('clock')
 def test_state_count_change_fails(self):self.run_case('state')
 def test_lef_matches_area_and_rejects_wrong_scale(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'cell.lef';p.write_text('MACRO ff1\n SIZE 1.08 BY 0.27 ;\nEND ff1\n')
   self.assertTrue(check_lef_areas(p,{'ff1':{'area':0.2916}})['all_library_cells_match_actual_lef_area'])
   with self.assertRaises(AssertionError):check_lef_areas(p,{'ff1':{'area':291600}})
if __name__=='__main__':unittest.main()
