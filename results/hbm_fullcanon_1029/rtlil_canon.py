#!/usr/bin/env python3
"""HBM-CORES-REBAL-9: canonical form of a whole-design RTLIL dump.  src attributes are dropped, and every module is
renamed bottom-up to <base>#<sha of its normalised body, children already renamed>.  Two designs then compare equal
iff each module's elaborated contents match, whatever the yosys paramod naming (an explicit default parameter vs an
omitted one gives a different $paramod hash for the same module).  usage: rtlil_canon.py IN.il OUT.txt [TOP]"""
import hashlib, re, sys
txt = open(sys.argv[1]).read()
mods, cur, name = {}, None, None
for ln in txt.splitlines():
    if re.match(r'\s*attribute \\src ', ln) or not ln.strip() or ln.startswith('#'):
        continue
    if re.search(r'attribute \\(hdlname|top|dynports|cells_not_processed) ', ln):
        continue
    m = re.match(r'module (\S+)$', ln)
    if m:
        name, cur = m.group(1), []
        continue
    if ln == 'end' and cur is not None and name is not None:
        mods[name] = cur; cur = name = None
        continue
    if cur is not None:
        cur.append(ln.rstrip())
top = sys.argv[3] if len(sys.argv) > 3 else None


def base(n):
    m = re.match(r'\$paramod(?:\$[0-9a-f]+)?\\([^\\]+)', n)
    return m.group(1) if m else n.lstrip('\\')


canon = {}


def cn(n, stack=()):
    if n in canon:
        return canon[n]
    if n not in mods:                                     # blackbox / primitive cell type
        canon[n] = n; return n
    body = []
    for ln in mods[n]:
        m = re.match(r'(\s*cell )(\S+)( .*)$', ln)
        if m and m.group(2) in mods:
            ln = m.group(1) + cn(m.group(2)) + m.group(3)
        if re.match(r'\s*parameter \\(MLAT|ALAT|WCOPY) ', ln) and n == top:   # the new top's declared parameters
            continue
        body.append(ln)
    h = hashlib.sha256('\n'.join(body).encode()).hexdigest()[:16]
    canon[n] = f'{base(n)}#{h}'
    mods[n] = body
    return canon[n]


for n in sorted(mods):
    cn(n)
with open(sys.argv[2], 'w') as f:
    for n in sorted(mods, key=lambda k: canon[k]):
        if n == top:
            f.write('TOP ' + base(n) + '\n')
        else:
            f.write(canon[n] + '\n')
    f.write('TOP_BODY\n' + '\n'.join(mods[top]) + '\n' if top else '')
