"""The declared type-local sender/receiver contract survives modern window and demand handling."""
import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_phys as GP
import schema
import sdc_lint
import test_io_hold as OLD


def plan(window=False):
    raw=copy.deepcopy(OLD.PAIR)
    raw['partition_types']['fb'].setdefault('clock',{})['out_hold_check_ps']=40
    raw['partition_types']['fa'].setdefault('clock',{})['io_hold']='sender_min'
    if window:
        raw['clock']['seam_hold']=dict(sender_ps=25,seam_ps=80)
        raw['clock']['tap_window']=dict(window_ps=80)
    return schema.Plan(raw)


def test_sender_and_receiver_check_the_same_forty_ps(tmp_path):
    P=plan()
    assert GP.io_hold_mode(P)=='legacy' and GP.io_hold_mode(P,'fa')=='sender_min'
    assert GP.hold_out_min_ps(P,'fb')==-27.5
    assert GP.hold_out_min_ps(P,'fa')==0
    assert GP.input_hold_min(P,'fa')['r_i']['in_min_ps']==40
    assert GP.input_hold_min(P,'fb')=={}
    assert GP.sender_out_guarantee_ps(P,'fb')==(40,'sender kit check fb')
    for tn in ['fa','fb']:
        sdc=GP.sdc(P,tn,GP.type_pins(P,tn));ctx=sdc_lint.kit_context(P,tn)
        assert sdc_lint.lint(sdc,**ctx)==[]
    kit=GP.write_type_kit(P,'fb',tmp_path,[])
    assert 'export OT_HOLD_OUT_MIN = -27.5000\n' in (kit/'config.mk').read_text()
    assert sdc_lint.kit_context(P,'fb')['hold_out_min_ps']==-27.5


def test_window_added_once_after_type_sender_check(tmp_path):
    P=plan(window=True)
    assert GP.hold_out_min_sdc_ps(P,'fb')==52.5
    sdc=GP.sdc(P,'fb',GP.type_pins(P,'fb'))
    assert 'set_output_delay -min 52.5000 -clock vclk [all_outputs]' in sdc
    assert sdc_lint.lint(sdc,**sdc_lint.kit_context(P,'fb'))==[]
    kit=GP.write_type_kit(P,'fb',tmp_path,[])
    assert 'export OT_HOLD_OUT_MIN = 52.5000\n' in (kit/'config.mk').read_text()
    assert sdc_lint.kit_context(P,'fb')['hold_out_min_ps']==-27.5


def test_type_override_preserves_other_plan_demand_receivers():
    P=plan();P.clock['io_hold']='plan_demand'
    assert GP.io_hold_mode(P,'fa')=='sender_min'
    assert GP.io_hold_mode(P,'fb')=='plan_demand'
    assert GP.input_hold_min(P,'fa')['r_i']['in_min_ps']==40


def test_absent_type_fields_have_identical_sdc_and_context():
    P=OLD._plan();raw=copy.deepcopy(P.raw)
    for typ in raw['partition_types'].values(): typ.setdefault('clock',{})
    empty=schema.Plan(raw)
    for tn in ['fa','fb']:
        assert GP.sdc(P,tn,GP.type_pins(P,tn))==GP.sdc(empty,tn,GP.type_pins(empty,tn))
        assert sdc_lint.kit_context(P,tn)==sdc_lint.kit_context(empty,tn)
