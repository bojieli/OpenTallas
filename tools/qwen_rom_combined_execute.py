#!/usr/bin/env python3
"""Execute the actual combined runtime with its cached embedding-ROM row."""
import argparse
import json
from pathlib import Path
import subprocess
from qwen_rom_combined_launch import prepare, require, sha, validate_selection


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('selection','stages','preload','oracle-root','baseline','output','embedding-bin'):
        ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--embedding-sha256',required=True)
    ap.add_argument('--prepare-only',action='store_true')
    a=ap.parse_args()
    # The same cached row used by the existing passing REAL_MEM run, never a
    # computed embedding or new oracle callback. Exact ABI: token32, scale16,
    # 4096 INT8 code bytes. Preserve every code/scale bit.
    require(sha(a.embedding_bin)==a.embedding_sha256,'cached embedding row identity')
    payload=a.embedding_bin.read_bytes()
    require(len(payload)==4102,'cached embedding ROM row extent')
    cmd,rec=prepare(a.selection,a.stages,a.preload,a.oracle_root,a.baseline,a.output)
    require(int.from_bytes(payload[:4],'little')==rec['token'],'embedding row token differs')
    cmd+=['--embed-bin',str(a.embedding_bin.resolve())]
    rec['command']=cmd
    rec['embedding']={'path':str(a.embedding_bin.resolve()),'sha256':a.embedding_sha256}
    rec['status']='prepared'
    (a.output/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    if a.prepare_only:
        print(json.dumps({'status':'prepared','command':cmd}));return 0
    with (a.output/'runtime.log').open('x') as log:
        child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
        (a.output/'runtime.pid').write_text(str(child.pid)+'\n')
        rc=child.wait()
    rec['returncode']=rc;rec['status']='runtime_exit_zero' if rc==0 else 'runtime_failed'
    try:
        require(sha(a.embedding_bin)==a.embedding_sha256,'cached embedding changed')
        require(all(sha(p)==expected for p,expected in rec['input_sha256'].items()),'launch inputs changed')
        require(all(sha(p)==expected for p,expected in rec['stage_payload_sha256'].items()),'stage images changed')
        require(all(sha(v['raw'])==v['raw_sha256'] for v in rec['kv_history'].values()),'raw history changed')
        validate_selection(rec['selection'])
    except (OSError,ValueError,KeyError) as e:
        rec['status']='failed';rec['error']=str(e);rc=2
    (a.output/'terminal.json').write_text(json.dumps(rec,indent=2)+'\n')
    # Exact numerical/token verdict remains the owning runtime's readback
    # checker. Exit zero alone is not promoted to golden/SSFF/rate qualification.
    return rc


if __name__=='__main__':raise SystemExit(main())
