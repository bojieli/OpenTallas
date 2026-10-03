#!/usr/bin/env python3
"""Offline source/compile receipt review; production ownership/timing stays open."""
import json,re
from Euclid_installed_RFACK_CDC_contract import ROOT,RECORD,sha,contract

def review():
 for p,h in json.loads((RECORD/'artifact-sha256-r1.json').read_text()).items():
  if sha(ROOT/p)!=h:raise ValueError('artifact/source pin '+p)
 for p,h in json.loads((RECORD/'frozen-bench-source-pins-r1.json').read_text()).items():
  if sha(ROOT/p)!=h:raise ValueError('actual compiled benchmark/source pin '+p)
 t=json.loads((RECORD/'terminal-r1/terminal.json').read_text())
 if t['status']!='PASS_ACTUAL_COMPILE_AND_CONDITIONAL_LEAVES_ONLY_PRODUCTION_JOIN_BLOCKED':raise ValueError('scoped terminal status')
 if t['source_contract']!=contract():raise ValueError('installed source receipt changed')
 expected=['ot_gpu_rf_service-lint','ot_gpu_rf_visibility_fence-lint','ot_hbm_r14_clock_bridge-lint','tb_RFACK_conditional-compile','tb_RFACK_conditional-run','tb_CDC_common_reset-compile','tb_CDC_common_reset-run']
 if [j['name'] for j in t['jobs']]!=expected:raise ValueError('actual jobs')
 for j in t['jobs']:
  log=RECORD/'terminal-r1'/(j['name']+'.log')
  if j['returncode']!=0 or sha(log)!=j['log_sha256']:raise ValueError('actual tool log '+j['name'])
 rf=(RECORD/'terminal-r1/tb_RFACK_conditional-run.log').read_text();cdc=(RECORD/'terminal-r1/tb_CDC_common_reset-run.log').read_text()
 if 'PASS_RFACK_CONDITIONAL_DIRECT_COMMON_RESET writes=2 ack_consumed=1 reset_aborted_ACK=1 reads=1 cycles=29' not in rf:raise ValueError('RF actual conditional result')
 if 'PASS_CDC_OPAQUE_COMMON_RESET accepted=2 reset_aborted=1 delivered=1' not in cdc:raise ValueError('CDC actual conditional result')
 h=json.loads((RECORD/'to-Popper-Dewey-r1.json').read_text())
 if h['tagged_ACK_installed'] or h['calendar_or_rate_admitted'] or h['actual_owner_switch_or_generation_reuse_admitted']:raise ValueError('unqualified credit')
 if not all(v is None for v in h['unknown_cycles'].values()):raise ValueError('unknown cycle promoted')
 return {'status':'PASS_ACTUAL_COMPILE_CONDITIONAL_RF_CDC_SOURCE_RECEIPTS_ONLY','production_join':'BLOCKED','RF_ACK_identity':None,'unknown_cycles_preserved':True,'original_sources_unchanged':True}
if __name__=='__main__':print(json.dumps(review(),sort_keys=True))
