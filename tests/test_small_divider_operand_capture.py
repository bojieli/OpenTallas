"""The divider captures operands without changing quotient, inexact, or latency."""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('simulator', ['iverilog', 'verilator'])
@pytest.mark.parametrize('divisor_bits', [6, 9])
def test_operand_capture(tmp_path, simulator, divisor_bits):
    before = tmp_path/'before.sv'
    before.write_text((ROOT/'results/rtl/small_divider_operand_capture/before.sv').read_text().replace(
        'module ot_wide_div_small_seq #(', 'module old_divider #('))
    bench = (ROOT/'rtl/test/tb_wide_div_small_seq_equiv.sv').read_text()
    bench = bench.replace('integer DBITS = 9', f'integer DBITS = {divisor_bits}')
    bench = bench.replace('reg [WIDTH:0] want;', 'reg [DBITS-1:0] reference_divisor;\n    reg [WIDTH-1:0] reference_dividend;\n    reg [WIDTH:0] want;')
    bench = bench.replace("dividend = a; divisor = d; start = 1'b1;",
                          "reference_dividend=a; reference_divisor=d; dividend = a; divisor = d; start = 1'b1;")
    bench = bench.replace("@(negedge clk); start = 1'b0;",
                          "@(negedge clk); start = 1'b0; dividend=~a; divisor=~d;")
    reference = r'''
    wire [DUTS-1:0] ref_busy, ref_done;
    genvar r;
    generate for(r=0;r<DUTS;r=r+1)begin : old_units
        old_divider #(.WIDTH(WIDTH),.DIVISOR_BITS(DBITS),.BITS_PER_STEP(1<<r)) ref_dut(
            .clk(clk),.rst_n(rst_n),.start(start),.dividend(reference_dividend),
            .divisor(reference_divisor),.busy(ref_busy[r]),.done(ref_done[r]),
            .quotient(),.inexact());
        always @(negedge clk) if(rst_n)
            if(busy[r] !== ref_busy[r] || done[r] !== ref_done[r])
                $fatal(1,"changed handshake latency chunk %0d",1<<r);
    end endgenerate
    initial begin #10000000; $fatal(1,"timeout");end
'''
    bench = bench.replace('endmodule', reference+'\nendmodule')
    source = tmp_path/'tb.sv';source.write_text(bench)
    sources = [str(ROOT/'rtl/lib/ot_wide_div_small_seq.sv'),str(before),str(source)]
    top = 'tb_wide_div_small_seq_equiv'
    if simulator == 'iverilog':
        command = ['iverilog','-g2012','-s',top,'-o',str(tmp_path/'sim'),*sources]
        run = ['vvp',str(tmp_path/'sim')]
    else:
        command = [str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),
                   '--binary','--timing','-j','2','-Wno-fatal','--top-module',top,
                   '--Mdir',str(tmp_path/'obj'),*sources]
        run = [str(tmp_path/'obj'/('V'+top))]
    p = subprocess.run(command,capture_output=True,text=True,timeout=300)
    assert p.returncode == 0,p.stdout+p.stderr
    p = subprocess.run(run,capture_output=True,text=True,timeout=120)
    assert p.returncode == 0,p.stdout+p.stderr
    assert 'FAIL' not in p.stdout
    assert 'PASS tb_wide_div_small_seq_equiv 354 arguments x 6 widths' in p.stdout
