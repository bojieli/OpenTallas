"""Type-level source profiles reach every existing frontend via config.mk."""
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_phys as GP
import schema
import rtl_lint
import lec


def tiny():
    return json.loads((Path(__file__).parent/'examples/tiny_plan.json').read_text())


def test_default_profile_unchanged(tmp_path):
    raw=tiny()
    source=tmp_path/'top.sv';source.write_text('module top; endmodule\n')
    kit=GP.write_type_kit(schema.Plan(raw),'src',tmp_path,[source])
    assert 'export VERILOG_DEFINES = -DSYNTHESIS\n' in (kit/'config.mk').read_text()
    assert GP.type_verilog_defines({}) == ['-DSYNTHESIS']


def test_head_native_profile_shared_by_synthesis_lint_and_lec(tmp_path):
    raw=tiny();raw['partition_types']['src']['verilog_defines']=['OT_COLL_NATIVE32','OT_COLL_NATIVE32_OFF']
    assert not schema.validate(raw)
    source=tmp_path/'top.sv';source.write_text('module top; endmodule\n')
    kit=GP.write_type_kit(schema.Plan(raw),'src',tmp_path,[source])
    cfg=(kit/'config.mk').read_text()
    expected=['-DSYNTHESIS','-DOT_COLL_NATIVE32','-DOT_COLL_NATIVE32_OFF']
    assert rtl_lint.config(kit)['VERILOG_DEFINES'] == expected
    assert 'verilog_defines '+' '.join(expected) in rtl_lint.script(kit)
    # LEC's real make-config reader reads the same export used by synthesis.
    env=lec.parse_config(kit)
    assert env['VERILOG_DEFINES'].split() == expected


@pytest.mark.parametrize('value',[['-DFOO'],['FOO=1'],['A B'],['X;touch'],['$(shell x)'],'FOO',[7]])
def test_reject_non_macro_tokens(value):
    raw=tiny();raw['partition_types']['src']['verilog_defines']=value
    assert schema.validate(raw)
    with pytest.raises(ValueError): GP.type_verilog_defines(raw['partition_types']['src'])
