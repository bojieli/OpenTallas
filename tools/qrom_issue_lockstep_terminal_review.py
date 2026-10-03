#!/usr/bin/env python3
"""Offline integrity/classification review; never starts a solver."""
import argparse,hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1]
PACKET=pathlib.Path('results/uarch/qwen_rom_issue_lockstep_terminal_20261003')
def review(root=ROOT):
 p=root/PACKET
 pins=json.loads((p/'artifact-pins.json').read_text())
 for name,want in pins.items():
  if hashlib.sha256((root/name).read_bytes()).hexdigest()!=want:raise ValueError('artifact hash mismatch: '+name)
 terminal=json.loads((p/'raw/terminal.json').read_text()); c=json.loads((p/'classification.json').read_text())
 if terminal['status']!='FAIL_LITERAL_ISSUE_LOCKSTEP' or terminal['results']!={'base':0,'induction':-9}:raise ValueError('original terminal changed')
 if c['classification']!='INCONCLUSIVE_TOOL_SIGKILL' or c['SAT_architecture_counterexample'] or c['unbounded_induction_PASS']:raise ValueError('unsupported proof claim')
 log=(p/'raw/induction.log').read_text()
 if 'Induction step proven: SUCCESS' in log or re.search(r'SAT proof finished - model found',log):raise ValueError('classification contradicts solver log')
 journal=(p/'kernel-journal-PID1998275.log').read_text()
 if not all(s in journal for s in ['global_oom','pid=1998275','Killed process 1998275 (yosys)','anon-rss:50685088kB']):raise ValueError('kernel cause not substantiated')
 for name,want in terminal['source_sha256'].items():
  if hashlib.sha256((p/'source-inputs'/name).read_bytes()).hexdigest()!=want:raise ValueError('terminal source mismatch: '+name)
 bounded=json.loads((p/'prior-base12-PASS-unchanged.json').read_text())
 if bounded['status']!='PASS_LITERAL_LOCKSTEP_BASE12_ONLY' or bounded['steps']!=12 or bounded['unbounded_transition_induction']:raise ValueError('bounded scope changed')
 from qrom_issue_lockstep_decomposition_prepare import prepare
 fresh=prepare();saved=json.loads((p/'decomposition-preparation.json').read_text())
 if fresh!=saved:raise ValueError('source decomposition differs')
 if fresh['proof_pass'] or fresh['solver_launched'] or fresh['arithmetic_shared_or_abstracted_before_exact_lemma']:raise ValueError('preparation promoted to proof')
 return {'status':'PASS_ARCHIVE_INTEGRITY_ONLY','artifact_pins':len(pins),'classification':c['classification'],'cause':c['tool_cause'],'base12_only':True,'one_step_candidate_proved':False,'whole_engine':False,'solver_launched':False}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=pathlib.Path);a=parser.parse_args()
 value=json.dumps(review(),indent=2,sort_keys=True)+'\n'
 if a.output:
  if a.output.exists():raise ValueError('exclusive output required')
  a.output.write_text(value)
 print(value,end='')
