#!/usr/bin/env python3
"""Elaborate the real generated SU source hierarchy; no C++ arithmetic build.

Run via ot-run. This is source/elaboration evidence only; it does not qualify
native programme execution, actual GEN placement, clocks, or die integration.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();root=a.root.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((root/'source_manifest.json').read_text())
    for p,d in manifest['sources'].items():
        if hashlib.sha256((root/p).read_bytes()).hexdigest()!=d:raise ValueError('stale implementing source '+p)
    generated=json.loads((root/'generated/native_source_inventory.json').read_text())
    for p,d in generated['generated_sha256'].items():
        if hashlib.sha256((root/'generated'/p).read_bytes()).hexdigest()!=d:raise ValueError('stale generated source '+p)
    compiler=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    compiler=str(compiler) if compiler.exists() else 'verilator'
    command=[compiler,'--json-only','--timing','--top-module','ot_s81_su_canonical_candidate',
             '--json-only-output',str(out/'hierarchy.tree.json'),'--json-only-meta-output',str(out/'hierarchy.meta.json'),'-Wno-fatal','-Wno-WIDTH',
             *[str(root/p) for p in manifest['files']],*[str(root/'generated'/p) for p in generated['generated_sha256']]]
    start=time.time()
    with(out/'elaborate.log').open('w') as f:r=subprocess.run(command,cwd=root,stdout=f,stderr=subprocess.STDOUT)
    receipt=dict(schema='opentallas.s81.native-su-source-elaboration.v1',native_qualified=False,exit_code=r.returncode,
        elapsed_s=time.time()-start,maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        source_commit=manifest['source_commit'],source_sha256=manifest['sources'],
        generated_sha256=generated['generated_sha256'],source_clock_entries=159,
        physical_clock_qualification=False,actual_GEN_instantiation=False,global_programmes_bound=False)
    if r.returncode==0:
        receipt.update(frontend_json_sha256=hashlib.sha256((out/'hierarchy.tree.json').read_bytes()).hexdigest(),
                       frontend_meta_sha256=hashlib.sha256((out/'hierarchy.meta.json').read_bytes()).hexdigest(),
                       actual_leaf_census_pending=True)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('source_sha256','generated_sha256','actual_module_counts')}))
    raise SystemExit(receipt['exit_code'])
if __name__=='__main__':main()
