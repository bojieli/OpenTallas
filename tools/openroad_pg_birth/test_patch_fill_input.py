from pathlib import Path
import subprocess
import pytest
from patch_fill_input import patch,loader,sha,ANCHOR


def fixture(tmp_path):
    scripts=tmp_path/'scripts';scripts.mkdir()
    (scripts/'fillcell.tcl').write_text('source $::env(SCRIPTS_DIR)/fillcell.native_pg_original.tcl\not_pg_native_birth_end\n')
    (scripts/'fillcell.native_pg_original.tcl').write_bytes(b'unchanged_prefix\n  '+ANCHOR+b'unchanged_suffix\n')
    src=tmp_path/'old/run/results/asap7/L1/base';src.mkdir(parents=True)
    odb=src/'5_2_route.odb';odb.write_bytes(b'genuine_saved_route_fixture')
    sdc=tmp_path/'old/lvt_grt.sdc';sdc.write_text('actual_sdc_fixture\n')
    return scripts,src,odb,sdc


def test_wrapped_input_only_patch_keeps_driver_and_other_stock_bytes(tmp_path):
    scripts,src,odb,sdc=fixture(tmp_path);driver=(scripts/'fillcell.tcl').read_bytes()
    r=patch(scripts,src,odb.name,sdc,sha(odb),sha(sdc),tmp_path/'receipt.json')
    body=(scripts/'fillcell.native_pg_original.tcl').read_bytes()
    assert body==b'unchanged_prefix\n  '+loader(src,odb.name,sdc)+b'unchanged_suffix\n'
    assert (scripts/'fillcell.tcl').read_bytes()==driver
    assert r['sdc_alias_created'] is False and r['dispatch_ready'] is False
    assert not (src/'5_1_grt.sdc').exists()


def test_wrong_input_hash_refuses_before_any_runtime_mutation(tmp_path):
    scripts,src,odb,sdc=fixture(tmp_path);before={p.name:p.read_bytes()for p in scripts.iterdir()}
    with pytest.raises(ValueError,match='hash mismatch'):
        patch(scripts,src,odb.name,sdc,'0'*64,sha(sdc),tmp_path/'receipt.json')
    assert {p.name:p.read_bytes()for p in scripts.iterdir()}==before


@pytest.mark.parametrize('failing',[False,True])
def test_actual_sdc_path_and_output_results_restored_even_on_load_error(tmp_path,failing):
    scripts,src,odb,sdc=fixture(tmp_path)
    body=loader(src,odb.name,sdc).decode()
    harness=tmp_path/'load.tcl'
    harness.write_text('''set ::env(RESULTS_DIR) /finish/run/results
proc load_design {odb sdc} {
 set ::seen_odb [file normalize $::env(RESULTS_DIR)/$odb]
 set ::seen_sdc [file normalize $::env(RESULTS_DIR)/$sdc]
 @FAIL@
}
set code [catch {
@BODY@
} why]
if {$code != @CODE@ || $::seen_odb ne {@ODB@} || $::seen_sdc ne {@SDC@} || $::env(RESULTS_DIR) ne "/finish/run/results" || [info exists ::ot_pg_fill_declared_results]} {error "bad input/output scope $code $why"}
puts PASS
'''.replace('@BODY@',body).replace('@FAIL@','error EXPECTED_LOAD_FAILURE'if failing else'').replace('@CODE@',str(int(failing))).replace('@ODB@',str(odb)).replace('@SDC@',str(sdc)))
    r=subprocess.run(['tclsh',str(harness)],capture_output=True,text=True)
    assert r.returncode==0 and r.stdout.strip()=='PASS',r.stdout+r.stderr
