#!/usr/bin/env python3
"""Run one prepared TU compile/link, remotely after the unchanged host guard."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared',required=True,type=Path)
    a=parser.parse_args()
    if float(Path('/proc/loadavg').read_text().split()[0])>=128:
        raise RuntimeError('post-guard E2 load >=128; no compiler launched')
    out=a.prepared.parent;record=json.loads(a.prepared.read_text())
    # compiler command ends with -c SOURCE -o OBJECT
    source=Path(record['command'][record['command'].index('-c')+1])
    if hashlib.sha256(source.read_bytes()).hexdigest()!=record['source_sha256']:
        raise ValueError('prepared TU changed')
    exits={}
    for name,command in (('compile',record['command']),('link',record['link']),
                         ('ABI_probe',[str(out/'linked_driver_tu_probe'),'--compile-probe'])):
        with (out/(name+'.log')).open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        exits[name]=result.returncode
        if result.returncode:
            break
    (out/'terminal.json').write_text(json.dumps(dict(
        status='PASS_DRIVER_TU_ONLY' if len(exits)==3 and all(v==0 for v in exits.values()) else 'FAIL_DRIVER_TU',
        exits=exits,new_frontend_launched=False,linked_runtime_exercised=False,
        full_token_exercised=False,physical_qualified=False,
        existing_compiled_seam_exports=record['existing_model']['seam_exports']),indent=2)+'\n')
    return next((v for v in exits.values() if v),0)


if __name__=='__main__':raise SystemExit(main())
