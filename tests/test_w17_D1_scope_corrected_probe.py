import importlib.util
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('scope_review',ROOT/'tools/w17_D1_scope_corrected_probe.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
A=ROOT/m.OLD/'source_authority'
DIE=(A/'rtl/w17_runtime/chip/ot_chip_v41x_die.sv').read_text()
CORE=(A/'rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv').read_text()
COPY=(ROOT/m.B/'ot_v41_rt_die_D1_scope.sv').read_text()


def test_portable_scope_review():
    r=m.verify(ROOT)
    assert r['WINDOW_names']==10 and r['core_fields']==13
    assert not r['compiled'] and not r['runtime_admitted']


def test_actual_failed_copy_is_negative_control():
    failed=(ROOT/m.previous.BENCH/'ot_v41_rt_die_D1_current.sv').read_text()
    with pytest.raises(ValueError,match='Unqualified root WINDOW'):
        m.check_paths(failed,DIE,CORE)


@pytest.mark.parametrize('name',m.WINDOW)
def test_one_unqualified_bus_reference_rejected(name):
    mutant=COPY.replace('dut.g_packed_kv.'+name,'dut.'+name)
    with pytest.raises(ValueError,match='Unqualified root WINDOW'):
        m.check_paths(mutant,DIE,CORE)


@pytest.mark.parametrize('name',m.WINDOW)
def test_each_real_bus_declaration_has_generate_scope(name):
    locations=m.declarations(DIE,{name})[name]
    assert locations and all(x['scope']==['g_packed_kv'] for x in locations)
    changed=DIE.replace('begin : g_packed_kv','begin : g_other_scope')
    with pytest.raises(ValueError,match='declaration scope'):
        m.check_paths(COPY,changed,CORE)


def test_wrong_ancestor_is_rejected():
    tile=(A/'rtl/w17_runtime/chip/ot_chip_v41x_tile.sv').read_text()
    m.instance(tile,'ot_hdc_core_v41x','u_core',())
    with pytest.raises(ValueError,match='Wrong ancestor'):
        m.instance(tile,'ot_hdc_core_v41x','wrong_u_core',())


def test_provider_wrong_generated_branch_rejected():
    m.instance(DIE,'ot_chip_v41x_window_attn_source','u_source',('g_packed_kv','g_window_hbm_attention'))
    with pytest.raises(ValueError,match='Wrong ancestor'):
        m.instance(DIE,'ot_chip_v41x_window_attn_source','u_source',('g_packed_kv',))


def test_scope_lexer_ignores_comments_and_literals():
    source='module m; /* begin : fake */ generate if(1)begin:g_real\nwire a,b;\ninitial begin $display("end begin : wrong");end\nend endgenerate endmodule'
    assert m.declarations(source,{'a','b'})=={
        'a':[{'scope':['g_real'],'line':2}],
        'b':[{'scope':['g_real'],'line':2}]}


def test_full_inverse_and_path_only_difference():
    canonical=COPY.replace('ot_v41_rt_die_D1_scope','ot_v41_rt_die_D1_current')
    inverse=m.previous.inverse_wrapper(canonical)
    assert inverse==(A/'rtl/test/v41_runtime/ot_v41_rt_die.sv').read_text()
    assert '.FULL_SHAPE(1)' in COPY and '.WINDOW_HBM_ATTENTION(1)' in COPY
    assert 'parameter bit SIM_D1=0' in COPY


def test_actual_failure_retained_and_no_go_transfer():
    e=ROOT/m.E
    record=json.loads((e/'correction_record.json').read_text())
    assert record['actual_error_count']==20
    assert record['parent_reported_exit']==1
    assert record['failed_source_commit']=='99e8f0df14453c64262e5cb165517289ce0140a6'
    log=(e/'original_frontend_FAILURE.log').read_text()
    assert "Can't find definition of 'w_wdone'" in log
    go=json.loads((e/'frontend_GO_template.json').read_text())
    assert not go['authorized'] and not go['old_GO_reusable']
    assert not go['native_authorized'] and not go['runtime_authorized']


def test_caps_and_nonobservational_fields_preserved():
    old=json.loads((ROOT/m.OLD/'plan.json').read_text())
    new=json.loads((ROOT/m.E/'plan.json').read_text())
    assert new['caps']==old['caps']
    assert new['source_geometry']==old['source_geometry']
    assert new['commands']['runtime']==old['commands']['runtime']
    assert not new['historical_attention_reused']


def test_bench_and_native_inverse_are_namespace_only():
    bench=(ROOT/m.B/'tb_D1_scope_core.sv').read_text()
    assert bench.replace('tb_D1_scope_core','tb_D1_current_core').replace('ot_v41_rt_die_D1_scope','ot_v41_rt_die_D1_current')==(ROOT/m.previous.BENCH/'tb_D1_current_core.sv').read_text()
    native=(ROOT/m.B/'native_main_scope.cpp').read_text()
    assert native.replace('Vtb_D1_scope_core','Vtb_D1_current_core')==(ROOT/m.previous.BENCH/'native_main.cpp').read_text()
