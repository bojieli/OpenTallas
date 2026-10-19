from pathlib import Path
import json,re
O=Path.cwd()
positive=(O/'positive_admission.log').read_text();assert positive.count('producer=0 slice=0 tap=0 target=0 cal=0 release=0')==2 and 'SERIAL_REQUESTS2 PASS' in positive
out=[]
for name in ['stale_input','missing_descriptor','host_identity_swap','restart_phase','overlap','reset_pulse_without_reinstall']:
 s=(O/(name+'.log')).read_text();assert '%Fatal' in s
 if name!='overlap':assert 'REQUEST0_ACCEPT stream3800 original32words unchanged' in s
 if name in ['stale_input','missing_descriptor','host_identity_swap']:
  assert 'ARITHMETIC FAIL b=          0 n=          0' in s
  nums=re.findall(r'NUM b=\s*0 n=\s*0 got=([0-9a-f]+) expected=([0-9a-f]+)',s)
  assert len(nums)==2 and nums[0][0]==nums[0][1] and nums[1][0]!=nums[1][1]
 if name=='restart_phase':assert re.search(r'ADMIT qt=297\d .*bridge=1',s)
 if name=='overlap':assert 'OVERLAP_START qt2700 busy=1 first_request_active' in s and 'PRODUCER FAIL edge=32 n=32 fault=1' in s
 if name=='reset_pulse_without_reinstall':
  assert 'RESET_NEW_EPOCH' in s and 'faults=0110' in s # actual slice + target fault, no injected flags
  assert json.loads((O/'reset_pulse_summary.json').read_text())['por_low_ps']==1668
 out.append(dict(case=name,observed_fail=True,causal_predicate_pass=True,first_fatal=next(x for x in s.splitlines()if '%Fatal' in x)))
(O/'causal_predicates.json').write_text(json.dumps(out,indent=2));print('SIX_DISTINCT_CAUSAL_CONTROLS PASS positive2x32, stale-input/rearm/address/phase/overlap/reset-epoch')
