import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import bind,native_istations

class NativeStations(unittest.TestCase):
 def fixture(self):
  typ={'module':'vehicle','buses':[{'name':'o','dir':'out','width':8}], 'internal_stations':[{'conn':'bus:o','regs_um':[[i,0] for i in range(8)]}], 'contents':[]}
  L={'lane':'L0','oname':'o','cycles':22,'ft':[]}
  b=SimpleNamespace(ab={'internal_stations_types':['sys']},types={'sys':typ},parts={'p':{'type':'sys'}},out_bus={'p':[L]},plan={'lanes':[{'id':'L0','fixed_cycles':8}]})
  return b,L
 def test_pricing_and_guards(self):
  b,L=self.fixture();native_istations.annotate(b);self.assertEqual(bind.lane_pad(L),12);self.assertEqual(2+bind.lane_pad(L)+L['internal_source_cycles'],22)
  b,L=self.fixture();b.plan['lanes'][0]['fixed_cycles']=7
  with self.assertRaises(ValueError):native_istations.annotate(b)
  b,L=self.fixture();L['cycles']=9
  with self.assertRaises(ValueError):native_istations.annotate(b)
 def test_cycle_and_mutants(self):
  b,L=self.fixture();native_istations.annotate(b)
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);f=d/'rtl/vehicle.sv';f.parent.mkdir()
   f.write_text('module vehicle(input clk,input arst_n,input [7:0] d,output [8:0] o);\nwire rst_n=arst_n;\n ot_dp_st #(.W(8)) u_bout_o (.clk(clk), .rst_n(rst_n), .d(d), .ea(rst_n), .q(o[7:0]), .eq(o[8]));\nendmodule\n')
   native_istations.materialize(b,'sys',f);text=f.read_text();self.assertEqual(text.count('FIRM plan station'),8)
   native_istations.materialize(b,'sys',f);self.assertEqual(f.read_text(),text)
   tb='''module tb;reg clk=0;always #5 clk=~clk;reg rst_n=0;reg[7:0]d=1;wire[8:0]o;vehicle u(clk,rst_n,d,o);reg[7:0] gold[0:21];integer i,cyc=0;wire[7:0]q,land;ot_dp_st #(.W(8)) rx(.clk(clk),.rst_n(rst_n),.d(o[7:0]),.ea(o[8]),.q(land),.eq());ot_dp_dly #(.W(8),.D(PAD)) pad(.clk(clk),.d(land),.q(q));always@(posedge clk)begin gold[0]<=d;for(i=1;i<22;i=i+1)gold[i]<=gold[i-1];end always@(negedge clk)begin cyc=cyc+1;if(cyc>40 && q!==gold[21])$fatal(1,"EDGE_MISMATCH %d",cyc);d={d[6:0],d[7]^d[5]^d[4]^d[3]};rst_n=1;if(cyc==120)begin $display("CYCLE22_PASS");$finish;end end endmodule'''
   for name,source,pad,want in [('nominal',text,12,0),('missing',text.replace('.d(o_is7_q)', '.d(d)'),12,1),('double',text,20,1)]:
    if name=='missing':self.assertNotEqual(source,text)
    src=d/(name+'.sv');src.write_text(bind.CELLS+'\n'+source+'\n'+tb.replace('PAD',str(pad)))
    binary=d/name;cp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(binary),str(src)],capture_output=True,text=True);self.assertEqual(cp.returncode,0,cp.stderr)
    run=subprocess.run(['vvp',str(binary)],capture_output=True,text=True);print(name,run.returncode,run.stdout.strip());self.assertEqual(bool(run.returncode),bool(want))
if __name__=='__main__':unittest.main()
