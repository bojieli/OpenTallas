#!/usr/bin/env python3
"""TOKj-KV 10-23: seed a new staged vehicle dir with the leaf files a previous bind's lint loop resolved (resolve_missing.py),
taking each from the NEW bind's source roots at the same rtl/... or physical/... relative path when it exists there.
    seed_extras.py OLD_VDIR NEW_VDIR"""
import os, re, shutil, sys
O, N = map(os.path.abspath, sys.argv[1:3])
nb = len(open(f'{O}/bind_files_n.txt').read().split()) if os.path.exists(f'{O}/bind_files_n.txt') else None
old = [l.strip() for l in open(f'{O}/files.f') if l.strip()]
roots = [l.strip() for l in open(f'{N}/src_roots.txt') if l.strip()]
have = set(l.strip() for l in open(f'{N}/files.f'))
haveb = {os.path.basename(x) for x in have}
add = 0
with open(f'{N}/files.f', 'a') as fo:
    for p in old:
        tag = p[len(O) + 5:].split('/')[0]                     # src/<tag>/<file>
        if os.path.basename(p) in haveb: continue
        orig = '/home/ubuntu/' + tag.replace('extra__', '', 1).replace('__', '/') + '/' + os.path.basename(p)
        m = re.search(r'/((rtl|physical)/.*)$', orig)
        src = next((f'{r}/{m.group(1)}' for r in roots if m and os.path.exists(f'{r}/{m.group(1)}')), None) or (orig if os.path.exists(orig) else p)
        t = 'extra__' + os.path.dirname(src).replace('/home/ubuntu/', '').replace('/', '__')
        os.makedirs(f'{N}/src/{t}', exist_ok=True); dst = f'{N}/src/{t}/{os.path.basename(src)}'
        shutil.copy2(src, dst); fo.write(dst + '\n'); haveb.add(os.path.basename(p)); add += 1
print('seeded', add)
