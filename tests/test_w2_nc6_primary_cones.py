"""Actual source cone contracts for the delta-feedback repair."""
import importlib.util
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w2_nc6_primary_source as p
import w2_nc6_acyclic_secondary_source as s

def cone(text, marker):
 start=text.index(marker)
 begin=text.index('always_comb',start)
 end=text.find(' always_comb',begin+len('always_comb'))
 if end<0:end=text.index(' always_ff',begin)
 # Continuous generation may precede the next cone.
 cut=text.find(' generate ',begin)
 if cut>=0 and cut<end:end=cut
 return "\n".join(line.split("//",1)[0] for line in text[start:end].splitlines())

def test_primary_reproduces():
 assert p.source()==p.RTL.read_text()

def test_secondary_reproduces():
 assert s.source()==(ROOT/'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_coded_secondary_acyclic.sv').read_text()

def test_current_status_has_no_feedback_inputs():
 c=cone(p.source(),' // CURRENT-only views:')
 for forbidden in ['permit','scrub_ready','context_next','correction_error','repair_retire_ready','WE=']:
  # Comment includes permit intentionally; inspect the executable block.
  assert forbidden not in c[c.index('always_comb'):]
 assert 'view_i' in c and 'for(i=' not in c

def test_fault_cone_is_independent_of_admission_and_writeback():
 c=cone(p.source(),' // Semantic fault is independent')
 for forbidden in ['request_open','completion_open','permit','context_next','repair_retire_ready','scrub_ready','plan_bad']:
  assert forbidden not in c[c.index('always_comb'):]
 for guard in ['qualified(', 'popcount16(', 'fault_row[42:39]', 'J[fault_n][86]', 'c_req_addr', 'correction_error']:
  assert guard in c

def test_retirement_offer_does_not_consume_feedback():
 c=cone(p.source(),' // Retirement eligibility does not consume')
 assert 'scrub_ready' not in c
 assert 'context_next' not in c
 assert 'repair_retire_ready' not in c
 assert 'repair_original' in c and 'repair_candidate' in c
 assert 'secondary_retire_offer' in c

def test_bank_eligibility_is_not_semantic_permit():
 c=cone(s.source(),' // Bank eligibility is CURRENT')
 executable=c[c.index('always_comb'):]
 for forbidden in ['normal_permit','semantic_bad','reserve_roles','scrub_ready','next_payload']:
  assert forbidden not in executable
 assert 'logic_fault' in executable and 'payload[36][0]' in executable
 assert 'normal_permit&&!semantic_bad&&!rearm_v' in s.source()

def test_exact_state_and_calendar_preserved():
 model=p.enrollment_model()
 assert (model['total_words'],model['primary_words'],model['secondary_words'],model['physical_bits'])==(219,182,37,15768)
 assert model['same_client_request_II_min']==19
 assert model['correction_II_min']==9
 assert 'p_wr_done_ready' in p.source()
 assert 'PTAGW=35' in p.source()

def test_count_facts_do_not_consume_bank_admission():
 c=cone(p.source(),' // Pre-permit intents/status')
 for forbidden in ['request_open','completion_open','permit','scrub_ready','reserve_roles']:
  assert forbidden not in c
 assert 'count_pending' in c and 'offer_drained' in c and 'reopen_epoch' in c

def test_prepare_does_not_write_fault_feedback():
 text=p.source();task=text[text.index(' task automatic prepare'):text.index(' function automatic [63:0] decode_data')]
 assert 'core_bad' not in task
 assert 'plan_bad=1' in task
 assert 'any_plan_bad' not in text

def test_fault_prevents_correction_retirement_ack():
 c=cone(p.source(),' // Retirement eligibility does not consume')
 assert '&&!core_bad' in c
 # Independent semantic fault cone must stay free of retirement inputs.
 fault=cone(p.source(),' // Semantic fault is independent')
 assert 'repair_retire_ready' not in fault and 'scrub_ready' not in fault
