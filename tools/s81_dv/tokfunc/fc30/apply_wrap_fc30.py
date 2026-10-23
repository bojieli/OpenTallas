#!/usr/bin/env python3
# STW-S81d-TOK 10-22 (from STW-S81c-RTLGAP g9c22/apply_wrap.py): (1) every cut-kit source must be blob-equal to a file of the
# DIE sim filelist (<W>/sim/sim_filelist.f, the executed bind sources) -- fail closed otherwise; (2) bind the DIE kit wrappers:
# each wrapped master's defining file is replaced by the DIE patched copy (master renamed <M>__ot_pr_core, asserted identical
# to the kit file modulo the rename) and wrappers/<M>.v is added to kit.f.
import json, re, subprocess, sys, os, shutil, hashlib
W, K = sys.argv[1], sys.argv[2]; C = W + '/sim'
SRC = '/srv/opentallas-scratch/claude/stw-s81c-cap30/gen-main/src'   # executed bind --rtl-root snapshot
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
sim = {}
for l in open(C + '/sim_filelist.f'):
    l = l.strip()
    if l.startswith('/') and os.path.isfile(l):
        m = re.search(r'/rtl_extra/[0-9a-f]+/(.*)$', l); rel = m.group(1) if m else re.sub(r'^.*/src/', '', l)
        sim.setdefault(rel, set()).add(h(l))
pat_dir = C + '/patched'
for x in os.listdir(pat_dir):   # patched copies stand for their originals too (compare modulo rename below)
    pass
k = json.load(open(K + '/kit.json')); bad = []
for f in k['files']:
    p = f['path']; rel = re.sub(r'^rtl_extra/[0-9a-f]+/', '', p)
    if p == 'cells_used.v': continue
    hk = h(K + '/src/' + p); sp = SRC + '/' + rel
    if hk not in sim.get(rel, set()) and not (os.path.isfile(sp) and h(sp) == hk): bad.append(p)
man = json.load(open(C + '/manifest.json'))['masters']
kitf = open(K + '/kit.f').read(); added = []; swapped = []
orig = {f['path']: open(K + '/src/' + f['path'], errors='replace').read() for f in k['files']}
for M in man:
    for f in k['files']:
        t = orig[f['path']]
        if re.search(r'^\s*module\s+' + M + r'\b', t, re.M):
            pat = [x for x in os.listdir(pat_dir) if re.search(r'^\s*module\s+' + M + r'__ot_pr_core\b', open(pat_dir + '/' + x).read(), re.M)]
            assert len(pat) == 1, (M, pat)
            pt = open(pat_dir + '/' + pat[0]).read()
            body = re.sub(r'__ot_pr_core\b', '', pt)
            if body.startswith('// die_sim_wrappers.py:'): body = body.split('\n', 1)[1]   # the tool's provenance header line
            assert body == t, ('patched != kit file modulo rename + header', M, f['path'])
            if f['path'] not in swapped:
                shutil.copy(pat_dir + '/' + pat[0], K + '/src/' + f['path']); swapped.append(f['path'])
            shutil.copy(C + '/wrappers/' + M + '.v', K + '/src/wrap_' + M + '.v'); added.append('src/wrap_' + M + '.v')
            break
open(K + '/kit.f', 'w').write(kitf.rstrip('\n') + '\n' + '\n'.join(added) + '\n')
json.dump(dict(source_mismatch=bad, swapped=swapped, wrappers=added, manifest_masters=list(man), die_v_sha256=json.load(open(C + '/manifest.json')).get('die_v_sha256')), open(K + '/simwrap.json', 'w'), indent=1)
print('WRAP mismatch', len(bad), bad[:6], 'swapped', len(swapped), 'wrappers', len(added))
sys.exit(1 if bad else 0)
