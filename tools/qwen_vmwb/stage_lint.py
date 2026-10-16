#!/usr/bin/env python3
"""Stage the join961w full-hierarchy lint sources (current main + this branch; SU glue sources absent from main are
taken from the codex SU branches only when their sha256 equals the pinned 961t lint source) and write source.json."""
import hashlib, json, pathlib, subprocess, sys
S = 'results/arch/qwen_split_compute_1014'
ST = pathlib.Path(sys.argv[1])
src = json.loads(subprocess.run(['git', 'show', f'origin/main:{S}/native_join_961t/fullhier/source.json'],
                                capture_output=True, check=True).stdout)['sources']
files = open(f'{S}/native_join_961w/fullhier/native_join.f').read().split()
out = {}
for f in files:
    p = pathlib.Path(f)
    if p.exists():
        b = p.read_bytes()
    else:
        b = None
        for br in ('origin/codex/su-glue-physical-1015', 'origin/codex/su-base-cut-1015'):
            r = subprocess.run(['git', 'show', f'{br}:{f}'], capture_output=True)
            if r.returncode == 0 and hashlib.sha256(r.stdout).hexdigest() == src[f]['sha256']:
                b = r.stdout
                break
        assert b is not None, f
    d = ST / f
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_bytes(b)
    out[f] = {'sha256': hashlib.sha256(b).hexdigest(), 'origin': 'worktree' if p.exists() else 'codex-su-branch(961t pin)'}
json.dump({'sources': out}, open(f'{S}/native_join_961w/fullhier/source.json', 'w'), indent=1)
print(len(out), 'sources staged')
