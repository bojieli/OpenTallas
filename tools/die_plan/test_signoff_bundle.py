from pathlib import Path
import subprocess
import sys
import pytest
import signoff


def test_bundle_copies_actual_lazy_dependencies_and_runs_isolated(tmp_path):
    copied=signoff.copy_signoff_bundle(tmp_path/'so_exact')
    assert set(copied)==set(signoff.SIGNOFF_BUNDLE) | set(signoff.OPTIONAL_SIGNOFF_BUNDLE)
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
    fragment=source[source.index('set ot_core_tap_fd'):source.index('set ot_pg_bound')].replace('/work/',str(tmp_path)+'/')
    (tmp_path/'constraint.sdc').write_text('# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc\n' if marker else '# no overlay\n')
    if available:(tmp_path/'core_taps_ff.sdc').write_text('set_clock_latency -source -109 [get_ports ck_core]\n')
    script=tmp_path/'probe.tcl';script.write_text('set C '+corner+'\nset ot_pg_C '+corner+'\nset reads 0\nproc read_sdc {p} {incr ::reads}\n'+fragment+'\nputs "READS $reads"\n')
    result=subprocess.run(['tclsh',str(script)],text=True,capture_output=True)
    if expected=='missing marked':assert result.returncode!=0 and expected in result.stderr
    else:assert result.returncode==0 and expected in result.stdout,result.stderr


def test_gate_bundle_closes_dependencies_and_preserves_custom_hook(tmp_path):
    target = tmp_path / "kit"
    signoff.copy_signoff_bundle(target, extra=("postcts_gate.tcl",))
    assert (target / "pinreg_measure.tcl").is_file()
    assert (target / "clock_family.tcl").is_file()
    (target / "postcts_gate.tcl").write_text("# KIT-SPECIFIC GATE\n")
    (target / "pinreg_measure.tcl").unlink()
    signoff.copy_signoff_bundle(target)
    assert (target / "postcts_gate.tcl").read_text() == "# KIT-SPECIFIC GATE\n"
    script = 'source {' + str(target / "pinreg_measure.tcl") + '}\n'
    script += 'foreach p {ot_pinreg_set ot_pinreg_arr} {if {![llength [info commands $p]]} {error "missing $p"}}\n'
    r = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stderr


def test_requested_gate_dependency_missing_fails_before_copy(tmp_path):
    source = tmp_path / "source"
    signoff.copy_signoff_bundle(source)
    (source / "postcts_gate.tcl").write_text("source /work/pinreg_measure.tcl\n")
    target = tmp_path / "kit"
    with pytest.raises(ValueError, match="pinreg_measure"):
        signoff.copy_signoff_bundle(target, source, extra=("postcts_gate.tcl",))
    assert not target.exists()


def test_legacy_bundle_without_optional_witness_still_runs(tmp_path):
    source=tmp_path/'source';signoff.copy_signoff_bundle(source)
    for name in signoff.OPTIONAL_SIGNOFF_BUNDLE:
        (source/name).unlink()
    copied=signoff.copy_signoff_bundle(tmp_path/'legacy',source)
    assert set(copied)==set(signoff.SIGNOFF_BUNDLE)
    code="import sys;sys.path.insert(0,sys.argv[1]);import signoff;signoff.require_signoff_bundle();assert 'CHILD_CLOCK_WITNESS' not in signoff.session_tcl('tt',[],True)"
    result=subprocess.run([sys.executable,'-I','-c',code,str(tmp_path/'legacy')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_passive_capture_reuses_only_the_existing_native_graph():
    default=signoff.session_tcl('tt',[],True)
    retained=signoff.session_tcl('tt',[],True,retain_child_clock_witness=True)
    assert retained.count('ot_ps_related $::ot_ps_R')==default.count('ot_ps_related $::ot_ps_R')==1
    assert retained.count('set ::ot_ps_R [ot_ps_regs]')==default.count('set ::ot_ps_R [ot_ps_regs]')==1
    assert 'set P $::ot_ps_retained_pairs' in retained
    assert retained.index('OT_CHILD_CLOCK_WITNESS tt COMPLETE') < retained.index('set so_regs {}')
    assert 'CHILD_CLOCK_WITNESS_FAILED' in retained


def test_explicit_engine_bundle_closes_dynamic_native_dependencies(tmp_path):
    target=tmp_path/'engine'
    signoff.copy_signoff_bundle(target,extra=('lec.py',))
    for name in ('lec.py','native_stub_metadata.py','native_bb.py','manifest_paths.py'):
        assert (target/name).read_bytes()==(Path(signoff.__file__).parent/name).read_bytes()
    code='''import sys
sys.path.insert(0,sys.argv[1])
import lec,native_stub_metadata,manifest_paths
assert lec.cons_base_coverage([None],[[0],[1]])['covered']
assert native_stub_metadata._native_bb().__file__.endswith('native_bb.py')
print('COMPLETE_ENGINE_BUNDLE_PASS')
'''
    result=subprocess.run([sys.executable,'-I','-c',code,str(target)],text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    assert 'COMPLETE_ENGINE_BUNDLE_PASS' in result.stdout


def test_missing_dynamic_engine_dependency_refuses_before_partial_output(tmp_path):
    source=tmp_path/'source'
    signoff.copy_signoff_bundle(source,extra=('lec.py',))
    (source/'native_bb.py').unlink()
    target=tmp_path/'target'
    with pytest.raises(ValueError,match='native_bb'):
        signoff.copy_signoff_bundle(target,source,extra=('lec.py',))
    assert not target.exists()
