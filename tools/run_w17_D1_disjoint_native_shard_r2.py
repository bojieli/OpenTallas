#!/usr/bin/env python3
"""Disk-backed temporary files for the otherwise read-only pinned native shard.
Preserves the first committed worker byte-for-byte; no temporary-file size cap.
"""
import argparse
import json
from pathlib import Path
import run_w17_D1_disjoint_native_shard as base

ORIGINAL_DOCKER_ARGV=base.docker_argv

def docker_argv(out,input_root,manifest):
    argv=ORIGINAL_DOCKER_ARGV(out,input_root,manifest)
    index=argv.index('-w')
    argv[index:index]=['-v',str(out/'tmp')+':/tmp']
    return argv

def run(packet,out):
    # Validate before creating compiler scratch or touching any process.
    base.validate(json.loads(packet.read_text()))
    if (out/'start.json').exists():raise ValueError('No duplicate launch')
    (out/'tmp').mkdir(exist_ok=False)
    (out/'temporary_storage_binding.json').write_text(json.dumps({'successor_source_SHA256':base.sha(__file__),'base_source_SHA256':base.sha(base.__file__),'temporary_storage':str(out/'tmp'),'disk_backed':True,'per_file_size_cap':None,'engine_changes':False},indent=2)+'\n')
    base.docker_argv=docker_argv
    return base.run(packet,out)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packet',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();raise SystemExit(run(a.packet,a.out))
