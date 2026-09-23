"""The divider captures operands without changing quotient, inexact, or latency."""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('rtl_source', ['rtl/lib/ot_wide_div_small_seq.sv',
    'results/rtl/small_divider_scratch_reset/candidate.sv'])
@pytest.mark.parametrize('simulator', ['iverilog', 'verilator'])
@pytest.mark.parametrize('divisor_bits', [6, 9])
@pytest.mark.parametrize('first_chunk', [1, 3])
def test_operand_capture(tmp_path, simulator, divisor_bits, first_chunk, rtl_source):
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
    bench = bench.replace('.BITS_PER_STEP(1)', f'.BITS_PER_STEP({first_chunk})')
    bench = bench.replace('//: Exact multiples,', r"""
        // Cancel in-flight payload and exercise start while reset is asserted.
        for (trial = 0; trial < 4; trial = trial + 1) begin
            @(negedge clk);
            reference_dividend = {WIDTH{1'b1}}; reference_divisor = 7;
            dividend = reference_dividend; divisor = reference_divisor; start = 1;
            @(negedge clk); start = 0;
            repeat (trial + 1) @(negedge clk);
            #1; rst_n = 0; start = 1;
            #1;
            if (busy !== 0 || done !== 0 || inexact !== 0)
                $fatal(1,"reset protocol outputs");
            for (k = 0; k < DUTS; k = k + 1)
                if (quotient[k] !== 0) $fatal(1,"reset quotient");
            repeat (2) @(negedge clk);
            start = 0; rst_n = 1;
            repeat (170) begin
                @(negedge clk);
                if (busy !== 0 || done !== 0) $fatal(1,"stale completion");
            end
        end
        //: Exact multiples,""")
    reference = r'''
    wire [DUTS-1:0] ref_busy, ref_done, ref_inexact;
    wire [WIDTH-1:0] ref_quotient [0:DUTS-1];
    genvar r;
    generate for(r=0;r<DUTS;r=r+1)begin : old_units
        old_divider #(.WIDTH(WIDTH),.DIVISOR_BITS(DBITS),.BITS_PER_STEP(r==0 ? FIRST_CHUNK : (1<<r))) ref_dut(
            .clk(clk),.rst_n(rst_n),.start(start),.dividend(reference_dividend),
            .divisor(reference_divisor),.busy(ref_busy[r]),.done(ref_done[r]),
            .quotient(ref_quotient[r]),.inexact(ref_inexact[r]));
        always @(negedge clk) if(rst_n)
            if({busy[r],done[r],quotient[r],inexact[r]} !==
               {ref_busy[r],ref_done[r],ref_quotient[r],ref_inexact[r]})
                $fatal(1,"changed public output chunk %0d",1<<r);
    end endgenerate
    initial begin #10000000; $fatal(1,"timeout");end
'''
    reference = reference.replace('FIRST_CHUNK', str(first_chunk))
    bench = bench.replace('endmodule', reference+'\nendmodule')
    source = tmp_path/'tb.sv';source.write_text(bench)
    sources = [str(ROOT/rtl_source),str(before),str(source)]
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
