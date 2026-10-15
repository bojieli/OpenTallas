import json,pathlib,subprocess,sys,tempfile,unittest
class PrebuildTest(unittest.TestCase):
 def test_manifest_named_roots_and_registered_crossing(self):
  m={'ports':{'a':{'direction':'input','bits':[1]},'b':{'direction':'input','bits':[2]}},'cells':{},'netnames':{'ra':{'bits':[10]},'rb':{'bits':[11]}}}
  for n,clk,d,q in [('a',1,11,10),('b',2,10,11)]:m['cells'][n]={'type':'$dff','parameters':{'WIDTH':'1','CLK_POLARITY':'1'},'connections':{'CLK':[clk],'D':[d],'Q':[q]},'port_directions':{'CLK':'input','D':'input','Q':'output'}}
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'n.json').write_text(json.dumps({'modules':{'dut':m}}));(p/'c.json').write_text(json.dumps({'clocks':['a','b']}))
   cp=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('fec_physical_prebuild.py')),'--top','dut','--netlist',str(p/'n.json'),'--clock-manifest',str(p/'c.json'),'--out',str(p/'o.json')],capture_output=True,text=True);self.assertEqual(cp.returncode,0,cp.stderr);j=json.loads((p/'o.json').read_text());self.assertEqual(j['total_flop_bits'],2);self.assertEqual(j['roots']['a']['registered_source_bits_conservative'],{'b':1});self.assertEqual(j['roots']['b']['registered_source_bits_conservative'],{'a':1})
if __name__=='__main__':unittest.main()
