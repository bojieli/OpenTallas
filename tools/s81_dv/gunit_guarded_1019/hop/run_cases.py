#!/usr/bin/env python3
import json
import hashlib
import shutil
from pathlib import Path
import re
import shlex
import subprocess
import sys
def main():
    r=Path(sys.argv[1]);o=r/'out_hop';k=r/'tools/s81_dv/gunit_guarded_1019/hop/kit0'
    # Check every target before any copy, argument write, log open or binary run.
    names = ('positive', 'old_main_age', 'wrong_age_plus1')
    targets = [o/'results.json', o/'kit_sorted']
    for name in names:
        targets.extend((o/name, o/(name+'.argv.json'), o/(name+'.log')))
    for target in targets:
        if target.exists() or target.is_symlink():
            raise SystemExit('GUARDED_OUTPUT_EXISTS: refusing existing target '+str(target))
    if '--sorted' in sys.argv:
        original_kit=k
        k=o/'kit_sorted'
        shutil.copytree(original_kit,k)
        shutil.copyfile(r/'tools/s81_dv/gunit_guarded_1019/hop/host_boot_sorted.memh',k/'prog/host_boot.memh')
        for p in original_kit.rglob('*'):
            if p.is_file() and p.relative_to(original_kit)!=Path('prog/host_boot.memh'):
                assert p.read_bytes()==(k/p.relative_to(original_kit)).read_bytes()
    original=(k/'tb.args').read_text()
    binary_sha=hashlib.sha256((o/'obj/sim').read_bytes()).hexdigest()
    records=[]
    for name,n,s in [('positive',1015,1013),('old_main_age',759,757),('wrong_age_plus1',1016,1014)]:
        args=re.sub(r'\+dir=\S+','+dir='+str(k),original)
        args=re.sub(r'\+HC_AGE_N=\d+',f'+HC_AGE_N={n}',args)
        args=re.sub(r'\+HC_AGE_S=\d+',f'+HC_AGE_S={s}',args)
        argv=[str(o/'obj/sim')]+shlex.split(args)+['+measure=1']
        (o/(name+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n')
        with (o/(name+'.log')).open('w') as log:rc=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT).returncode
        text=(o/(name+'.log')).read_text()
        if name=='positive':passed=rc==0 and 'GU_LAYER PASS' in text and 'GU_AGE_CONTRACT_FAIL' not in text
        else:passed=rc==0 and 'GU_LAYER FAIL' in text and 'GU_AGE_CONTRACT_FAIL' in text
        records.append({'case':name,'exit':rc,'expected_verdict_observed':passed,'age_N':n,'age_S':s,'binary_sha256':binary_sha,'sorted_fixture':('--sorted' in sys.argv)})
        (o/'results.json').write_text(json.dumps(records,indent=2)+'\n')
        print(name+': '+('EXPECTED_VERDICT' if passed else 'UNEXPECTED_VERDICT'),flush=True)
        if not passed:sys.exit(2)
    print('GUARDED_HOP_PASS')


if __name__ == '__main__':
    main()
