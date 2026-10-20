"""Typed Liberty two-release-stage proof; no threshold/old-proof changes."""
import sys,json,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import native_census as N
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import textbook_lint as T
LIB='''library(test) {
cell(ASR) { ff(IQ,IQN) { clocked_on : "CLK"; next_state : "D"; clear : "!RESETN"; preset : "!SETN"; }
pin(CLK){direction:input;clock:true;} pin(D){direction:input;}pin(RESETN){direction:input;}pin(SETN){direction:input;}pin(QN){direction:output;function:"IQN";} }
cell(INV){pin(A){direction:input;}pin(Y){direction:output;function:"!A";}}
cell(BUF){pin(A){direction:input;}pin(Y){direction:output;function:"A";}}
}'''
def fixture(wrong=None):
 rows=['module top(ck,other,rst_n,din,y);\ninput ck,other,rst_n,din;\noutput y;']
 for a in range(3):
  rows += [f'wire f{a}n,f{a}; ASR first{a}(.CLK(ck),.D(1\'b1),.RESETN(rst_n),.SETN(1\'b1),.QN(f{a}n)); INV fi{a}(.A(f{a}n),.Y(f{a}));']
  for b in range(2):
   k=a*2+b;clock='other'if wrong=='clock'and k==0 else'ck';d="1'b0"if wrong=='D'and k==0 else"1'b1";reset=f'f{a}n'if wrong=='polarity'and k==0 else f'f{a}';reset='rst_n'if wrong=='bypass'and k==0 else reset
   rows += [f'wire l{k}n,l{k},q{k}; ASR last{k}(.CLK({clock}),.D({d}),.RESETN({reset}),.SETN(1\'b1),.QN(l{k}n)); INV li{k}(.A(l{k}n),.Y(l{k})); ASR data{k}(.CLK(ck),.D(din),.RESETN(l{k}),.SETN(1\'b1),.QN(q{k}));']
 rows+=['assign y=q0;endmodule'];return'\n'.join(rows)
class Proof(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.lib=Path(self.tmp.name)/'cells.lib';self.lib.write_text(LIB);self.roles,_=N.liberty_roles([self.lib]);self.profile=dict(schema='opentallas.ref_tile.reset_landing.v1',top='top',enable=False,async_release=dict(stages=2,clock='ck',ports=dict(rst_n=dict(first=3,final=6))))
 def tearDown(self):self.tmp.cleanup()
 def graph(self,wrong=None):return T.flatten(T.parse_verilog(fixture(wrong)),'top')[0]
 def proof(self,wrong=None):return N.async_release_proof(self.graph(wrong),self.roles,[self.lib],self.profile)
 def test_positive(self):
  self.assertEqual(self.proof()['ports']['rst_n']['edges'],2);self.assertEqual(N.census(self.graph(),self.roles)['status'],'PASS')
 def test_actual_lib_state_orientation(self):
  self.lib.write_text(LIB.replace('ff(IQ,IQN)','ff(IQN,IQNN)').replace('next_state : "D"','next_state : "!D"').replace('clear : "!RESETN"; preset : "!SETN"','clear : "!SETN"; preset : "!RESETN"'))
  self.roles,_=N.liberty_roles([self.lib])
  self.assertEqual(self.proof()['status'],'PASS')
 def test_setn_D0_positive_release(self):
  src=fixture()
  import re
  def stage(m):
   s=m.group().replace(".D(1'b1)",".D(1'b0)")
   return re.sub(r"\.RESETN\(([^)]+)\),\.SETN\(1'b1\)",r".RESETN(1'b1),.SETN(\1)",s)
  src=re.sub(r'ASR (?:first|last)\d+\([^;]+;',stage,src)
  src=re.sub(r'INV ([fl]i\d+)',r'BUF \1',src)
  g=T.flatten(T.parse_verilog(src),'top')[0]
  self.assertEqual(N.async_release_proof(g,self.roles,[self.lib],self.profile)['status'],'PASS')
 def test_wrong_clock(self):
  with self.assertRaisesRegex(ValueError,'clock'):self.proof('clock')
 def test_wrong_D(self):
  with self.assertRaisesRegex(ValueError,'D'):self.proof('D')
 def test_wrong_polarity(self):
  with self.assertRaisesRegex(ValueError,'polarity'):self.proof('polarity')
 def test_raw_bypass(self):
  with self.assertRaises(ValueError):self.proof('bypass')
 def test_stale_counts(self):
  self.profile['async_release']['ports']['rst_n']['final']=5
  with self.assertRaisesRegex(ValueError,'count'):self.proof()
 def test_not_two_edges(self):
  self.profile['async_release']['stages']=3
  with self.assertRaisesRegex(ValueError,'two'):self.proof()
 def test_wrong_liberty_polarity(self):
  self.lib.write_text(LIB.replace('!RESETN','RESETN'))
  with self.assertRaises(ValueError):self.proof()
 def test_wrong_liberty_output_function(self):
  self.roles['ASR']['pins']['QN']['function']='IQ'
  with self.assertRaises(ValueError):self.proof()
 def test_inserted_stage_profile_refused(self):
  self.profile['enable']=True
  with self.assertRaisesRegex(ValueError,'existing RTL'):self.proof()
if __name__=='__main__':unittest.main()
