"""The opt-in central-fence hook runs after boundary cells and remains source-bound."""
from pathlib import Path
import sys
import subprocess
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ref_tile as R

HOOK = 'physical/common_flow/pin_reg_split.tcl'
BASE = dict(name='probe',kind='tile',recipe=3,clock='cts',pins={},sources=[],macros=[],children=[],route={},io_flop_at_pins={'through_frac':None},inhold=True)


def test_runs_after_boundary_fixing_and_is_source_bound():
    s = dict(BASE, pin_hook_after_flops=[HOOK])
    text = R.gen_pin_hooks(s)['pre_gpl.tcl']
    script = 'set order {}; proc source {p} {lappend ::order [file tail $p]}\n'
    p = subprocess.run(['tclsh'], input=script+text+'\nputs $order\n',capture_output=True,text=True)
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip().split() == ['leaf_inhold.tcl','io_flop_at_pins.tcl','pin_reg_split.tcl']
    assert HOOK in R.referenced_paths(s,'physical/ref_tile/probe')


def test_default_generation_is_identical():
    assert R.gen_pin_hooks(BASE) == R.gen_pin_hooks(dict(BASE,pin_hook_after_flops=[]))


@pytest.mark.parametrize('bad',['/tmp/x.tcl','../x.tcl','bad;exec.tcl','physical/missing.tcl'])
def test_unsafe_or_missing_hook_refuses(bad):
    with pytest.raises(R.SpecError): R.gen_pin_hooks(dict(BASE,pin_hook_after_flops=[bad]))


def test_hook_requires_wrapper():
    with pytest.raises(R.SpecError): R.gen_pin_hooks(dict(BASE,recipe=1,pin_hook_after_flops=[HOOK]))
