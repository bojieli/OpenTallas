#!/usr/bin/env python3
"""Build only the canonical actual epoch allocator; no bench/main or RTL edits."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
before=digest(a.source)
command=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--cc','--build','-j','2','--top-module','ot_qwen_tp8_token_epoch_allocator','-GINITIAL_EPOCH=0','-Wno-fatal','--Mdir',str((a.out/'obj').resolve()),str(a.source.resolve())]
start=time.monotonic()
with (a.out/'build.log').open('w') as log:run=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
archive=a.out/'obj/Vot_qwen_tp8_token_epoch_allocator__ALL.a'
record={'scope':'CANONICAL_ACTUAL_ALLOCATOR_LIBRARY_ONLY_NOT_HOST_TOKEN_CLOSURE','exit_code':run.returncode,'command':command,'source_sha256':before,'source_stable':digest(a.source)==before,'archive_sha256':digest(archive) if archive.exists() else None,'seconds':time.monotonic()-start,'initial_epoch':0}
(a.out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
raise SystemExit(run.returncode or int(not record['source_stable']))
