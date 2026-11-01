from pathlib import Path
import importlib.util
import subprocess
import pytest
spec=importlib.util.spec_from_file_location('guide_patch',Path(__file__).with_name('orfs_hold_mm.py'))
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

@pytest.mark.parametrize('post_fails',[False,True])
def test_only_successful_post_hook_serializes_final_guide_state(tmp_path,post_fails):
 source='  write_guides $::env(RESULTS_DIR)/route.guide\n'+M.FINAL_GUIDE_ANCHOR+'\n'
 p=tmp_path/'global_route.tcl';p.write_text(source)
 assert M.patch_final_guides(tmp_path)=='patched'
 assert M.patch_final_guides(tmp_path)=='already patched'
 setup='''set ::env(RESULTS_DIR) {ROOT}
set state old
proc write_guides {path} {set f [open $path w];puts $f $::state;close $f}
proc source_step_tcl {args} {set ::state new;FAIL}
proc orfs_write_db {args} {set ::db_state $::state}
'''.replace('ROOT',str(tmp_path)).replace('FAIL','error {actual post-hook failure}' if post_fails else '')
 script=tmp_path/'test.tcl';script.write_text(setup+'set code [catch {\n'+p.read_text()+'} message]\nputs "$code $message"\n')
 r=subprocess.run(['tclsh',str(script)],capture_output=True,text=True,check=True)
 assert (tmp_path/'route.guide').read_text().strip()==('old' if post_fails else 'new')
 assert r.stdout.startswith('1 actual post-hook failure' if post_fails else '0')


def test_unknown_image_is_unchanged(tmp_path):
 p=tmp_path/'global_route.tcl';p.write_text('unrecognized image\n')
 assert 'unchanged' in M.patch_final_guides(tmp_path)
 assert p.read_text()=='unrecognized image\n'


def test_native_guide_export_classification_is_neutral():
    path = Path(__file__).parent / 'closure_loop' / 'helper_overlay.py'
    overlay = importlib.util.spec_from_file_location('guide_overlay', path)
    module = importlib.util.module_from_spec(overlay); overlay.loader.exec_module(module)
    row = module.RULE_COMMITS['5d01b8aa74dd7564d63a3335fefcfc4bdc9828f2']
    assert row['kind'] == 'neutral'
    assert row['paths'] == ('tools/orfs_hold_mm.py',)
    assert 'requires' not in row
