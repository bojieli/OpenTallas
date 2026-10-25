"""Explicit lifted reset vectors must cover the exact planned core instances."""
from pathlib import Path
from types import SimpleNamespace
import copy
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind
import reset_tree as RT
from test_bind_wavefront import emitter, plan


def fixture():
    raw = plan()
    raw['partition_types']['src']['hard_cores'] = [dict(inst='u_parent.u_c'+str(i), module='hard'+str(i),
        origin_um=[50+i*50, 50], outline_um=[30, 30], pins=[dict(name='rst_n', layer='M4', xy=[0, 15])]) for i in range(2)]
    b = emitter(raw)
    part = next(p for p in b.parts if b.parts[p]['type']=='src')
    b.ab['reset_lifts'] = {'parent':dict(port='ot_core_rst_n',enable='OT_HIER_RST',targets=[
        dict(inst='u_c'+str(i),pin='rst_n',module='hard'+str(i),source_role='external_distribution') for i in range(2)])}
    c=SimpleNamespace(path='die.u_parent',ports={'rst_n':[1]},module='parent',params={},ytype='parent')
    b.F.cells=[c];b.G.dirs={0:{'rst_n':'input'}};b.G.kind=['leaf'];b.members[part]=[0]
    b.sinks={(0,'rst_n',0):('rst','low')};b.rel_of=lambda ci:'core'
    b.lift_interfaces={('parent','parent'):dict(ports={'ot_core_rst_n':dict(direction='input',bits=[2,3])},parameters={'OT_HIER_RST':'0'})}
    return b,part


def test_extra_vector_carries_each_planned_tap_in_slot_order():
    b,p=fixture();text,_=b.emit_type('src',p)
    taps={x['inst']:x['tap'] for x in RT.for_type(b.wavefront_plan(),'src')['core_resets']}
    assert '.OT_HIER_RST(1)' in text
    assert f'.ot_core_rst_n({{rst_n_t{taps["u_parent.u_c1"]}, rst_n_t{taps["u_parent.u_c0"]}}})' in text


@pytest.mark.parametrize('mutation,reason', [('wrong_target','expected one planned core'),('private','private or unknown'),('duplicate','more than once'),('real_connection','already supplies'),('wrong_width','declared input width')])
def test_rejects_unapproved_or_ambiguous_lift(mutation,reason):
    b,p=fixture();slots=b.ab['reset_lifts']['parent']['targets']
    if mutation=='wrong_target':slots[0]['inst']='u_wrong'
    if mutation=='private':slots[0]['source_role']='private_core'
    if mutation=='duplicate':slots[1]=copy.deepcopy(slots[0])
    if mutation=='real_connection':b.F.cells[0].ports['ot_core_rst_n']=[10,11]
    if mutation=='wrong_width':b.lift_interfaces[('parent','parent')]['ports']['ot_core_rst_n']['bits']=[2]
    with pytest.raises(bind.BindError,match=reason):b.emit_type('src',p)
