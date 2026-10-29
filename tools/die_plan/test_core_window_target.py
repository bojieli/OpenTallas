import copy
import pytest
import core_infra as CI
from test_core_infra import sample


def vehicle():
    s=sample();s['pg_obstructions_um']={}
    s['core_tree']=dict(clock_port='clk',equal_load=False,load_balance='joint_nldm_plan',nodes=[
        dict(name='root',master='BUFx16f_ASAP7_75t_R',xy_um=[430,430],parent='port:clk'),
        dict(name='a',master='BUFx8_ASAP7_75t_R',xy_um=[420,430],parent='root'),
        dict(name='b',master='BUFx8_ASAP7_75t_R',xy_um=[440,430],parent='root')],
        leaves=[dict(node='a',sinks=['r0/CLK']),dict(node='b',sinks=['r1/CLK','r2/CLK'])],
        model_qualification=dict(measured_timing_used=False,band_policy='info',corners={
            'TT':dict(leaf_min=250,leaf_max=271.32,leaf_window=21.32,slew_max=31.9),
            'FF':dict(leaf_min=200,leaf_max=226.79,leaf_window=26.79,slew_max=24.3)}))
    return s


def test_near_target_window_is_explicit_information_only():
    s=vehicle()
    with pytest.raises(CI.InfraError,match='target FAIL'):CI.emit_tcl(s)
    s['core_tree']['model_qualification']['window_policy']='info'
    tcl=CI.emit_tcl(s)
    assert 'core tap window INFO TT: 21.32' in tcl
    assert 'core tap window INFO FF: 26.79' in tcl
    assert 'actual related-pair STA/setup/hold sign-off unchanged' in tcl


@pytest.mark.parametrize('mut',[
    lambda q:q['corners']['TT'].update(slew_max=81),
    lambda q:q['corners'].pop('FF'),
    lambda q:q.update(measured_timing_used=True),
    lambda q:q.update(band_policy='gate'),
    lambda q:q.update(window_policy='oops')])
def test_info_window_preserves_other_plan_refusals(mut):
    s=vehicle();q=s['core_tree']['model_qualification'];q['window_policy']='info';mut(q)
    with pytest.raises(CI.InfraError):CI.emit_tcl(s)
