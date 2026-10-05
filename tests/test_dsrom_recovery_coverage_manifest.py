import hashlib
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'results/rtl/dsrom_recovery_20261004/coverage_manifest/manifest.json'


def load():
    return json.loads(PATH.read_text())


def test_real_full40_selections_and_owner_mapping():
    d=load()
    assert d['canonical_layers']==list(range(40))
    assert d['canonical_matrix_count']==46671
    assert len(d['actual_selected_matrix_owners'])==1311
    records=d['actual_golden_program_inputs']
    assert {r['layer'] for r in records}==set(range(40))
    for r in records:
        assert len(set(r['selected_experts_in_record_order']))==6
        assert r['npz_present'] and r['npz_bytes']>0
        assert not r['accepted_runtime_journal_qualified']
    assert len(d['next_exact_binding']['missing_layers'])==33
    assert not d['next_exact_binding']['actual_full40_native_accepted_journal_available']


def test_minimal_observer_work_has_no_single_phase_or_compile():
    d=load();pending=d['minimum_additional_retained_structural_classes']
    assert len(pending)==38
    assert d['additional_pairs']==9728
    assert len(d['exact_paired_groups'])==5
    for r in pending:
        assert r['phase_count']>1 and r['phase_count']<=8
        assert r['paired_runs']==2*len(r['regions'])
        assert r['expected_W_VMW_VMS_assertions']==3*r['expected_output_rows_both_modes']
        assert r['admission_budget_cycles'] is None
        assert r['frontend_compiles']==r['archive_compiles']==0
    assert sum(r['paired_runs'] for r in d['family_budgets'].values())==9728


def test_selected_rejections_keep_baseline_without_layer_extrapolation():
    d=load();s=d['active_SU_selection']
    assert s['norm']['required_parallel_width_ratio']==128
    assert s['swiglu']['required_parallel_width_ratio']==96
    assert s['swiglu']['SS_ps']<0 and s['swiglu']['FF_ps']<0
    assert not s['norm']['admission'] and not s['swiglu']['admission']
    c=d['native_port_hc_pair']
    assert c['count']==81 and c['head_pairs']==1 and c['layers']==list(range(40))
    assert len({p['first'] for p in c['literal_pairs']})==81
    assert c['impossible_entire_node_elimination_rate_gain_percent']<1
    assert c['baseline_entire_three_op_node_us']==pytest.approx(.20889)
    assert c['verdict']=='REJECT_SCOPED_PAIR_BELOW_ONE_PERCENT'
    assert c['current_incremental_gain_us'] is None and not c['rtl_authorized']
    assert d['active_composition']['baseline_SU_latency_retained']
    assert d['active_composition']['matched_L20_only_saved_us']==pytest.approx(.920,abs=.001)


def test_one_per_die_issuer_is_priced_proposal_not_free_capture():
    p=load()['issuer_slot_proposal']
    x0,y0,x1,y1=p['requested_subbox_um']
    assert (x1-x0)*(y1-y0)==pytest.approx(p['reservation_um2'])
    assert p['instances_per_field_die']==1 and p['raw_FF']==47
    assert p['incremental_reservation_mm2_per_die']>0
    assert not p['fitted'] and not p['loaded_SS_FF_qualified']


def test_frozen_source_inputs():
    for path,expected in load()['inputs'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
