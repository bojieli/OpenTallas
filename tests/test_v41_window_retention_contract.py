import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('ret',Path(__file__).resolve().parents[1]/'tools/v41_window_retention_contract.py')
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)

def desc(role):
    d=dict(user=0,layer=0,pos=199999,region_base=100000,region_count=900000,stack=0,step_epoch=4,source_epoch=9,mode='WINDOW_FP8',role=role,js=0,hg=1,mmode=1,wbase=0)
    d.update(dict(ts=512,ks=1,k=512,nout=128,tiles=4) if role=='qk' else dict(ts=1,ks=32,k=128,nout=512,tiles=16))
    return d

def arm():
    c=r.Retention();c.complete_qk(desc('qk'),complete_rows=128,engine_idle=True,drained=True);return c

def test_different_descriptors_same_content_new_generation():
    assert r.canonical(desc('qk'))==r.canonical(desc('pv'))
    c=arm();assert c.accept_pv(desc('pv'),drained=True,mutation_pending=False,fresh_generation=True)
    assert not c.accept_pv(desc('pv'),drained=True,mutation_pending=False,fresh_generation=True)

@pytest.mark.parametrize('field,value',[('user',1),('layer',1),('pos',200000),('source_epoch',10),('region_base',200000),('region_count',1),('stack',1),('step_epoch',5),('mode','CKV_FP4'),('k',127),('ks',1),('js',1),('wbase',1)])
def test_identity_and_shape_changes_miss(field,value):
    d=desc('pv');d[field]=value
    assert not arm().accept_pv(d,drained=True,mutation_pending=False,fresh_generation=True)

@pytest.mark.parametrize('drained,pending,fresh',[(False,False,True),(True,True,True),(True,False,False)])
def test_hazards_cannot_return_ready(drained,pending,fresh):
    assert not arm().accept_pv(desc('pv'),drained=drained,mutation_pending=pending,fresh_generation=fresh)

def test_write_invalidates_at_accept_not_completion():
    c=arm();c.invalidate()
    assert not c.accept_pv(desc('pv'),drained=True,mutation_pending=False,fresh_generation=True)

def test_partial_fill_does_not_arm():
    c=r.Retention();c.complete_qk(desc('qk'),complete_rows=127,engine_idle=True,drained=True)
    assert not c.accept_pv(desc('pv'),drained=True,mutation_pending=False,fresh_generation=True)

def test_actual_intervening_instructions_do_not_write_kv():
    d=r.build();assert d['qk']['pc']==24 and d['pv']['pc']==32

def test_retention_rtl_identity_and_hazards(tmp_path):
    import shutil, subprocess
    if not shutil.which('iverilog'):
        pytest.skip('Icarus unavailable')
    root=Path(__file__).resolve().parents[1]
    output=tmp_path/'retention.vvp'
    subprocess.run(['iverilog','-g2012','-s','tb_v41x_window_retention','-o',str(output),str(root/'rtl/chip/ot_chip_v41x_window_retention.sv'),str(root/'rtl/test/tb_v41x_window_retention.sv')],check=True,capture_output=True,text=True)
    result=subprocess.run(['vvp',str(output)],check=True,capture_output=True,text=True)
    assert 'RETENTION_PASS identity_bits=320 hazards=9 single_use=1 late_invalidate=1' in result.stdout
