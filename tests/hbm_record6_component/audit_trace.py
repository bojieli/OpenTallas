#!/usr/bin/env python3
"""Audit real R6 simulator logs; compile errors/timeouts never become causal FAIL."""
import argparse, json, re
from pathlib import Path

EXPECTED={5:['LANE_CAPTURE_IDENTITY','F0_SOURCE_AGE_ID'],6:['M1_SOURCE_AGE_DATA','LANE_CAPTURE_IDENTITY','X_SOURCE_AGE_DATA'],7:['SCALAR_IDENTITY','NATIVE_FULL_OLD_SECTOR'],8:['SCALAR_IDENTITY','NATIVE_FULL_OLD_SECTOR'],9:['RF_WRITE_PIN_ID_AGE','NATIVE_FULL_OLD_SECTOR'],10:['RF_CLASS5_ID_AGE','Q0_FAULT'],11:['DRAIN_ID_AGE_MASK','NATIVE_FULL_OLD_SECTOR'],13:['DESCRIPTOR_REARM_IGNORED_LAUNCH'],14:['RESET_WITHOUT_REINSTALL_PRODUCER_FAULT','PROGRAMME_Q0']}

def audit(log,abort=False,mut=0):
 text=log.read_text();failures=re.findall(r'Assertion failed[^\n]*|\$fatal[^\n]*|Error[^\n]*',text)
 if mut:
  witnesses=[p for p in EXPECTED[mut]if any('Assertion failed'in f and p in f for f in failures)]
  return dict(verdict='CAUSAL_FAIL'if witnesses and 'R6_COMPONENT_PASS'not in text else'UNQUALIFIED_NEGATIVE',mutant=mut,witnesses=witnesses,failures=failures)
 if 'R6_COMPONENT_PASS two_distinct_episodes native_full_sector'not in text:
  return dict(verdict='FAIL_OR_INCOMPLETE',failures=failures)
 def fields(line):return dict(re.findall(r'([A-Za-z_]+)=([^ ]+)',line))
 inputs={};outputs={};duplicates=[]
 for line in text.splitlines():
  if not line.startswith(('ADD_IN ','ADD_OUT ')):continue
  f=fields(line)
  if int(f['aborted']):continue
  key=(int(f['episode']),int(f['id']))
  target=inputs if line.startswith('ADD_IN ')else outputs
  if key in target:duplicates.append(key)
  target[key]=f
 wanted={(e,i)for e in range(2)for i in range(1281)}
 missing_in=sorted(wanted-inputs.keys());missing_out=sorted(wanted-outputs.keys())
 roots=[fields(l)for l in text.splitlines()if l.startswith('ROOT ')]
 scalars=[fields(l)for l in text.splitlines()if l.startswith('SCALAR ')]
 sectors=[fields(l)for l in text.splitlines()if l.startswith('NATIVE_FULL_SECTOR ')]
 retires=[fields(l)for l in text.splitlines()if l.startswith('SERIAL_RETIRE ')]
 starts=[fields(l)for l in text.splitlines()if l.startswith('PROGRAMME_START ')]
 starts=[v for v in starts if int(v['aborted'])==0]
 captures=[fields(l)for l in text.splitlines()if l.startswith('SOURCE_CAPTURE ')]
 # An aborted prefix legitimately captures group0 once in each quarter.
 expected_capture=20 if abort else 16
 ok=(not duplicates and not missing_in and not missing_out and len(roots)==2 and len(scalars)==2 and len(sectors)==2 and len(retires)==2 and len(starts)==2 and len(captures)==expected_capture and 'CLOCK_CAUSAL_PASS' in text and not failures)
 return dict(verdict='NUMERICAL_COMPONENT_PASS'if ok else'INCOMPLETE_TRACE',scope='No full-token, SRAM physical, timing or parent-H qualification',reset_abort=abort,adds_in=len(inputs),adds_out=len(outputs),missing_inputs=missing_in,missing_outputs=missing_out,duplicates=duplicates,roots=roots,scalars=scalars,native_sectors=sectors,retires=retires,starts=starts,captures=len(captures),failures=failures)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);p.add_argument('--reset-abort',action='store_true');p.add_argument('--mut',type=int,default=0);p.add_argument('--output',type=Path);a=p.parse_args();r=audit(a.log,a.reset_abort,a.mut);s=json.dumps(r,indent=2)+'\n';print(s,end='');
 if a.output:a.output.write_text(s)
 raise SystemExit(0 if r['verdict']in('NUMERICAL_COMPONENT_PASS','CAUSAL_FAIL')else 1)
