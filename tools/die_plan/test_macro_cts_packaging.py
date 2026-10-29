import subprocess
from pathlib import Path
from tools.die_plan import kit_modes, signoff

HERE=Path(__file__).resolve().parent


def test_standalone_and_repository_lookup(tmp_path):
    tail=(HERE.parent/'orfs_hold_mm.tcl').read_text().split('# MACRO-CLK (2026-10-10):',1)[1]
    tail='# MACRO-CLK (2026-10-10):'+tail
    for standalone in (True,False):
        root=tmp_path/str(standalone); tools=root/'tools';tools.mkdir(parents=True)
        script=tools/'orfs_hold_mm.tcl';script.write_text(tail)
        helper=(tools if standalone else root/'physical/common_flow')/'macro_cts_cluster.tcl'
        helper.parent.mkdir(parents=True,exist_ok=True)
        helper.write_text('puts ACTUAL_MACRO_HELPER_LOADED\n')
        r=subprocess.run(['tclsh',str(script)],text=True,capture_output=True)
        assert r.returncode==0 and 'ACTUAL_MACRO_HELPER_LOADED' in r.stdout
        assert 'unavailable' not in r.stdout


def test_signoff_bundle_carries_selected_standalone_macro_helper(tmp_path):
    (tmp_path/'orfs_hold_mm.tcl').write_text('# copied route hook\n')
    signoff.copy_signoff_bundle(tmp_path)
    assert (tmp_path/'macro_cts_cluster.tcl').read_bytes()==(HERE.parents[1]/'physical/common_flow/macro_cts_cluster.tcl').read_bytes()
    assert (tmp_path/'orfs_hold_mm.tcl').read_text()=='# copied route hook\n'
