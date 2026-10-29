"""Exercise the actual core pin-site gate with declared and undeclared interior entries."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_legacy as G


def pin(name, x=56.184, y=56.16):
    return dict(name=name, layer='M5', x=x, y=y)


def test_declared_one_clock_and_exact_bus_entries():
    assert G.plan_pin_sites([pin('ck_k')], [112.32]*2, {'clock_port':'ck_k'})['verdict']=='PASS'
    assert G.plan_pin_sites([pin('xk[0]'),pin('xk[1]',40)], [112.32]*2,
        {'clock_port':'xk[0]','clock_ports':['xk[0]','xk[1]']})['verdict']=='PASS'


def test_undeclared_clock_reset_and_default_name_fail():
    for name in ('ck_n','ck_k_fake','rs_k','clk','xk[2]'):
        r=G.plan_pin_sites([pin(name)], [112.32]*2, {'clock_port':'ck_k','clock_ports':['xk[0]']})
        assert r['verdict']=='FAIL' and r['counts']['off_face']==1


def test_declared_clock_still_cannot_stack_or_break_face_pitch():
    r=G.plan_pin_sites([pin('ck_k'),pin('data')], [112.32]*2, {'clock_port':'ck_k'})
    assert r['verdict']=='FAIL' and r['counts']['dup_site']==1
    r=G.plan_pin_sites([pin('ck_k',10,.042),pin('data',10.024,.042)], [112.32]*2, {'clock_port':'ck_k'})
    assert r['verdict']=='FAIL' and r['counts']['pitch']==1


def test_width_one_alias_requires_elaborated_source_width_and_input():
    pins = [pin('clk[0]')]
    spec = {'clock_port':'clk'}
    assert G.plan_pin_sites(pins, [112.32]*2, spec)['verdict'] == 'FAIL'
    assert G.plan_pin_sites(pins, [112.32]*2, spec, {'clk':'INPUT','clk[0]':'INPUT'})['verdict'] == 'PASS'
    # A multi-bit source has no bare key in rtl_port_dirs.
    for dirs in ({'clk[0]':'INPUT','clk[1]':'INPUT'}, {'clk':'OUTPUT','clk[0]':'OUTPUT'}, {'clk':'INPUT','clk[1]':'INPUT'}):
        assert G.plan_pin_sites(pins, [112.32]*2, spec, dirs)['verdict'] == 'FAIL'
