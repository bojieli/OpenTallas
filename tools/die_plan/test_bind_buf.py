"""Exercise emitted Slang/Yosys buffer logic, including four-state values and a mutant."""
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind


@pytest.mark.skipif(not shutil.which("iverilog"), reason="requires Icarus")
@pytest.mark.parametrize("mutant", [False, True])
def test_emitted_buffer_exhaustive_and_four_state(tmp_path, mutant):
    c = NS(ytype="$buf", yparams={"WIDTH": "00010000"}, src="original.sv:1")
    stmt = bind._glue(c, {"A": "~a" if mutant else "a", "Y": "y"}, "$buf$1")
    src = """module tb;
reg [15:0] a;
wire [15:0] y;
integer i;
""" + stmt + """
initial begin
 for(i=0;i<65536;i=i+1) begin
  a=i; #1; if(y!==a) $fatal(1,"identity mismatch");
 end
 a=16'hxxxx; #1; if(y!==a) $fatal(1,"x mismatch");
 a=16'hzzzz; #1; if(y!==a) $fatal(1,"z mismatch");
 a=16'b10xz01zx10xz01zx; #1; if(y!==a) $fatal(1,"mixed mismatch");
 $finish;
end
endmodule
"""
    f=tmp_path/"tb.sv"; f.write_text(src)
    exe=tmp_path/"sim"
    subprocess.run(["iverilog","-g2012","-o",str(exe),str(f)],check=True,capture_output=True)
    run=subprocess.run(["vvp",str(exe)],capture_output=True,text=True)
    assert (run.returncode != 0) == mutant
