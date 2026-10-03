"""Gate refusals only, no substitute actual PC0-1 execution."""
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_remote_relaunch_plan_r66 as R


def test_local_launch_refused_even_with_capacity():
    with pytest.raises(ValueError,match='local launch prohibited'):
        R.validate_launch({},hostname='local',output_root='/tmp/x',resources={},dual_constructor={},smoke={})


def test_incomplete_projection_refused_before_constructor_credit():
    with pytest.raises(ValueError,match='projection pending'):
        R.validate_launch({'resolved_output_root':'/tmp/x'},hostname='ot-pve1',output_root='/tmp/x',resources={},dual_constructor={},smoke={})


def test_compact_unit_test_is_not_actual_smoke():
    plan=dict(resolved_output_root='/tmp/x',projection_complete=True,required_disk_bytes=1,required_RAM_bytes=1)
    with pytest.raises(ValueError,match='mandatory actual PC0-1'):
        R.validate_launch(plan,hostname='ot-pve1',output_root='/tmp/x',
            resources=dict(available_disk_bytes=1,available_RAM_bytes=1),
            dual_constructor=dict(status='PASS_ACTUAL_PRODUCER_AND_COLD_ADDITIVE_CONSTRUCTORS'),smoke=dict(status='UNIT_TEST_PASS'))


def test_same_process_restore_is_refused():
    plan=dict(resolved_output_root='/tmp/x',projection_complete=True,required_disk_bytes=1,required_RAM_bytes=1)
    smoke=dict(status='PASS_ACTUAL_PC0_1_ATOMIC_CHECKPOINT_COLD_PROCESS_RESTORE',retired_PCs=[0,1],
        actual_payload_exact=True,all_owners_drained=True,live_debts=0,
        sealed_journals_verified_after_producer_exit=True,producer_pid=1,restore_pid=1)
    with pytest.raises(ValueError,match='fresh-process'):
        R.validate_launch(plan,hostname='ot-agidock128',output_root='/tmp/x',
            resources=dict(available_disk_bytes=1,available_RAM_bytes=1),
            dual_constructor=dict(status='PASS_ACTUAL_PRODUCER_AND_COLD_ADDITIVE_CONSTRUCTORS'),smoke=smoke)
