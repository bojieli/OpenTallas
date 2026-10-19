#!/usr/bin/env python3
"""Diagnostic fleet replay of unchanged compiler with git-show bytes source-pinned.
Sourcepack replaces git object lookup only; every byte validates against manifest.
No compiler result or fail-closed readiness/adoption check is replaced.
"""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools/qwen_layerbench'))
import layer_compile as C
HERE=Path(__file__).resolve().parent
sources=json.loads((HERE/'sourcepack.json').read_text())
def pinned_source(commit,path):
 matches=[s for s in sources if s['commit']==commit and s['path']==path]
 if len(matches)!=1:raise ValueError(f'Unpinned git-show request: {commit}:{path}')
 s=matches[0];b=(HERE/s['file']).read_bytes()
 if hashlib.sha256(b).hexdigest()!=s['sha256']:raise ValueError('sourcepack SHA mismatch')
 return b.decode()
C.git_show=pinned_source
sys.exit(C.main(sys.argv[1:]))
