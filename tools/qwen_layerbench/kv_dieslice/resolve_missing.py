#!/usr/bin/env python3
"""TOKj-KV 10-23: add the files that define modules the vehicle lint reports MODMISSING (leaf modules that live in files not
named after them; BINDER3's per-partition lints stubbed these leaves).  Search order = the bind source roots in the
binder's priority (kvsrc36 = the v3.6 bind source, then rtl6 e33504a6f as built, then binder3 wt rtl/lib).
    resolve_missing.py VDIR LINTLOG   -> appends to VDIR/files.f (copies into VDIR/src/extra__<root>/...)"""
import os, re, shutil, sys
V, LOG = os.path.abspath(sys.argv[1]), sys.argv[2]
ROOTS = ['/home/ubuntu/scratch/binder2-1023/asap7_cells'] + ([l.strip() for l in open(f'{V}/src_roots.txt') if l.strip()] if os.path.exists(f'{V}/src_roots.txt') else []) + ['/home/ubuntu/scratch/binder3-1023/kvsrc36', '/home/ubuntu/scratch/binder2-1023/kv_src_e33504a6f', '/home/ubuntu/wt/binder3-1023']
miss = sorted(set(re.findall(r"Cannot find file containing module: '(\w+)'", open(LOG).read())))
idx = {}
# staged dirs first, in the -y order (a module defined in a file of an included dir wins: same tree the lints used)
for ln in open(f'{V}/incdirs.f'):
    d = ln.split()[-1]
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if f.endswith(('.sv', '.v')) and '_sim' not in f:
            for m in re.findall(r'^\s*module\s+(\w+)', open(os.path.join(d, f), errors='ignore').read(), re.M):
                idx.setdefault(m, os.path.join(d, f))
MOD = re.compile(r'^\s*module\s+(\w+)', re.M)
for r in ROOTS:
    for sub in (('rtl', 'physical') if 'asap7_cells' not in r else ('',)):
        for dp, dn, fn in os.walk(os.path.join(r, sub)):
            if '/test' in dp or '/tb' in dp: continue
            for f in fn:
                if not f.endswith(('.sv', '.v')) or f.endswith(('_bb.v',)) or '_sim' in f: continue
                p = os.path.join(dp, f)
                try: txt = open(p, errors='ignore').read()
                except Exception: continue
                for m in MOD.findall(txt):
                    idx.setdefault(m, p)
add, unres = {}, []
for m in miss:
    p = idx.get(m)
    if p: add.setdefault(p, []).append(m)
    else: unres.append(m)
have = set(open(f'{V}/files.f').read().split())
with open(f'{V}/files.f', 'a') as fo:
    for p, ms in sorted(add.items()):
        if p.startswith(V + '/src/'):
            dst = p
            if dst not in have: fo.write(dst + '\n'); have.add(dst)
            print('ADD', p, ms); continue
        tag = 'extra__' + p.replace('/home/ubuntu/', '').replace('/', '__').rsplit('__', 1)[0]
        d = f'{V}/src/{tag}'; os.makedirs(d, exist_ok=True); dst = f'{d}/{os.path.basename(p)}'
        if p != dst: shutil.copy2(p, dst)
        if dst not in have: fo.write(dst + '\n')
        print('ADD', p, ms)
print('missing', len(miss), 'added files', len(add), 'unresolved', unres)
