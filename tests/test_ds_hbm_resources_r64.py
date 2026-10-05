"""Additive costs and preallocation identity guards; no numerical execution."""
import ast,copy,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_resources_r64 as R


def test_diagnostics_contract_and_all_inherited_costs_retained(monkeypatch,tmp_path):
    original=dict(checkpoint={'components':{'retained':100},'checkpoint_new_bytes':100},checkpoint_new_bytes=100,
        other_new_bytes=200,cold_and_restore_new_RAM_bytes=300,serialization_workspace_RAM_bytes=300,
        producer_new_RAM_bytes=400,journal_new_bytes=500,
        RAM={'components':{'retained':700},'coexistence_RAM_peak_bytes':700,
             'cold_and_restore_new_RAM_bytes':300,'serialization_workspace_RAM_bytes':300})
    monkeypatch.setattr(R.base,'model',lambda *a,**k:copy.deepcopy(original))
    pins={p:R.sha(ROOT/p) for p in R.NEW}
    result=R.compose({'instructions':[]},[],{},output_root=tmp_path,pins=pins)
    costs=result['R64_additive_costs']
    assert costs['two_durable_records'] is True
    assert costs['stage_or_terminal_file_upper_bytes']>=6*costs['source_and_graph_diagnostic_text_upper_bytes']
    assert result['checkpoint']['components']['retained']==100
    assert result['RAM']['components']['retained']==700
    assert result['journal_new_bytes']==500 and result['producer_new_RAM_bytes']==400
    assert result['other_new_bytes']>=200+2*costs['stage_or_terminal_file_upper_bytes']
    assert result['cold_and_restore_new_RAM_bytes']>300
    assert sum(result['RAM']['components'].values())==result['RAM']['coexistence_RAM_peak_bytes']
    assert sum(result['checkpoint']['components'].values())==result['checkpoint_new_bytes']
    assert result['output_root']==str(tmp_path.resolve())


def test_constructor_requires_output_and_registered_loader_before_runner():
    source=(ROOT/'tools/ds_hbm_dual_constructor_r64.py').read_text()
    ast.parse(source)
    assert 'import ds_hbm_checkpointed_prefix_r63 as original' in source
    assert source.index('validate_output_root(args.out,plan,projection)')<source.index('enrollment.install()')<source.index('original.main()')
    assert "plan.get('numerical_GO') is not False" in source
    assert 'setrlimit' not in source and 'sched_setaffinity' not in source
