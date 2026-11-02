from pathlib import Path
import pytest
from stage_grt import stage


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
        'source /work/native_pg_binding.tcl','ot_pg_native_birth_begin /work/nativepgbirth.so',
        'source {/work/eco_grt_pre.tcl}']
    assert (k/'native_pg_birth_post.tcl').read_text().splitlines()==[
        'source {/work/old_post.tcl}','ot_pg_native_birth_end']
    assert (k/'native_pg_binding.before_birth.tcl').read_text()=='old_helper\n'
    assert r['physical_release'] is False and r['status']=='STAGED_NOT_RUN'


def test_missing_original_hook_refuses_before_mutating_kit(tmp_path):
    k,m,h=fixture(tmp_path);(k/'old_post.tcl').unlink();before={p.name:p.read_bytes()for p in k.iterdir()}
    with pytest.raises(ValueError,match='missing/nonlocal'):stage(k,m,h)
    assert {p.name:p.read_bytes()for p in k.iterdir()}==before


def test_reapplication_refuses_without_overwriting_adapter(tmp_path):
    k,m,h=fixture(tmp_path);stage(k,m,h);before={p.name:p.read_bytes()for p in k.iterdir()}
    with pytest.raises(ValueError,match='existing'):stage(k,m,h)
    assert {p.name:p.read_bytes()for p in k.iterdir()}==before
