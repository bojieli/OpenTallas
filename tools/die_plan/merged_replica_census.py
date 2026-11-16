#!/usr/bin/env python3
# Merged-replica census (GENBUG-5): sibling instances of the SAME elaborated module must keep the same number of flops in
# the flattened Yosys netlist; an instance with fewer lost them to opt_merge (shared with a twin) or to constant/dead pruning.
# usage: mergeq.py KITDIR...   prints MRG rows. Inputs per kit: run/results/asap7/*/base/{1_1_yosys_canonicalize.rtlil,1_2_yosys.v}
import sys, re, glob, collections, os
def one(K):
    t = os.path.basename(K.rstrip('/'))
    r = glob.glob(K + '/run/results/asap7/*/base/1_1_yosys_canonicalize.rtlil'); v = glob.glob(K + '/run/results/asap7/*/base/1_2_yosys.v')
    if not r or not v: print('MRG\t%s\tNOINPUT' % t); return
    mods = {}; cur = None; top = None; attr_top = False
    for l in open(r[0], errors='replace'):
        if l.startswith('attribute \\top'): attr_top = True; continue
        if l.startswith('module '):
            cur = l.split()[1]; mods[cur] = []
            if attr_top: top = cur
            attr_top = False; continue
        if l.startswith('  cell ') and cur:
            p = l.split()
            if len(p) >= 3 and not p[1].startswith('$_') and not p[1].startswith('$a'): mods[cur].append((p[2].lstrip('\\'), p[1]))
        elif not l.startswith('attribute'): attr_top = False
    if top is None: print('MRG\t%s\tNOTOP' % t); return
    paths = {}  # path -> module
    st = [('', top)]
    while st:
        pre, m = st.pop()
        for inst, sub in mods.get(m, ()):
            if sub in mods:
                p = pre + inst; paths[p] = sub; st.append((p + '.', sub))
    cnt = collections.Counter(); regs = collections.defaultdict(collections.Counter)
    rx = re.compile(r'^\s*(?:DFF|DLL|DHL|ASYNC_DFF|SDF)\w*\s+(\S.*?)\s*\($')
    for l in open(v[0], errors='replace'):
        m = rx.match(l)
        if not m: continue
        nm = m.group(1).lstrip('\\').strip()
        nm = re.sub(r'\$_[A-Z0-9_]+_$', '', nm)
        parts = nm.split('.')
        for k in range(len(parts) - 1, 0, -1):
            p = '.'.join(parts[:k])
            if p in paths:
                loc = re.sub(r'\[\d+\]', '', '.'.join(parts[k:]))
                while True:
                    cnt[p] += 1; regs[p][loc] += 1
                    if '.' not in p: break
                    # propagate to ancestors that are instance paths
                    q = p; p = None
                    qp = q.split('.')
                    for kk in range(len(qp) - 1, 0, -1):
                        c = '.'.join(qp[:kk])
                        if c in paths: p = c; loc = '.'.join(qp[kk:]) + '.' + loc; break
                    if p is None: break
                break
    bym = collections.defaultdict(list)
    for p, m in paths.items(): bym[m].append(p)
    rows = []; lost_tot = 0
    seen_parent_short = set()
    for m, ps in bym.items():
        if len(ps) < 2: continue
        mx = max(cnt[p] for p in ps)
        if mx < 16: continue
        short = [p for p in ps if cnt[p] < mx]
        if not short: continue
        # skip when the shortfall is inherited from a child module already reported (report leaf-most)
        lost = sum(mx - cnt[p] for p in short)
        full = [p for p in ps if cnt[p] == mx][0]
        names = collections.Counter()
        for p in short:
            for loc, n in regs[full].items():
                d = n - regs[p].get(loc, 0)
                if d > 0: names[loc.split('.')[-1]] += d
        rows.append((lost, m, len(ps), len(short), mx, names.most_common(3), short[0]))
    # leaf-most: drop a module row if some other row's module instances are all descendants and explain the same loss
    rows.sort(reverse=True)
    keep = []
    for r_ in rows:
        if any(k[0] == r_[0] and k[6].startswith(r_[6] + '.') for k in rows if k is not r_): continue
        keep.append(r_)
    nfl = sum(1 for _ in open(v[0], errors='replace') if rx.match(_))
    print('MRGSUM\t%s\tflops %d\tinstances %d\tmodules_with_short_siblings %d\tflops_missing_in_short_siblings %d' % (t, nfl, len(paths), len(keep), sum(k[0] for k in keep)))
    global _missing
    _missing += sum(k[0] for k in keep)
    for lost, m, n, ns, mx, names, ex in keep[:6]:
        print('MRG\t%s\t%s\tinsts %d\tshort %d\tfull_flops %d\tmissing %d\tregs %s\te.g. %s' % (t, re.sub(r'^\$paramod\$[0-9a-f]+', '$p', m.lstrip('\\'))[:40], n, ns, mx, lost, ','.join('%s:%d' % x for x in names), ex[-50:]))
GATE = None; JSON_OUT = None; KITS = []
_a = iter(sys.argv[1:])
for x in _a:
    if x == '--gate': GATE = int(next(_a))
    elif x == '--json': JSON_OUT = next(_a)
    else: KITS.append(x)
_missing = 0
for K in KITS:
    try: one(K)
    except Exception as e: print('MRG\t%s\tERR %r' % (os.path.basename(K), e))
if JSON_OUT:
    import json; json.dump(dict(schema='ot_merge_census/1', flops_missing=_missing, gate=GATE), open(JSON_OUT, 'w'))
if GATE is not None:
    # OT_MERGE_CENSUS gate: sum of flops missing in short sibling instances (merged away by Yosys) >= GATE fails the kit
    print('OT_MERGE_CENSUS %s missing=%d gate=%d' % ('FAIL' if _missing >= GATE else 'PASS', _missing, GATE))
    sys.exit(4 if _missing >= GATE else 0)
