#!/usr/bin/env python3
"""Prepare/lint ONE full native PF384 endpoint; never launch C++ compilation here.
Fleet admission owns all costly generation/compilation and fills build-job count.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
import hbm_collective_full_gate as full
ROOT=Path(__file__).resolve().parents[1]
P='rtl/hbm_accel/collective_native_gate_20261007/'
TOP='tb_hbm_collective_native_composed'
END='rtl/hbm_accel/collective_native_link_20261007/ot_hbm_collective_native_link_candidate.sv'
C='rtl/hbm_accel/collective_credit_20261007/'
EXTRA=[
 'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv',
 'rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc.sv',
 'rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc_refill.sv',
 'rtl/hbm_accel/collective_flight_20261007/ot_hbm_collective_protected_flight.sv',
 'rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_reset_entry.sv',
 *[C+n+'.sv' for n in ['ot_hbm_credit_secded_pkg','ot_hbm_credit_source','ot_hbm_credit_rx','ot_hbm_credit_source_debt','ot_hbm_initial_credit_ack_observer','ot_hbm_credit_source_session','ot_hbm_link_session_coordinator','ot_hbm_link_start_adapter','ot_hbm_link_session_agent','ot_hbm_link_management_cdc']],
 'rtl/hbm_accel/collective_ingress_20261007/ot_hbm_collective_protected_ingress.sv',
 END,P+'tb_native_peer_session.sv',P+TOP+'.sv']
FILES=list(dict.fromkeys([f for f in full.FILES if f not in [full.END,full.P+full.TOP+'.sv']]+EXTRA))
EVIDENCE=['tools/hbm_collective_native_composed_gate.py','tools/hbm_collective_native_composition_model.py','results/rtl/hbm_collective_native_gate_20261007/model_before_bench.json','results/rtl/hbm_collective_native_gate_20261007/traffic_contract.json',full.P+full.TOP+'.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--prepare-only',action='store_true',required=True)
 p.add_argument('--verilator',default='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator');a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 pins={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES+EVIDENCE}
 (out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
 version=subprocess.run([a.verilator,'--version'],capture_output=True,text=True)
 (out/'tool_version.txt').write_text(version.stdout+version.stderr)
 if version.returncode or 'Verilator 5.' not in version.stdout:raise SystemExit('Requires modern pinned Verilator5; no old-tool fallback.')
 text=(ROOT/END).read_text()
 peer='!invalid_partial_port[p] && owner_p_r[p]) rb_pop[p]'
 reserve='.reserve_valid(tv[p]),.reserve_ready(source_ready)'
 assert text.count(peer)==1 and text.count(reserve)==1
 mutant=out/'endpoint_mutation.sv'
 mutant.write_text(text.replace(peer,'!invalid_partial_port[p] && (owner_p_r[p] || $test$plusargs("IGNORE_PEER_CREDIT"))) rb_pop[p]').replace(reserve,'.reserve_valid(tv[p]&&!$test$plusargs("BYPASS_TX_RESERVATION")),.reserve_ready(source_ready)'))
 (out/'mutation_sha256.txt').write_text(hashlib.sha256(mutant.read_bytes()).hexdigest()+'\n')
 sources=[str(mutant if f==END else ROOT/f) for f in FILES]
 common=['--timing','-Wno-fatal','-Wno-WIDTH','--top-module',TOP]
 lint=[a.verilator,'--lint-only',*common,*sources]
 (out/'lint_command.json').write_text(json.dumps(lint,indent=2)+'\n')
 with (out/'lint.log').open('w') as log:r=subprocess.run(lint,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 (out/'lint.exit').write_text(str(r.returncode)+'\n')
 assert pins=={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES+EVIDENCE},'Sources changed during lint'
 if r.returncode:
  (out/'verdict.json').write_text(json.dumps({'status':'FAIL_LINT','exit':r.returncode},indent=2)+'\n');return r.returncode
 build=[a.verilator,'--binary',*common,'-O0','--build-jobs','${ADMITTED_BUILD_JOBS}','--Mdir',str(out/'obj'),*sources]
 (out/'build_command_template.json').write_text(json.dumps(build,indent=2)+'\n')
 modes=[{'mode':'baseline','args':[],'expected_exit':0,'marker':'PASS_NATIVE_COMPOSED_ENDPOINT'},
 {'mode':'CORRUPT_GOLDEN','args':['+CORRUPT_GOLDEN'],'expected_exit':'nonzero','markers_any':['ENDPOINT_FAIL numerical or identity mismatch','NATIVE_GATE_PEER_RESULT numerical or identity mismatch']},
 {'mode':'IGNORE_PEER_CREDIT','args':['+IGNORE_PEER_CREDIT'],'expected_exit':'nonzero','marker':'ENDPOINT_CREDIT_VIOLATION'},
 {'mode':'BYPASS_TX_RESERVATION','args':['+BYPASS_TX_RESERVATION'],'expected_exit':'nonzero','marker':'NATIVE_GATE_RESERVATION_VIOLATION'},
 {'mode':'CHANGE_CONTEXT_BUSY','args':['+CHANGE_CONTEXT_BUSY'],'expected_exit':'nonzero','marker':'NATIVE_GATE_CONTEXT_REJECTED'}]
 (out/'run_modes.json').write_text(json.dumps(modes,indent=2)+'\n')
 receipt={'status':'PREPARED_LINT_PASS_NO_BUILD_NO_SIMULATION','source_pins':'source_pins.json','model':'results/rtl/hbm_collective_native_gate_20261007/model_before_bench.json','scope':'One fullPF384/16lane native endpoint; all eight full-duplex credit ports, actual source/receiver/storage/flight/CDC/session. Own24 arithmetic golden from original reference.1512 externally provided results checked for exact transport only. VendorPHY quiesce/resetACK remain fixtures. No fullfabric/physical proof.','next':'Fleet measured CPU/RAM/disk admission in a pinned clean worktree; replace ADMITTED_BUILD_JOBS using admission decision, remap repository paths to pinned sources, build once and run all five modes. No local C++ compilation launched.'}
 (out/'verdict.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return 0
if __name__=='__main__':raise SystemExit(main())
