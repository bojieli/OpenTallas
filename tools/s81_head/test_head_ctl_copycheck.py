from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[2]
RTL=ROOT/'rtl/dsrom_sys/s81_head/ot_s81hd_ctl_hsf0_static.sv'


@pytest.mark.parametrize('mutant',[0,1,2])
def test_registered_word_reduction_exact_and_mutants(tmp_path,mutant):
    yosys=shutil.which('yosys') or str(Path.home()/'.local/opentallas-tools/bin/yosys')
    if not Path(yosys).exists():pytest.skip('yosys unavailable')
    text=RTL.read_text();unit=tmp_path/'unit.sv'
    unit.write_text(text[text.index('module ot_s81hd_ctl_copycheck'):])
    miter=tmp_path/'miter.sv'
    miter.write_text('''module miter(input clk,input[242:0]a,b,output bad);
reg gold;always@(posedge clk)gold<=(a[0+:81]!=b[0+:81])||(a[81+:81]!=b[81+:81])||(a[162+:81]!=b[162+:81]);
wire actual;ot_s81hd_ctl_copycheck #(.MUT(MUTANT))u(.ck(clk),.a(a),.b(b),.mismatch(actual));
assign bad=gold!=actual;endmodule
'''.replace('MUTANT',str(mutant)))
    cmd=f'read_verilog -sv {unit} {miter}; prep -top miter -flatten; sat -seq 3 -set-init-zero -prove bad 0'
    p=subprocess.run([yosys,'-Q','-p',cmd],text=True,capture_output=True)
    assert p.returncode==0,p.stderr
    assert ('SUCCESS' in p.stdout) == (mutant==0),p.stdout
    if mutant:assert 'FAIL' in p.stdout
