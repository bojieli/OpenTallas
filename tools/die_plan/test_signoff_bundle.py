from pathlib import Path
import subprocess
import sys
import pytest
import signoff


def test_bundle_copies_actual_lazy_dependencies_and_runs_isolated(tmp_path):
    copied=signoff.copy_signoff_bundle(tmp_path/'so_exact')
    assert set(copied)==set(signoff.SIGNOFF_BUNDLE)
    bundle=tmp_path/'so_exact'
    code='''import sys;sys.path.insert(0,sys.argv[1]);import signoff,sdc_lint,face_guard,io_hold_qualification
signoff.require_signoff_bundle()
assert 'ot_lib_load FF /out/libraries.json' in signoff.session_tcl('ff',[],spef=True)
print('STANDALONE_BUNDLE_PASS')'''
    p=subprocess.run([sys.executable,'-I','-c',code,str(bundle)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert 'STANDALONE_BUNDLE_PASS' in p.stdout


@pytest.mark.parametrize('missing',['sdc_lint.py','face_guard.py','io_hold_qualification.py'])
def test_incomplete_bundle_fails_before_partial_output(tmp_path,missing):
    source=tmp_path/'source';signoff.copy_signoff_bundle(source)
    (source/missing).unlink()
    dest=tmp_path/'dest'
    with pytest.raises(ValueError,match=missing.replace('.','\\.')):
        signoff.copy_signoff_bundle(dest,source)
    assert not dest.exists()


def test_marked_ff_core_tap_overlay_copied_and_only_read_at_ff(tmp_path):
    sdc=tmp_path/'constraint.sdc';sdc.write_text('# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc\n')
    (tmp_path/'core_taps_ff.sdc').write_text('set_clock_latency -source -109 [get_ports ck_core]\n')
    out=tmp_path/'sdcdir'
    assert signoff.copy_core_tap_overlay(sdc,out)
    assert (out/'core_taps_ff.sdc').read_text()==(tmp_path/'core_taps_ff.sdc').read_text()
    ff=signoff.session_tcl('ff',[],True,core_taps_ff=True)
    tt=signoff.session_tcl('tt',[],True,core_taps_ff=True)
    assert ff.index('read_sdc /sdc/golden.sdc')<ff.index('read_sdc /sdc/core_taps_ff.sdc')
    assert 'read_sdc /sdc/core_taps_ff.sdc' not in tt


def test_missing_marked_overlay_rejected_and_unmarked_stale_file_ignored(tmp_path):
    golden=tmp_path/'constraint.sdc';golden.write_text('# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc\n')
    with pytest.raises(ValueError,match='missing marked'):signoff.copy_core_tap_overlay(golden,tmp_path/'out')
    golden.write_text('create_clock -period 833 [get_ports clk]\n')
    (tmp_path/'core_taps_ff.sdc').write_text('BAD_STALE_OVERLAY')
    assert not signoff.copy_core_tap_overlay(golden,tmp_path/'out')
    assert not (tmp_path/'out/core_taps_ff.sdc').exists()


def test_ambiguous_or_path_overlay_marker_rejected(tmp_path):
    golden=tmp_path/'constraint.sdc'
    for text in ['# OT_CORE_TAP_CORNER_FILE ../outside.sdc\n','# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc\n'*2]:
        golden.write_text(text)
        with pytest.raises(ValueError,match='malformed or ambiguous'):signoff.copy_core_tap_overlay(golden,tmp_path/'out')

@pytest.mark.parametrize('corner,marker,available,expected',[
    ('TT',True,True,'READS 0'),('FF',True,True,'READS 1'),
    ('FF',True,False,'missing marked'),('FF',False,True,'READS 0'),
])
def test_postcts_actual_tcl_overlay_fragment(tmp_path,corner,marker,available,expected):
    source=(Path(signoff.__file__).with_name('postcts_gate.tcl')).read_text()
    fragment=source[source.index('set ot_core_tap_fd'):source.index('set bound')].replace('/work/',str(tmp_path)+'/')
    (tmp_path/'constraint.sdc').write_text('# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc\n' if marker else '# no overlay\n')
    if available:(tmp_path/'core_taps_ff.sdc').write_text('set_clock_latency -source -109 [get_ports ck_core]\n')
    script=tmp_path/'probe.tcl';script.write_text('set C '+corner+'\nset reads 0\nproc read_sdc {p} {incr ::reads}\n'+fragment+'\nputs "READS $reads"\n')
    result=subprocess.run(['tclsh',str(script)],text=True,capture_output=True)
    if expected=='missing marked':assert result.returncode!=0 and expected in result.stderr
    else:assert result.returncode==0 and expected in result.stdout,result.stderr
