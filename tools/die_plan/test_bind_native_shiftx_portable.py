"""Native $shiftx is printed portably without changing its primitive or X/OOB semantics."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace as NS

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_native_glue as NG

pytestmark = pytest.mark.skipif(not shutil.which("iverilog") or
    not (shutil.which("docker") or os.environ.get("OT_BIND_YOSYS")), reason="native Yosys and Icarus required")


def run_case(tmp, aw, bw, yw, signed, constant=False, mutant=None):
    params = {k: format(v, "032b") for k, v in dict(A_WIDTH=aw, B_WIDTH=bw, Y_WIDTH=yw,
                                                   A_SIGNED=0, B_SIGNED=signed).items()}
    ports = dict(A=["1"] * aw if constant else list(range(2, 2+aw)),
                 B=list(range(2+aw, 2+aw+bw)), Y=list(range(2+aw+bw, 2+aw+bw+yw)))
    cell = NS(ytype="$shiftx", yparams=params, ports=ports, dirs=dict(A="input", B="input", Y="output"))
    native = NG.NativeGlue(tmp / "helpers", ["$shiftx"])
    call = native.emit(cell, dict(A="A", B="B", Y="U"), "u")
    iw = max(bw, aw.bit_length(), yw.bit_length()) + 3
    extend = "{{" + str(iw-bw) + ("{B["+str(bw-1)+"]}},B}" if signed else "{1'b0}},B}")
    src = ("{" + str(aw) + "{1'b1}}") if constant else "A"
    # Independent per-bit mathematical index model, not an oversized SV part-select.
    tb = f'''module tb;reg[{aw-1}:0] A;reg[{bw-1}:0] B;wire[{yw-1}:0] U;
wire[{aw-1}:0] ref_A={src};reg[{yw-1}:0] G;reg signed[{iw-1}:0]base,index;
integer j,bad=0,checks=0,seed=93; {call}
task check;begin #1;G='x;
if((^B)!==1'bx)begin base={extend};for(j=0;j<{yw};j=j+1)begin index=base+j;if(index>=0&&index<{aw})G[j]=ref_A[index];end end
checks++;if(G!==U)bad++;end endtask
initial begin A='1;
for(integer k=-{yw+4};k<={aw+4};k++)begin B={bw}'(k);check;end
for(integer k=0;k<128;k++)begin A=$random(seed);B=$random(seed);check;end
A='x;B=0;check;A='1;A[0]=1'bx;check;A[0]=1'bz;check;
A='1;B='x;check;B='z;check;B=0;B[0]=1'bx;check;B=0;B[{bw-1}]=1'bx;check;
B={{1'b0,{{{bw-1}{{1'b1}}}}}};check;B={{1'b1,{{{bw-1}{{1'b0}}}}}};check;B='1;check;
$display("SHIFTX_CHECKS %0d ERRORS %0d",checks,bad);if(bad)$fatal(1,"shiftx mismatch");$finish;end endmodule'''
    (tmp / "tb.sv").write_text(tb)
    subprocess.run(["iverilog", "-g2012", "-o", str(tmp / "sim"), str(tmp / "tb.sv"),
                    *map(str, native.files)], check=True, capture_output=True, text=True)
    r = subprocess.run(["vvp", str(tmp / "sim")], capture_output=True, text=True)
    assert (r.returncode != 0) == bool(mutant), r.stdout + r.stderr
    if not mutant:
        assert "ERRORS 0" in r.stdout
    return native


@pytest.mark.parametrize("aw,bw,yw,signed,constant", [(32,34,128,1,True), (128,34,32,1,False),
                                                     (13,6,37,0,False), (1,1,1,1,False)])
def test_shiftx_signed_large_indices_and_four_state(tmp_path, aw, bw, yw, signed, constant):
    native = run_case(tmp_path, aw, bw, yw, signed, constant)
    if constant:
        assert native.files[0].stem == "ot_bind_native_4ee6006e6a5bb9ff1c0dff1c"  # canonical CW helper ABI


@pytest.mark.parametrize("mutation", ["wrong_shift", "zero_fill"])
def test_shiftx_mutant_controls(tmp_path, monkeypatch, mutation):
    old = NG.SHIFTX_PORTABLE_MAP
    new = (old.replace("index = base + PAD", "index = -base + PAD") if mutation == "wrong_shift"
           else old.replace("1'bx", "1'b0"))
    assert old != new
    monkeypatch.setattr(NG, "SHIFTX_PORTABLE_MAP", new)
    run_case(tmp_path, 32, 34, 128, 1, True, mutant=mutation)
