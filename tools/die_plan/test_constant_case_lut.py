from pathlib import Path
import re
import shutil
import subprocess
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from constant_case_lut import rewrite
ROOT=Path(__file__).resolve().parents[2]


def test_actual_coefficient_table_exhaustive_and_mutant(tmp_path):
    if not shutil.which('iverilog'):pytest.skip('iverilog unavailable')
    source=(ROOT/'rtl/hdc/ot_hdc_sfu_q.sv').read_text();new,r=rewrite(source)
    assert r['default_zero_rows']==[128,129] and r['added_cycles']==0
    pat=r'    function automatic \[63:0\] ln2_nk\(.*?    endfunction'
    oldfn=re.search(pat,source,re.S)[0].replace('ln2_nk','oldfn')
    newfn=re.search(pat,new,re.S)[0].replace('ln2_nk','newfn')
    tb='''integer i;initial begin for(i=0;i<256;i=i+1) if(oldfn(i[7:0])!==newfn(i[7:0])) $fatal(1,"coefficient differs%0d",i);$display("TABLE256PASS");$finish;end endmodule'''
    def run(fn,name):
        p=tmp_path/(name+'.sv');p.write_text('module tb;\n'+oldfn+'\n'+fn+'\n'+tb);exe=tmp_path/name
        subprocess.run(['iverilog','-g2012','-DSYNTHESIS','-s','tb','-o',str(exe),str(p)],check=True,capture_output=True,text=True)
        return subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
    assert run(newfn,'nominal').returncode==0
    # Flip one actual decoder coefficient bit.
    bad=re.sub(r"(64'h)([0-9a-f]{16})",lambda m:m[1]+format(int(m[2],16)^1,'016x'),newfn,count=1)
    assert run(bad,'wrong_coefficient').returncode!=0
