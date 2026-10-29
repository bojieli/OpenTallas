"""Compiler coverage output must not shadow production RTL definitions."""
from pathlib import Path
import bind_elab as E
import bind


def put(root,path,text):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p


def test_automatic_coverage_duplicate_cannot_shadow_canonical_reset(tmp_path):
    canonical=put(tmp_path,'rtl/lib/ot_reset_sync.sv','module ot_reset_sync(input clk); wire a=clk; endmodule\n')
    bad=put(tmp_path,'rtl/build/coverage_probe/merged_annotated/ot_reset_sync.sv',
            '%000007 module ot_reset_sync(input wrong_abi); endmodule\nmodule bad_probe; endmodule\n')
    # Coverage annotations may themselves still parse a later module definition.
    bad.write_text('module ot_reset_sync(input wrong_abi);\n%000007 illegal_coverage_text\nendmodule\n')
    idx=E.module_index(['rtl'],[],tmp_path)
    assert idx['ot_reset_sync']==[str(canonical)]
    picks={};files,missing,macros=bind.kit_closure(['ot_reset_sync'],idx,[],picks)
    assert files==[str(canonical)] and not missing and not macros
    assert picks['ot_reset_sync']==str(canonical)


def test_generated_production_rtl_and_explicit_files_remain_selectable(tmp_path):
    canonical=put(tmp_path,'rtl/lib/leaf.sv','module leaf(input original); endmodule\n')
    generated=put(tmp_path,'rtl/generated/normal.sv','module normal; endmodule\n')
    intentional=put(tmp_path,'rtl/build/custom.sv','module leaf(input selected); endmodule\n')
    bench=put(tmp_path,'rtl/test/bench.sv','module explicit_bench; endmodule\n')
    idx=E.module_index(['rtl'],[str(intentional),str(bench)],tmp_path)
    assert idx['normal']==[str(generated)] and idx['explicit_bench']==[str(bench)]
    assert E.pick(idx,'leaf',[str(intentional)])==(str(intentional),False)
    # A concrete preference alone also remains an explicit override after pool filtering.
    auto=E.module_index(['rtl'],[],tmp_path)
    assert E.pick(auto,'leaf',[str(intentional)])==(str(intentional),False)
    # Naming the directory itself as an explicit root opts into that pool.
    assert str(intentional) in E.module_index(['rtl/build'],[],tmp_path)['leaf']
    assert str(canonical) in idx['leaf']


def test_only_known_output_components_are_filtered(tmp_path):
    keep=put(tmp_path,'rtl/rebuild_engine/mod.sv','module good; endmodule\n')
    skip=put(tmp_path,'rtl/obj_dir/mod.sv','module hidden; endmodule\n')
    idx=E.module_index(['rtl'],[],tmp_path)
    assert idx['good']==[str(keep)] and 'hidden' not in idx
    assert E.module_index([str(skip)],[],tmp_path)['hidden']==[str(skip)]
