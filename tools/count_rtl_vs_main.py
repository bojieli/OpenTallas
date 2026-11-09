import json, sys, collections, subprocess, shlex, os
S = sys.argv[1]
canon = collections.defaultdict(dict)   # basename -> {path: blob} for canonical sources
for ln in open(S + '/main_rtl.lst'):
    meta, p = ln.rstrip('\n').split('\t', 1); b = meta.split()[2]
    if p.startswith('rtl/') or '/bind/r18h5_bundle/rtl/' in p:
        canon[os.path.basename(p)][p] = b
PY = open(S + '/rtl_vs_main.py').read().split("PY = r'''")[1].split("'''")[0]
for l in open(S + '/rtl_vs_main.jsonl'):
    o = json.loads(l); h, kit = o['kit'].split(':', 1)
    r = subprocess.run(['ssh', '-o', 'ControlPath=none', '-o', 'BatchMode=yes', h, 'python3 -I -c %s %s' % (shlex.quote(PY), shlex.quote(kit))], capture_output=True, text=True, timeout=300)
    kf = json.loads(r.stdout or '{}')
    res = {'same': [], 'diff': [], 'gen': []}
    for f, b in sorted(kf.items()):
        c = canon.get(os.path.basename(f))
        if not c: res['gen'].append(f)
        elif b in c.values(): res['same'].append(f)
        else: res['diff'].append('%s (main %s)' % (f, ','.join(sorted(c))[:160]))
    print(json.dumps(dict(top=o['top'], kit=o['kit'], origin=o['origin'], n=len(kf), **res)))
