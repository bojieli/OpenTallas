"""Retention scripts fail closed on changed stages and never keep all DFFs."""
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from w10_wake_synth_preserve import companion, retain


def original():
    return (ROOT/'results/uarch/w10_baseline_wake/retention_diagnostic/orfs_synth_original.tcl').read_text()


def test_narrow_driver_selection_has_eight_count_barriers():
    patched=companion(original())
    assert patched.count('select -assert-count 8 {w:g_wake.g_leaf*.wake}')==2
    assert 'setattr -set keep 1 @ot_wake_proc' in patched
    assert 'setattr -set keep 1 @ot_wake_techmap' in patched
    assert 'opt -fast\n  hierarchy -check' in patched
    assert 'log_cmd abc {*}$abc_args' in patched
    assert '  yosys proc\n  flatten\n' in patched


@pytest.mark.parametrize('old,new',[
    ('-run :fine','-run :changed'),
    ('-run fine: -noabc','-run changed: -noabc'),
    ('} elseif { !$::env(SYNTH_HIERARCHICAL) } {','} elseif { 0 } {'),
])
def test_stage_drift_rejected(old,new):
    with pytest.raises(ValueError):companion(original().replace(old,new))


def test_selection_uses_driver_cells_not_generated_instance_names():
    for stage in ('proc','techmap'):
        script=retain(stage)
        assert '%ci' in script and '@ot_wake_' in script
        assert '$procdff' not in script.split('\n',1)[1]
        assert 'setattr -set keep 1 t:' not in script
