import importlib.util
from pathlib import Path
import re
import pytest
spec=importlib.util.spec_from_file_location('recovery_prepare',Path(__file__).parents[1]/'tools/w17_window_recovery_prepare.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_added_copy_defaults_preserve_literal_healthy_implementation(tmp_path):
    out=tmp_path/'copies';records=m.prepare(out)
    renames={m.split_module(m.read_origin(*v))[2]:m.split_module(m.read_origin(*v))[2]+'_recovery_legacy' for v in m.ORIGINS.values()}
    for f,origin in m.ORIGINS.items():
        original=m.read_origin(*origin);copied=(out/f).read_text();name=m.split_module(original)[2]
        a=copied.index('module '+name+'_recovery_legacy');b=copied.index('endmodule',a)+len('endmodule')
        # Timescale/preamble are outside module, compare canonical whole body.
        restored=copied[a:b]
        for old,new in renames.items():restored=re.sub(r'\b'+new+r'\b',old,restored)
        oa=original.index('module ');ob=original.index('endmodule',oa)+len('endmodule')
        assert restored==original[oa:ob]
        assert 'generate if (!OPT_RECOVERY) begin : g_legacy' in copied
        assert records[f]['default_branch_inverse_rename_byte_identical']
        _,_,_,_,_,ports=m.split_module(copied)
        controls=[p for p in ports if p.startswith('rec_')]
        assert len(controls)==(6 if f.startswith('idx') else 9)
    with pytest.raises(ValueError):m.prepare(out)


def test_mutants_are_enabled_only_and_have_required_failure(tmp_path):
    out=tmp_path/'copies';m.prepare(out);metadata=m.mutant_patches(out)
    assert len(metadata)==3
    for label,item in metadata.items():
        assert item['expected_failure'] and (out/(label+'.patch')).exists()
        text=(out/item['file']).read_text();mutation=m.control_mutants()[label]
        # Legacy matching WC_DONE is deliberately not the mutation target.
        starts=[match.start() for match in re.finditer(r'\bmodule ',text)]
        active=text[starts[2]:]
        assert active.count(mutation['old'])==1
        assert mutation['new'] not in text


def test_finite_connected_bench_binding_and_alias_oracle(tmp_path):
    out=tmp_path/'copies';m.prepare(out);m.prepared_bench(out)
    b=(out/'tb.sv').read_text()
    assert '.WIN_STACK(2)' in b and b.count('.SELECT_STACK(2)')==4
    assert b.count('.OPT_RECOVERY(1)')==4
    assert 'cycles>250000' in b and 'hold_return' in b
    assert 'observer ring/ledger mismatch' in b
    assert 'oracle_visible_at' in b and '7274' in b
    assert 'other_grants==0' in b
    assert '.rec_commit(commit)' in b


def test_unknown_source_anchor_rejected():
    with pytest.raises(ValueError):m.edit('changed source','old pinned anchor','replacement')
