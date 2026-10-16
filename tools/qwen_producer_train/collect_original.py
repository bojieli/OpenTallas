#!/usr/bin/env python3
"""One-shot collector; never waits, restarts, or changes the remote simulation."""
import pathlib,subprocess,json
D=pathlib.Path(__file__).resolve().parent
assert json.load(open('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock'))['owner']=='codex'
p=subprocess.run(['ssh','ot-agidock128','test -f /tmp/codex-qwen-producer-train-1103/mutant.exit'],capture_output=True)
if p.returncode:raise SystemExit('PENDING original missing-marker simulation; no files changed')
for name in ['mutant.log','mutant_compile.log','mutant.exit']:
 (D/'actual_producer'/name).write_bytes(subprocess.check_output(['ssh','ot-agidock128','cat /tmp/codex-qwen-producer-train-1103/'+name]))
s=(D/'actual_producer/mutant.log').read_text();rc=(D/'actual_producer/mutant.exit').read_text().strip()
assert rc!='0' and 'TRAIN_EXPECTATION count=0 gap=999 fault=0' in s,(rc,s)
p=D/'manifest.json';m=json.loads(p.read_text());m['status']='ACTUAL_DUT_POSITIVE_AND_MISSING_MARKER_MUTANT_PASS';m['actual_producer_positive']['mutant']='Actual producer marker forcedzero; explicit eight-capture expectation rejects count0/gap999/fault0';p.write_text(json.dumps(m,indent=2)+'\n')
print('PASS original actual controller/port positive and missing-marker mutant; remote processes untouched')
