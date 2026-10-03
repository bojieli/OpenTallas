import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'rtl/dsrom_sys/c8'

def test_native_completion_source_is_actual_serviced_queue_not_grant():
 s=(D/'ot_hdc_v41x_idx_hbm_c8.sv').read_text()
 assert "wr_done[p] <= 1'b1;wr_done_addr[p*AW+:AW]<=q_addr[p][slot];wr_done_tag[p*TAGW+:TAGW]<=q_tag[p][slot];" in s
 assert 'm_rdy' not in (D/'ot_dsrom_c8_write_journal.sv').read_text()
 j=(D/'ot_dsrom_c8_write_journal.sv').read_text()
 assert 'match_count!=1' in j and 'backend_done_tag' in j
 assert 'if(!(&empty)) quarantine<=1' in j

def test_writable_path_retained_and_visibility_controls_publication():
 m=(D/'ot_chip_v41x_kv_reqmux_c8.sv').read_text()
 assert 'C8_PUBLICATION ? c_we[s]' in m
 assert 'pending && owner_c && m_wr_done[s]' in m
 s=(D/'ot_chip_v41x_ckv_die_service_c8.sv').read_text()
 assert 'wr_pending && c_wr_done[wr_stack]' in s
 assert 'rows_ready && !own_pending' in s
 assert 'own_visible_identity<=own_identity' in s
 # Full K512 and original quantizer remain, no substituted payload generator.
 assert 'parameter integer K = 512' in s
 assert 'ot_chip_v41x_ckv_row_encoder u_enc' in s

def test_actual_parent_native_callback_and_dynamic_partition_contract():
 s=(D/'ot_chip_v41x_die_owner_safe_c8.sv').read_text()
 assert '.accepted_write(h_v & h_rdy & h_we)' in s
 assert '.backend_wr_done(h_wr_done)' in s
 assert '.backend_done_tag(c8_done_tag)' in s
 assert '&& !kb_busy && !c8_own_pending && c8_ckv_reuse_ready && !win_service_busy && window_prime_ready' in s
 r=json.loads((ROOT/'results/uarch/dsrom_c8_publication_20261003/model.json').read_text())
 assert r['selected_partition']['stages']==82
 assert not r['selected_partition']['physical_fit_qualified']
 assert r['return_baseline']['node_RD']==64
 assert r['cell_area_50pct_reservation_mm2']==2*r['cell_area_floor_mm2']
 for p,h in r['source_sha256'].items():
  b=subprocess.check_output(['git','show',r['source_pin']+':'+p],cwd=ROOT)
  assert hashlib.sha256(b).hexdigest()==h

def test_stage_admission_is_not_engine_entry_or_retirement():
 s=(D/'ot_dsrom_c8_stage_context.sv').read_text()
 assert 'launch=context_v&&context_restored' in s
 assert '(count+active)<2' in s
 assert 'done_armed&&engine_done' in s
 assert 'write_journal_quiet&&!write_quarantine&&!write_fault' in s
 assert 'if(active||count!=0) quarantine<=1' in s


def test_c_grant_matches_selected_nonreset_backend_acceptance():
 s=(D/'ot_chip_v41x_kv_reqmux_c8.sv').read_text()
 assert 'assign c_rdy[s] = rst_n && !hold_write && !choose_w && m_rdy[s];' in s
 assert 'assign w_rdy[s] = rst_n && !hold_write && choose_w && m_rdy[s];' in s
 assert '!rst_n && !hold_write && choose_w' not in s

def test_native_transport_fixture_uses_actual_golden_qdq_value():
 import sys
 sys.path.insert(0,str(ROOT/'tools'))
 import numpy as np
 from hdc_golden_v41 import qdq_fp4_e4m3
 y=qdq_fp4_e4m3(np.ones(512,dtype=np.float32))
 assert np.all(y.view(np.uint32)==0x3f840000)
 s=(ROOT/'rtl/test/dsrom_sys/c8/tb_dsrom_c8_native.sv').read_text()
 assert "32'h3f840000" in s
 assert 'if(sf)$fatal' in s


def test_native_backend_lengths_match_actual_parent_not_default():
 b=(ROOT/'rtl/test/dsrom_sys/c8/tb_dsrom_c8_native.sv').read_text()
 assert '.TAGW(17),.LENW(4),.BEATW(4),' in b
 parent=(D/'ot_chip_v41x_hbm3e_phy_c8.sv').read_text()
 assert '.LENW(4), .BEATW(4)' in parent


def test_actual_l20_top_launch_entry_identity_and_retire_are_connected():
 s=(D/'ot_v41_rt_die_l20_c8.sv').read_text()
 assert 'parameter integer C8_CONTEXT=0' in s
 assert '.host_start(C8_CONTEXT ? c8_engine_start : start)' in s
 assert ".host_entry(C8_PUBLICATION ? (C8_CONTEXT ? c8_engine_entry : c8_entry) : 14'd0)" in s
 assert '.c8_position_identity(C8_CONTEXT ? c8_engine_identity : c8_position_identity)' in s
 assert '.offer_token(token),.offer_pos(pos),.offer_user(user)' in s
 assert '.context_restored(c8_context_restored)' in s
 assert '.engine_done(done),.write_journal_quiet(c8_write_quiet)' in s
 assert '.write_quarantine(c8_write_quarantine),.write_fault(c8_write_fault)' in s
 assert 'C8 context requires actual native publication callbacks' in s

def test_selected_reuse_clear_wins_and_legacy_default_is_preserved():
 s=(D/'ot_chip_v41x_ckv_die_service_c8.sv').read_text()
 assert "if (C8_PUBLICATION && sel_v && !rd_act) npresent <= 0;" in s
 assert "else npresent <= npresent + (KW+1)'(nwr);" in s
 b=(ROOT/'rtl/test/dsrom_sys/c8/tb_dsrom_c8_two_positions.sv').read_text()
 assert 'identity={16\'d7,10\'d2,21\'(100+p)}' in b
 assert 'read_row(766,first_row)' in b
 assert '(!service.f_ready || !(&quiet))' in b
 assert 'second selection retained stale present count' in b


def test_context_retirement_requires_actual_local_fetch_and_table_reuse_ready():
 s=(D/'ot_chip_v41x_ckv_die_service_c8.sv').read_text()
 assert 'assign reuse_ready=rst_n && !fault && f_ready && !f_ov && !f_job' in s
 for required in ('!rel_on','!rd_act','!rq_v','tail==0','!own_pending','!enc_busy','!nw_have','nw_got==0'):
  assert required in s.split('assign reuse_ready=',1)[1].split(';',1)[0]
 parent=(D/'ot_chip_v41x_die_owner_safe_c8.sv').read_text()
 assert '.reuse_ready(c8_ckv_reuse_ready)' in parent
 assert '&& c8_ckv_reuse_ready && !win_service_busy' in parent
 assert 'assign c8_ckv_reuse_ready=1;' in parent  # CKV disabled branch only
