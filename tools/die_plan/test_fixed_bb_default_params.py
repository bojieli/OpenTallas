import tempfile
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G
import native_bb as N

class FixedBBDefaults(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bb = self.root / "egn_bb.v"
        self.bb.write_text("(* blackbox *) module egn(clk,x,q); input clk; input [31:0] x; output [31:0] q; endmodule\n")
        self.rtl = self.root / "eng.sv"
        self.rtl.write_text("module egn #(parameter integer LM=5,LA=4)(input clk,input[31:0]x,output[31:0]q);assign q=x;endmodule\n")
        self.top = self.root / "top.sv"
        self.top.write_text("module top(input clk);egn #(.LM(5),.LA(4)) u(.clk(clk),.x(0),.q());endmodule\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_restore_defaults_preserves_physical_header(self):
        text = G.fixed_bb_default_parameters("egn", self.bb.read_text(), [self.top,self.rtl,self.bb])
        self.assertIn(G._module_header(self.bb.read_text(), "egn"), text)
        params = N.header_params(text)["egn"]
        self.assertEqual(params, {"LM":("int",5),"LA":("int",4)})
        p=self.root/"recovered_bb.v";p.write_text(text)
        hp=N.headers_params([p])
        self.assertEqual(N.plan([("egn","top","u","LM","1","00000000000000000000000000000101")],hp)[2],[])
        self.assertEqual(len(N.plan([("egn","top","u","LM","1","00000000000000000000000000000110")],hp)[2]),1)

    def test_caller_mutant_cannot_redefine_identity(self):
        self.top.write_text(self.top.read_text().replace(".LM(5)",".LM(6)"))
        text=G.fixed_bb_default_parameters("egn",self.bb.read_text(),[self.top,self.rtl,self.bb])
        self.assertEqual(N.header_params(text)["egn"]["LM"],("int",5))

    def test_existing_metadata_and_plain_call_unchanged(self):
        text=G.fixed_bb_default_parameters("egn",self.bb.read_text(),[self.top,self.rtl,self.bb])
        self.assertIsNone(G.fixed_bb_default_parameters("egn",text,[self.top,self.rtl,self.bb]))
        self.top.write_text("module top(input clk);egn u(.clk(clk),.x(0),.q());endmodule")
        self.assertIsNone(G.fixed_bb_default_parameters("egn",self.bb.read_text(),[self.top,self.rtl,self.bb]))

    def test_missing_native_default_refuses(self):
        with self.assertRaisesRegex(ValueError,"not unique"):
            G.fixed_bb_default_parameters("egn",self.bb.read_text(),[self.top,self.bb])

    def test_duplicate_incompatible_native_default_refuses(self):
        other=self.root/"other.sv";other.write_text(self.rtl.read_text().replace("LM=5","LM=6"))
        with self.assertRaisesRegex(ValueError,"not unique"):
            G.fixed_bb_default_parameters("egn",self.bb.read_text(),[self.top,self.rtl,self.bb,other])

if __name__ == "__main__": unittest.main()
