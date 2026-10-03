from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/rtl/dsrom_system_rtl_20261003'
def test_actual_terminal_exact_tokens_and_source_vector():
 c=json.loads((D/'system_gate_sys_b2_lrt0.json').read_text());b=json.loads((D/'system_gate_sys_b2.json').read_text())
 assert c['pass'] and c['returncode']==0
 assert c['parsed']['tokens']==b['parsed']['tokens']
 assert [t['token'] for t in c['parsed']['tokens']]==[2815,3537,2047]
 assert c['parsed']['total_cycles']==1304979
 assert not any(c['parsed'][k] for k in ['token_mismatches','logit_mismatches','state_mismatches'])
 assert hashlib.sha256((D/'system_gate_sys_b2_lrt0.out.txt').read_bytes()).hexdigest()==c['log_sha256']
 for p,h in c['input_sha256'].items():
  q=D/'source_sys_b2_lrt0/tb_dsrom_system.sv' if p=='rtl/test/dsrom_sys/tb_dsrom_system.sv' else ROOT/p
  assert hashlib.sha256(q.read_bytes()).hexdigest()==h
def test_control_not_adopted_and_manifest_discrepancy_retained():
 r=json.loads((D/'execution_takeover_20261003.json').read_text())
 assert r['cycle_delta']==0 and not r['adopted']
 assert not r['source_manifest_mismatch_preserved']['current_commit_qualifies']
 assert r['source_manifest_mismatch_preserved']['matching_git_source']=='aa02d73f8'
 assert '-GLINK_RT=0' in json.loads((D/'system_gate_sys_b2_lrt0.build_cmd.json').read_text())
 assert (D/'system_gate_sys_b2_lrt0.rc').read_text().splitlines()[0]=='0'
