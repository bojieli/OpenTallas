import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_kv_residence_gate import generate


def test_existing_hbm_policy_does_not_prove_current_runtime_residence():
 r=generate()
 assert r['residence_policy_in_source'] and not r['actual_runtime_persistent_hbm_bound']
 assert not r['physical_build_ready'] and not r['adoption'] and not r['model_rates_changed']


def test_reconciled_read_bytes_are_not_added_twice():
 r=generate()['byte_ledger']
 assert r['existing_fp8_kv_read_bytes_per_TP4_die']==144*1024*1024
 assert r['same_bytes'] and r['incremental_full_reload_bytes_to_add']==0
 assert r['incremental_finite_refill_cycles'] is None
 assert r['aggregate_read_lower_bound_cycles_at_1p2GHz']==pytest.approx(50331.648)


def test_policy_reconciliation_scales_context_without_changing_architecture():
 a=generate(context=4096)['byte_ledger'];b=generate()['byte_ledger']
 assert a['existing_fp8_kv_read_bytes_per_TP4_die']*2==b['existing_fp8_kv_read_bytes_per_TP4_die']
 assert a['incremental_full_reload_bytes_to_add']==0
