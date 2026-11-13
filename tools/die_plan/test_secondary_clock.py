from pathlib import Path
import importlib.util
import shutil
import subprocess
import pytest

HERE = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location('secondary_clock', HERE/'secondary_clock.py')
M = importlib.util.module_from_spec(sp)
sp.loader.exec_module(M)
SPEC = dict(port='pma_rck[0]', clock='pma_rck', target=1000, dmax_um=80., radius_um=200.)


def test_absent_spec_is_noop(tmp_path):
    p = tmp_path/'config.mk';p.write_text('original\n')
    assert not M.install(tmp_path)
    assert p.read_bytes() == b'original\n'
    assert list(tmp_path.iterdir()) == [p]


def test_existing_vector_source_keeps_sdc_and_primary_hook(tmp_path):
    (tmp_path/'config.mk').write_text('export PRE_CTS_TCL = /work/pre_cts.tcl\nexport CTS_ARGS = -repair_clock_nets\n')
    (tmp_path/'pre_cts.tcl').write_text('source /work/clock_taps.tcl\n')
    (tmp_path/'constraint.sdc').write_text('create_clock -name pma_rck -period 833 [get_ports {pma_rck[0]}]\n')
    before=(tmp_path/'constraint.sdc').read_bytes()
    assert M.install(tmp_path, SPEC)
    assert (tmp_path/'constraint.sdc').read_bytes() == before
    assert (tmp_path/'pre_cts.tcl').read_text() == 'source /work/clock_taps.tcl\n'
    cfg=(tmp_path/'config.mk').read_bytes();hook=(tmp_path/'secondary_clock_pre_cts.tcl').read_text()
    assert '{pma_rck[0]}' in hook and hook.startswith('source /work/pre_cts.tcl\n')
    assert 'export CTS_ARGS = -repair_clock_nets' in cfg.decode()
    assert M.install(tmp_path, SPEC) and (tmp_path/'config.mk').read_bytes()==cfg
    with pytest.raises(ValueError, match='another reviewed spec'):
        M.install(tmp_path, dict(SPEC, port='unrelated'))


@pytest.mark.parametrize('patch', [dict(period_ps=900), dict(port='pma_rck;error bad'),
    dict(clock='clk pma_rck'), dict(target=True), dict(target=1501), dict(dmax_um=201)])
def test_no_period_or_unsafe_unbounded_contract(patch):
    with pytest.raises((ValueError,TypeError)): M.validate(dict(SPEC, **patch))


def tcl(script):
    if not shutil.which('tclsh'):pytest.skip('tclsh unavailable')
    return subprocess.run(['tclsh'],input=script,text=True,capture_output=True)


def test_runtime_off_does_not_touch_clock_commands():
    p=tcl('source {'+str(HERE/'secondary_clock_taps.tcl')+'}\nputs "OFF [info commands ::ot_secondary_clock::apply]"\n')
    assert p.returncode==0 and p.stdout.strip()=='OFF' and not p.stderr


def test_runtime_missing_native_input_fails_before_edit():
    p=tcl('''
namespace eval ord {proc get_db_block {} {return blk}}
proc blk {method args} {if {$method eq "findBTerm"} {return NULL};error "unexpected edit"}
set ::ot_secondary_clock_spec [dict create port {pma_rck[0]} clock pma_rck target 1000 dmax_um 80 radius_um 200]
puts "FAIL [catch {source {%s}} msg] $msg"
''' % (HERE/'secondary_clock_taps.tcl'))
    assert 'FAIL 1 SECONDARY_CLOCK requires an existing input root pma_rck[0]' in p.stdout
