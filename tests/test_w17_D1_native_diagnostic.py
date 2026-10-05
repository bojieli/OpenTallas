import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import run_w17_D1_native_diagnostic as m

GATE = 'D1_REAL_GATE time=1000 pc=0 me_ready=1 kv_ok=0 kvd_v=0 win_idle=1 waited=1 q_gate=1 m0_gate=1\n'
DESC = 'D1_REAL_DESCRIPTOR time=2000 generation=1 rows=128\n'
REQ = 'D1_REAL_ACCEPT time=3000 address=262144 tag=1 write=0\n'
RSP = 'D1_REAL_RESPONSE time=4000 tag=1 beat=0\n'
WITNESS = 'D1_PREFIX_GATE_AND_FIRST_RETURN_ONLY reads=1 returns=1 writes=0 acks=0\n'
END = 'D1_TERMINAL_PREFIX_ONLY evals=12 time_ps=4500 cycles=4\n'

def test_actual_qualified_prefix_still_not_full_token():
    r = m.classify(GATE + DESC + REQ + RSP + WITNESS + END, 0)
    assert r['verdict'] == 'PASS_CONTROLLED_PREFIX_GATE_AND_FIRST_RETURN_ONLY'
    assert r['actual_gate_records'] == 1

@pytest.mark.parametrize('fault', ['%Error', 'D1_SOURCE_OR_LEDGER_FAULT', 'D1_SOURCE_ADMISSION_MISMATCH'])
def test_sticky_fault_wins_over_late_witness(fault):
    assert m.classify(GATE + DESC + REQ + RSP + WITNESS + END + fault, 0)['qualified_prefix'] is False

@pytest.mark.parametrize('removed', [GATE, DESC, REQ, RSP])
def test_missing_real_event_cannot_borrow_witness(removed):
    text = (GATE + DESC + REQ + RSP + WITNESS + END).replace(removed, '')
    assert m.classify(text, 0)['verdict'] == 'FAIL_DIAGNOSTIC_WITNESS_PROTOCOL'

def test_cycle_stop_is_inconclusive_even_with_PC_gate_activity():
    r = m.classify(GATE + 'D1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT cycles=512\n' + END.replace('cycles=4', 'cycles=512'), 0)
    assert r['verdict'] == 'INCONCLUSIVE_COMPILED_512_CYCLE_STOP'
    assert r['qualified_prefix'] is False

def test_inconsistent_native_cycle_terminal_rejected():
    assert m.classify('D1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT cycles=512\n' + END, 0)['verdict'] == 'FAIL_DIAGNOSTIC_WITNESS_PROTOCOL'

@pytest.mark.parametrize('mutant', ['reads=0 returns=1 writes=0 acks=0', 'reads=1 returns=2 writes=0 acks=0', 'reads=1 returns=1 writes=0 acks=1'])
def test_impossible_ledger_counts_rejected(mutant):
    assert m.classify(GATE + DESC + REQ + RSP + 'D1_PREFIX_GATE_AND_FIRST_RETURN_ONLY ' + mutant + '\n' + END, 0)['qualified_prefix'] is False

def test_nonzero_process_exit_cannot_be_success():
    assert m.classify(GATE + DESC + REQ + RSP + WITNESS + END, -9)['qualified_prefix'] is False

def test_missing_or_repeated_native_terminal_rejected():
    assert m.classify(GATE + DESC + REQ + RSP + WITNESS, 0)['qualified_prefix'] is False
    assert m.classify(GATE + DESC + REQ + RSP + WITNESS + END + END, 0)['qualified_prefix'] is False
