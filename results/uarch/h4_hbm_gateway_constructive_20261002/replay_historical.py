#!/usr/bin/env python3
"""Verify retained constructor records against their exact archived generators.

Only IO roots change: algorithms, pinned input bytes and model bytes do not.
No Git object database, remote ref, checkpoint or hardware tool is required.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import types

BASE=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--revision',type=int,action='append',required=True);args=ap.parse_args()
    for revision in args.revision:
        case=BASE/('constructor_r'+str(revision))
        manifest=json.loads((case/'manifest.json').read_bytes())
        source=(case/'generator_snapshot.py').read_bytes()
        if hashlib.sha256(source).hexdigest()!=manifest['tool_sha256']:raise ValueError('historical source pin')
        raw=(case/'input_manifest_snapshot.json').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=manifest['input_pin']:raise ValueError('historical input pin')
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);(home/'manifest.json').write_bytes(raw)
            for row in json.loads(raw)['inputs']:
                target=home/row['archive'];target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(BASE/row['archive'],target)
            module=types.ModuleType('historical_constructor');module.__file__=str(case/'generator_snapshot.py')
            exec(compile(source,str(case/'generator_snapshot.py'),'exec'),module.__dict__)
            module.HOME=home
            result=module.build()
            encoded=(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode()
            if encoded!=gzip.decompress((case/'model.json.gz').read_bytes()):raise ValueError('historical model replay')
            print('PASS_EXACT_HISTORICAL_CONSTRUCTOR_R'+str(revision))

if __name__=='__main__':main()
