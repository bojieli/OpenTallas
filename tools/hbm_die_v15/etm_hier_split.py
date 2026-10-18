#!/usr/bin/env python3
"""Hierarchical SYNTH ETM netlist splitter (HBM-IDXETM 2026-10-18).

Why: synth_etm.sh links the whole mapped netlist flat.  ot_hbm_idx_score_static (TP=192) is 36.9 M flat cells
(4 engines x 4 ot_hbm_idx_chunk_owned_native x 32 hslices) and its flat write_timing_model needs >116 GB.  The 16
chunks are ONE module (2.29 M cells): characterise it once, then link the parent with the chunk as a liberty
cell, so the parent never flattens (~0.26 M cells + 16 macros).

    etm_hier_split.py split STA_V TOP CHILD[,CHILD..] OUTDIR
        OUTDIR/child_<C>.v = module C + every module it instantiates (transitively)
        OUTDIR/parent.v    = modules reachable from TOP without entering a CHILD; CHILD instances stay as cell
                             references (resolved by <C>_synth_<corner>.lib)
        OUTDIR/split.json  = {top, children: {C: {instances, modules, flat_cells}}, parent_flat_cells, flat_cells}
    etm_hier_split.py extract STA_V MODULE NEWNAME OUT_V
        MODULE (+ transitive deps) as a stand-alone netlist whose top is renamed NEWNAME (plain identifier, so an
        escaped $paramod module can be an STA top).  Used for the reduced verification configuration.

A CHILD must be a plain identifier (it becomes a liberty cell name) and must not instantiate itself (no recursion).
"""
import collections, json, os, re, sys

MOD = re.compile(r'^module\s+(\\\S+|[A-Za-z_][\w$]*)\s*\(', re.M)
END = re.compile(r'^endmodule\b', re.M)
INST = re.compile(r'^\s*(\\\S+|[A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$\[\]\.]*)\s*\(', re.M)
KW = {'module', 'input', 'output', 'wire', 'assign', 'inout', 'reg', 'endmodule'}


def parse(path):
    txt = open(path).read()
    mods = collections.OrderedDict()
    pos = 0
    while True:
        m = MOD.search(txt, pos)
        if not m:
            break
        e = END.search(txt, m.end())
        body = txt[m.start():e.end()]
        hdr_end = body.index(';')                 # instances start after the port list
        inst = collections.Counter(t.group(1) for t in INST.finditer(body, hdr_end + 1) if t.group(1) not in KW)
        mods[m.group(1)] = dict(text=body, inst=inst)
        pos = e.end()
    return mods


def flat_count(mods):
    memo = {}

    def f(m):
        if m not in memo:
            memo[m] = sum(n * (f(t) if t in mods else 1) for t, n in mods[m]['inst'].items())
        return memo[m]
    return f


def closure(mods, root, stop=()):
    seen, todo = [], [root]
    while todo:
        m = todo.pop()
        if m in seen or m not in mods:
            continue
        seen.append(m)
        if m != root and m in stop:
            continue
        for t in mods[m]['inst']:
            if t in mods and t not in seen and not (t in stop and t != root):
                todo.append(t)
    return seen


def split(sta_v, top, children, outdir):
    mods = parse(sta_v)
    if top not in mods:
        sys.exit(f'etm_hier_split: top {top} not in {sta_v}')
    fc = flat_count(mods)
    os.makedirs(outdir, exist_ok=True)
    rep = dict(top=top, flat_cells=fc(top), children={})
    for c in children:
        if c not in mods:
            sys.exit(f'etm_hier_split: child {c} not in {sta_v}')
        if not re.fullmatch(r'[A-Za-z_]\w*', c):
            sys.exit(f'etm_hier_split: child {c} is not a plain identifier (liberty cell name)')
        deps = closure(mods, c)
        open(f'{outdir}/child_{c}.v', 'w').write('\n'.join(mods[m]['text'] for m in reversed(deps)) + '\n')
        rep['children'][c] = dict(modules=len(deps), flat_cells=fc(c))
    par = [m for m in closure(mods, top, stop=set(children)) if m not in children]
    # count child instances under the parent, and the cells left in the parent netlist
    inst = collections.Counter()
    pc = {}

    def pcount(m):
        if m in pc:
            return pc[m]
        n = 0
        for t, k in mods[m]['inst'].items():
            if t in children:
                n += k                                   # one macro cell
            elif t in mods:
                n += k * pcount(t)
            else:
                n += k
        pc[m] = n
        return n

    def walk(m, mult):
        for t, k in mods[m]['inst'].items():
            if t in children:
                inst[t] += mult * k
            elif t in mods:
                walk(t, mult * k)
    walk(top, 1)
    for c in children:
        rep['children'][c]['instances'] = inst[c]
    rep['parent_cells'] = pcount(top)
    rep['parent_modules'] = len(par)
    open(f'{outdir}/parent.v', 'w').write('\n'.join(mods[m]['text'] for m in reversed(par)) + '\n')
    json.dump(rep, open(f'{outdir}/split.json', 'w'), indent=1)
    print('OT_ETM_HIER_SPLIT ' + json.dumps(rep))


def extract(sta_v, module, newname, out_v):
    mods = parse(sta_v)
    if module not in mods:
        sys.exit(f'etm_hier_split: {module} not in {sta_v}')
    deps = closure(mods, module)
    texts = []
    for m in reversed(deps):
        t = mods[m]['text']
        if m == module:
            assert t.startswith('module ' + module)
            t = 'module ' + newname + ' ' + t[len('module ' + module):].lstrip()
        texts.append(t)
    open(out_v, 'w').write('\n'.join(texts) + '\n')
    print(f'OT_ETM_HIER_EXTRACT {module} -> {newname} modules={len(deps)} flat_cells={flat_count(mods)(module)}')


if __name__ == '__main__':
    if len(sys.argv) == 6 and sys.argv[1] == 'split':
        split(sys.argv[2], sys.argv[3], [c for c in sys.argv[4].split(',') if c], sys.argv[5])
    elif len(sys.argv) == 6 and sys.argv[1] == 'extract':
        extract(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        sys.exit(__doc__)
