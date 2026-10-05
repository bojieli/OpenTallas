#!/usr/bin/env python3
"""Run distinct expected-FAIL reference mutants using the qualified fixture binary.

No compilation, RTL edits, timing limits, or replacement of positive receipts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

MESSAGES = {
    'omit': 'rejected stale return retired reset-orphan debt',
    'drop': 'reset orphan receipt dropped without provider disposal',
    'drop_debt': 'external accepted receipt conservation',
    'consume': 'client terminal consumed quarantined reset orphan',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--record',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    original=json.loads(a.record.read_text())
    if original['status']!='PASS_FUNCTIONAL' or not original['reset_quarantine_selected']:
        raise SystemExit('requires completed reset-quarantine positive gate')
    binary=a.record.parent/'gate.bin'
    if sha(binary)!=original['binary_sha256']:
        raise SystemExit('positive binary pin mismatch')
    a.out.mkdir()
    receipt=dict(pid=os.getpid(),positive_record=str(a.record.resolve()),
                 positive_record_sha256=sha(a.record),binary_sha256=sha(binary),
                 binary_path=str(binary.resolve()),controls=[],status='RUNNING',
                 physical_or_fulltoken_admission=False,compile_launched=False)
    def save():
        (a.out/'record.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save()
    for name,message in MESSAGES.items():
        command=[str(binary.resolve()),'+oracle_reset_'+name]
        start=time.monotonic()
        with (a.out/(name+'.log')).open('w') as log:
            result=subprocess.run(command,cwd=a.out,stdout=log,stderr=subprocess.STDOUT)
        text=(a.out/(name+'.log')).read_text()
        matched=result.returncode!=0 and message in text and 'COMPONENT_PASS' not in text
        receipt['controls'].append(dict(name=name,command=command,rc=result.returncode,
            seconds=time.monotonic()-start,expected_message=message,
            expected_failure_observed=matched,log_sha256=sha(a.out/(name+'.log'))))
        save()
        print(name,'EXPECTED_FAIL' if matched else 'FAIL_CONTROL',flush=True)
    receipt['binary_sha256_post']=sha(binary)
    receipt['status']='PASS_REFERENCE_NEGATIVE_CONTROLS' if all(
        x['expected_failure_observed'] for x in receipt['controls']) and receipt['binary_sha256_post']==receipt['binary_sha256'] else 'FAIL_REFERENCE_CONTROLS'
    save();print(receipt['status'],flush=True)
    return 0 if receipt['status']=='PASS_REFERENCE_NEGATIVE_CONTROLS' else 1

if __name__=='__main__':
    raise SystemExit(main())
