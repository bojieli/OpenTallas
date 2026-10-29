"""The reader comparison keeps its full 32-bit threshold; truncating K would silently alias it."""
import shutil
import re
import subprocess
from pathlib import Path
try:
    import pytest
except ImportError:
    pytest=None


def test_land_reader_explicit_counter_width_preserves_all_thresholds(tmp_path):
    pinned=Path.home()/'.local/opentallas-tools/bin/yosys'
    yosys=str(pinned) if pinned.is_file() else shutil.which('yosys')
    if not yosys:
        raise RuntimeError('yosys required for combinational comparison proof')
    version=subprocess.check_output([yosys,'-V'],text=True)
    vm=re.search(r'Yosys (\d+)\.(\d+)',version)
    if vm and (int(vm[1]),int(vm[2]))<(0,10):
        if pytest:
            pytest.skip('legacy system Yosys lacks the required SystemVerilog size casts; use project Yosys 0.68')
        raise RuntimeError('use project Yosys 0.68')
    source=Path(__file__).resolve().parents[2]/'rtl/common/landed_parent/ot_pl_land.sv'
    assert "if (32'(rc) == K-1) warm <= 1;" in source.read_text()
    sv=tmp_path/'comparison.sv'
    sv.write_text("""module comparison(input wire[2:0] rc,input wire signed[31:0] K,
output wire ok, output wire truncated_ok);
wire old_cmp = rc == K-1;
wire new_cmp = 32'(rc) == K-1;
wire bad_cmp = rc == 3'(K-1);
assign ok=old_cmp==new_cmp;
assign truncated_ok=old_cmp==bad_cmp;
endmodule
""")
    base=f'read_verilog -sv {sv}; prep -top comparison; '
    good=subprocess.run([yosys,'-Q','-T','-p',base+'sat -verify -prove ok 1 -show rc,K'],capture_output=True,text=True)
    (tmp_path/'positive.log').write_text(good.stdout+good.stderr)
    assert good.returncode==0,good.stdout+good.stderr
    # A plausible WIDTH "fix" that narrows K changes behavior for out-of-range/negative thresholds.
    bad=subprocess.run([yosys,'-Q','-T','-p',base+'sat -verify -prove truncated_ok 1 -show rc,K'],capture_output=True,text=True)
    (tmp_path/'truncation_mutant.log').write_text(bad.stdout+bad.stderr)
    assert bad.returncode!=0 and 'proof did fail' in bad.stderr.lower(),bad.stdout+bad.stderr


if __name__=='__main__':
    import sys
    run=Path(sys.argv[1]);run.mkdir(parents=True,exist_ok=False)
    test_land_reader_explicit_counter_width_preserves_all_thresholds(run)
    print('LAND_READER_WIDTH_PASS all32bitK symbolic; truncationmutant CAUGHT')
