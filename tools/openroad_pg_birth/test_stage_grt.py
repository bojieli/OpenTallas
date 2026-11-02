from pathlib import Path
import subprocess
import pytest
from stage_grt import stage, DRIVER


def fixture(tmp_path):
    k=tmp_path/'kit';k.mkdir()
    c=k/'config.mk';c.write_text('export OT_ECO_GRT_PRE_CHAIN = /work/old_pre.tcl\nexport PRE_GLOBAL_ROUTE_TCL = /work/eco_grt_pre.tcl\nexport POST_GLOBAL_ROUTE_TCL = /work/old_post.tcl\n')
    (k/'eco_grt_pre.tcl').write_text('source $::env(OT_ECO_GRT_PRE_CHAIN)\n')
    (k/'old_post.tcl').write_text('existing_post\n')
    (k/'native_pg_binding.tcl').write_text('old_helper\n')
    m=tmp_path/'module.so';m.write_bytes(b'module_fixture_not_a_runtime_capability')
    h=tmp_path/'helper.tcl';h.write_text('new_helper\n')
    return k,m,h


def test_outermost_pre_and_last_post_preserve_existing_access_chain(tmp_path):
    k,m,h=fixture(tmp_path);before=(k/'config.mk').read_bytes()
    r=stage(k,m,h)
    assert (k/'config.mk').read_bytes().startswith(before)
    assert (k/'native_pg_birth_pre.tcl').read_text().splitlines()==[
        'source /work/native_pg_binding.tcl',
        'if {![ot_pg_strict_enabled]} {error OT_PG_GRT_REQUIRES_STRICT_MODE}',
        'ot_pg_native_birth_begin /work/nativepgbirth.so',
        'source {/work/eco_grt_pre.tcl}']
    assert (k/'native_pg_birth_post.tcl').read_text().splitlines()==[
        'source {/work/old_post.tcl}','ot_pg_native_birth_end']
    assert (k/'native_pg_binding.before_birth.tcl').read_text()=='old_helper\n'
    assert r['physical_release'] is False and r['status']=='STAGED_NOT_RUN'
    assert r['dispatch_ready'] is False and r['required_env']=={'OT_PG_STRICT':'1'}


def test_missing_original_hook_refuses_before_mutating_kit(tmp_path):
    k,m,h=fixture(tmp_path);(k/'old_post.tcl').unlink();before={p.name:p.read_bytes()for p in k.iterdir()}
    with pytest.raises(ValueError,match='missing/nonlocal'):stage(k,m,h)
    assert {p.name:p.read_bytes()for p in k.iterdir()}==before


def test_reapplication_refuses_without_overwriting_adapter(tmp_path):
    k,m,h=fixture(tmp_path);stage(k,m,h);before={p.name:p.read_bytes()for p in k.iterdir()}
    with pytest.raises(ValueError,match='existing'):stage(k,m,h)
    assert {p.name:p.read_bytes()for p in k.iterdir()}==before


@pytest.mark.parametrize('body,cleanup_error,expected', [
    ('error ORIGINAL_BODY_FAILURE', False, 'ORIGINAL_BODY_FAILURE'),
    ('error ORIGINAL_BODY_FAILURE', True, 'ORIGINAL_BODY_FAILURE'),
    ('set body_pass 1', True, 'CLEANUP_FAILURE'),
    ('set body_pass 1', False, '')])
def test_driver_cleans_up_original_hook_body_failures(tmp_path, body, cleanup_error, expected):
    (tmp_path/'global_route.tcl').write_text(body+'\n')
    driver=tmp_path/'driver.tcl';driver.write_text(DRIVER)
    script = """set ::env(SCRIPTS_DIR) {@DIR@}
set ::ended 0
proc ot_native_pg_status {} {return {active 1}}
proc ot_pg_native_birth_end {} {incr ::ended; @CLEANUP@}
set code [catch {source {@DRIVER@}} result]
if {$code != @CODE@ || $result ne {@EXPECTED@} || $::ended != 1} {error "unexpected result code=$code result=$result ended=$::ended"}
puts PASS
""".replace('@DIR@',str(tmp_path)).replace('@DRIVER@',str(driver)).replace('@CODE@',str(int(bool(expected)))).replace('@EXPECTED@',expected).replace('@CLEANUP@','error CLEANUP_FAILURE' if cleanup_error else '')
    harness=tmp_path/'harness.tcl';harness.write_text(script)
    r=subprocess.run(['tclsh',str(harness)],text=True,capture_output=True)
    assert r.returncode==0 and r.stdout.strip()=='PASS',r.stdout+r.stderr
