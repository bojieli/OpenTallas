"""Actual glue25f 571-bit IDX-query launch: both forwarded slices and a failing mutant."""
import ast
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_terminal_idx_query_launch_two_real_slices(tmp_path):
    spec = importlib.util.spec_from_file_location('station', ROOT / 'tools/hbm_die_station_gen.py')
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    fixture = json.loads((ROOT / 'tests/fixtures/hbm_die/launch_571_terminal.json').read_text())
    rec = fixture['record']
    fc = {ast.literal_eval(k): v for k, v in fixture['forwarded'].items()}
    for mutant in (False, True):
        e, _ = g.build(rec, fc, mutant=mutant)
        assert len(e.clk_out) == 2
        assert len(e.map) == 571
        assert e.map['b[512]'] == {'src': 'a[512]', 'dom': 'b[572]'}
        (tmp_path / 'dut.sv').write_text(g.module_text(rec, e))
        (tmp_path / 'tb.sv').write_text('''`timescale 1ps/1fs
module tb;
reg [570:0] a = 0; reg ck=0; wire [572:0] b; integer i,j,errors=0;
hfd_stn_699 dut(.a(a), .b(b), .ck(ck), .rst(1'b1));
initial begin
for(i=0;i<4096;i=i+1)begin
 ck=0; for(j=0;j<571;j=j+1)a[j]=((i*29+j*13+i/7)%11)<5;
 #416.666; ck=1; #1;
 if(b[570:0]!==a)errors=errors+1;
 if(b[572:571]!==2'b11)errors=errors+1;
 #415.667;
end
$display("checks=4096 errors=%0d",errors);
if(errors)$fatal(1,"two-slice launch mismatch"); $finish;
end
endmodule
''')
        subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(tmp_path / 'sim'),
                        str(tmp_path / 'tb.sv'), str(tmp_path / 'dut.sv'),
                        str(ROOT / 'physical/hbm_accel_die_views/stations/rtl/ot_hbm_stn_lib.sv'),
                        str(ROOT / 'rtl/common/ot_fwd_link_stage.sv')], check=True, capture_output=True)
        run = subprocess.run(['vvp', str(tmp_path / 'sim')], capture_output=True, text=True)
        assert (run.returncode != 0) == mutant, run.stdout + run.stderr
        assert ('errors=0' in run.stdout) != mutant
