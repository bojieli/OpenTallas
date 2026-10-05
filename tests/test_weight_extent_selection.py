"""Check extent arbitration against integer minima, including partial streams."""
from pathlib import Path
import random
import shutil
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which('iverilog') is None,reason='iverilog unavailable')
def test_extent_minimum(tmp_path):
    rng=random.Random(2718)
    values=[0,1,31,32,33,511,512,513,1023,1024,1025,0x7fffffff,0xffffffff]
    cases=[]
    for replay in [0,1]:
        for bank in [0,1]:
            for first in [1,32,172,512]:
                for left in values:
                    for row in [0,1,31,32,511,512,513,1024]:
                        limit=(512 if bank else first) if replay else 32
                        cases.append((replay,bank,first,left,row,min(left,limit,row) if replay else min(left,limit)))
    for _ in range(2000):
        replay=rng.randrange(2);bank=rng.randrange(2);first=rng.randrange(1,513)
        left=rng.randrange(1<<32);row=rng.randrange(1025)
        limit=(512 if bank else first) if replay else 32
        cases.append((replay,bank,first,left,row,min(left,limit,row) if replay else min(left,limit)))
    bench=tmp_path/'tb.sv'
    checks='\n'.join(f"check(1'b{r},1'b{b},10'd{f},32'd{l},11'd{row},10'd{expect});"for r,b,f,l,row,expect in cases)
    bench.write_text('''module tb;
wire [9:0] tile_words;
ot_a3_weight_tile_scheduler #(.ROW_REUSE(1)) dut(.clk(1'b0),.rst_n(1'b0),.clear(1'b0),.tile_words(tile_words));
task check(input bit r,b,input [9:0] f,input [31:0] l,input [10:0] row,input [9:0] expected);
begin
 dut.replay=r;dut.tile_bank=b;dut.first_words=f;dut.tile_left=l;dut.row_left=row;
 #1;if(tile_words!==expected)$fatal(1,"extent mismatch r=%0d b=%0d f=%0d l=%0d row=%0d got=%0d expected=%0d",r,b,f,l,row,tile_words,expected);
end endtask
initial begin
'''+checks+'\n$display("PASS extent minima");$finish;end\nendmodule\n')
    sim=tmp_path/'sim'
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(sim),str(ROOT/'rtl/abi3/ot_a3_weight_tile_scheduler.sv'),str(bench)],check=True,capture_output=True,timeout=30)
    r=subprocess.run(['vvp',str(sim)],capture_output=True,text=True,timeout=30)
    assert r.returncode==0,r.stdout+r.stderr
    assert 'PASS extent minima' in r.stdout
