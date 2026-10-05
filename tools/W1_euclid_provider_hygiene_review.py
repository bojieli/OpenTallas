#!/usr/bin/env python3
"""Offline immutable W1 receipt review; no RTL build, simulation or adoption."""
import json,re,sys
from pathlib import Path
from W1_euclid_provider_hygiene_gate import ROOT,RECORD,identity,sha,sources

def review():
 for p,h in json.loads((RECORD/'artifact-sha256-r1.json').read_text()).items():
  if sha(ROOT/p)!=h:raise ValueError('evidence/source pin '+p)
 if (ROOT/'rtl/model_ready_hbm_w1_euclid_20261003/provider-sources-r1.f').read_text().splitlines()!=sources():raise ValueError('selected source list changed')
 original=json.loads((RECORD/'original-ENABLE0-lint-FAIL.json').read_text())
 for p,h in original['source_sha256'].items():
  if sha(ROOT/p)!=h:raise ValueError('original input pin '+p)
 for token in ('IMPLICIT','UNDRIVEN'):
  if '%Warning-'+token not in (RECORD/'original-ENABLE0-diagnostics-FAIL.log').read_text():raise ValueError('original failure not preserved')
 terminal=json.loads((RECORD/'terminal-r2/terminal.json').read_text())
 if terminal['status']!='PASS_W1_DEFAULT_OFF_LINT_AND_ENABLED_IDENTITY_FINITE_STAGE':raise ValueError('actual terminal verdict')
 if terminal['identity']!=identity():raise ValueError('normalized enabled identity')
 for p,h in terminal['source_pins'].items():
  if sha(ROOT/p)!=h:raise ValueError('actual source pin '+p)
 if [j['name'] for j in terminal['jobs']]!=['ENABLE0-lint','ENABLE1-lint','stage-build','stage-run']:raise ValueError('exact actual jobs')
 for job in terminal['jobs']:
  log=RECORD/'terminal-r2'/(job['name']+'.log')
  if job['returncode']!=0 or sha(log)!=job['log_sha256']:raise ValueError('actual job record '+job['name'])
  if job['name'].endswith('-lint') and re.search(r'%(?:Warning|Error)-(?:IMPLICIT|UNDRIVEN):',log.read_text()):raise ValueError('forbidden lint diagnostic')
 want=json.loads((RECORD/'review-r1.json').read_text())
 if terminal['binary_sha256']!=want['actual_binary_sha256']:raise ValueError('binary receipt')
 log=(RECORD/'terminal-r2/stage-run.log').read_text()
 expected='PASS_W1_TWO_TRANSACTIONS '+ ' '.join(f'{k}={v}' for k,v in [('accepts',2),('commits',1),('WR',1),('RD',1),('owned',3),('reverse',1),('off_checks',164),('cycle',162)])
 if expected not in log:raise ValueError('exact handshake/default-off counts')
 if 'FAIL_' in log:raise ValueError('finite bench failure')
 return {'status':'PASS_OFFLINE_W1_SOURCE_MODEL_LINT_FINITE_STAGE_RECEIPTS','original_immutable':True,'enabled_byte_identity':True,'model_delta':0,'no_PR_or_calendar_credit':True}
if __name__=='__main__':print(json.dumps(review(),sort_keys=True))
