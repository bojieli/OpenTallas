import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('producer_prep',ROOT/'tools/w17_window_actual_producer_cancel_prepare.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def test_default_inverse_reconstruction_is_original_pinned_module():
 original,text,module,legacy,enabled=m.candidate()
 assert legacy.replace(m.NAME+'_cancel_legacy',m.NAME,1)==module
 assert 'parameter integer OPT_CANCEL = 0' in text
 assert 'generate if (!OPT_CANCEL)' in text
 assert original==m.origin(m.PRODUCER)

def test_prepared_copy_is_reproducible_and_only_new_local_control_state():
 _,text,_,_,enabled=m.candidate()
 p=ROOT/'rtl/test/w17_window_actual_producer_cancel_prepared/ot_hdc_v41x_window_kv_blocks_cancel.sv'
 assert p.read_text()==text
 r=json.loads((m.RECORD/'model.json').read_text())
 assert r['candidate_sha256']==m.sha(text)
 assert r['prepared_declared_added_register_bits']==2
 assert 'input wire rec_suffix_closed' in enabled and 'input wire rec_qe_idle' in enabled

def test_clear_metadata_requires_source_suffix_and_idle_preserves_fault():
 _,_,_,_,enabled=m.candidate()
 a=enabled.index('end else if (rec_cancel) begin');b=enabled.index('        end else begin',a+10)
 block=enabled[a:b]
 assert 'rec_freeze && rec_suffix_closed && rec_qe_idle' in block
 assert 'state <= EMPTY; count <= 0; rd_idx <= 0;' in block
 assert "rec_cancel_ack <= 1'b1; rec_cancel_token_ack <= rec_token;" in block
 assert 'fault <= 0' not in block and 'codes[' not in block and 'scales[' not in block
 assert 'rec_cancel_token_ack != rec_token' in block

def test_same_edge_local_error_and_freeze_stop_every_new_handshake():
 _,_,_,_,enabled=m.candidate()
 for part in ['!rec_stop && (state','!rec_stop && state == FULL','!rec_stop && !rec_local_bad && state == DRAIN','if (cap_v && !rec_stop && !rec_local_bad)','if (issue && !rec_stop && !rec_local_bad)','if (blk_v && blk_ready && !rec_local_bad)']:
  assert part in enabled


def test_actual_QE_no_ready_good_or_poison_and_VM_hooks_are_bound():
 r=m.plan();qe=m.origin(m.QE);core=m.origin(m.CORE)
 assert 'kvb_v <= aq_vo && mode == QDQ8' in qe and 'kvb_fault <= aq_vo && mode == QDQ8' in qe
 assert 'input  wire              cap_ready' not in qe
 assert r['actual_shape']['nb']==16
 assert len(r['core_hooks'])==6 and '.cap_v(win_capture_v)' in core
 assert r['qualification']['actual_core_adapter_installed'] is False
 assert 'No actual causal PHY provider exists' in r['local_cancel_contract']['producer_fault_rearm']

def test_priced_control_not_duplicate_observer_or_payload_and_no_causal_timer():
 r=m.plan();e=r['unified_compatible_entry']
 assert e['concrete_subtotal_bits']==2+8 and e['prior_conservative_local_adapter_envelope_bits']==19
 assert e['new_payload_bits']==0 and e['healthy_added_guard_cycles']==0
 assert r['unchanged_healthy_landmarks']=={'producer_EMPTY_cycle':871,'final_WR_ACK_cycle':905,'projected_visible_ps':911274,'projected_deadline_not_causal_completion':True}
 assert r['qualification']['causal_PHY_provider'] is False


def test_explicit_rearm_requires_certified_retirement_and_held_token():
 _,_,_,_,enabled=m.candidate()
 a=enabled.index('end else if (rec_rearm) begin');b=enabled.index('        end else begin',a)
 block=enabled[a:b]
 assert 'rec_cancel_ack && rec_freeze && rec_suffix_closed && rec_qe_idle' in block
 assert 'rec_retired_certified && rec_cancel_token_ack == rec_token' in block
 assert "fault <= 1'b0; rec_cancel_ack <= 1'b0;" in block
 assert "else fault <= 1'b1" in block
 assert 'rec_rearm || !(rec_freeze' in enabled
 assert 'rec_retired_certified' in m.plan()['local_cancel_contract']['producer_fault_rearm']


def test_ready_has_no_input_valid_feedback():
 _,_,_,_,enabled=m.candidate()
 for name in ['cap_ready','issue_ready']:
  line=next(x for x in enabled.splitlines() if 'assign '+name+' =' in x)
  assert 'rec_local_bad' not in line and 'cap_v' not in line and 'issue &&' not in line
