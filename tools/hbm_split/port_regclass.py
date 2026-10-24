#!/usr/bin/env python3
"""HBM-P5-RTLB 10-23: launch / capture class of every bit of the named ports of one module (Yosys RTL, flattened):
  output bit: 'reg' = driven straight by a flop Q (any $*dff* / $dffe / $sdff / $aldff ... cell, through $buf / plain
  connections only), 'const', 'in:<port>' (feed-through), else 'logic';
  input bit:  set of sink classes: 'reg' (flop D), 'ff-ctl' (flop EN / SRST / ARST / CLK), 'logic', 'out:<port>', 'unused'.
usage: port_regclass.py OUT.json TOP 'PARAM=VAL,...' 'port1,port2,...' file1.sv [file2.sv ...]
Ports '*' = all ports.  Defines: env PORTCLASS_DEFINES='A B'."""
import json, os, subprocess, sys, tempfile, collections
out, top, params, ports, files = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:]
tmp = tempfile.mkdtemp(prefix='pcls_')
ch = ' '.join(f'-chparam {p.split("=")[0]} {p.split("=")[1]}' for p in params.split(',') if p)
defs = ' '.join('-D' + d for d in os.environ.get('PORTCLASS_DEFINES', '').split())
scr = f"""read_verilog -sv -nooverwrite {defs} {' '.join(files)}
hierarchy -top {top} {ch}
proc; flatten; opt_expr; opt_dff; opt_clean
write_json {tmp}/n.json
"""
open(f'{tmp}/s.ys', 'w').write(scr)
r = subprocess.run([os.environ.get('YOSYS', os.path.expanduser('~/.local/opentallas-tools/yosys-0.68/bin/yosys')), '-q', '-s', f'{tmp}/s.ys'], capture_output=True, text=True)
if r.returncode:
    sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:]); sys.exit(2)
J = json.load(open(f'{tmp}/n.json'))['modules'][top]
drv, snk = {}, collections.defaultdict(list)
for pn, p in J['ports'].items():
    for i, b in enumerate(p['bits']):
        if p['direction'] == 'input': drv[b] = ('PORT', pn, i)
        else: snk[b].append(('PORT', pn, i))
for cn, c in J['cells'].items():
    t = c['type']; dirs = c.get('port_directions', {})
    for pn, bl in c['connections'].items():
        for b in bl:
            if isinstance(b, str): continue
            if dirs.get(pn) == 'output': drv[b] = ('CELL', t, pn)
            else: snk[b].append(('CELL', t, pn))
isff = lambda t: 'dff' in t or 'dlatch' in t or t.startswith('$mem')
def ocls(b):
    if isinstance(b, str): return 'const'
    d = drv.get(b)
    if d is None: return 'undriven'
    if d[0] == 'PORT': return 'in:' + d[1]
    if isff(d[1]): return 'reg'
    return 'logic'
def icls(b):
    s = set()
    for k in snk.get(b, []):
        if k[0] == 'PORT': s.add('out:' + k[1]); continue
        t, pn = k[1], k[2]
        if isff(t): s.add('reg' if pn in ('D', 'WR_DATA', 'WR_ADDR', 'RD_ADDR') else 'ff-ctl:' + pn)
        else: s.add('logic')
    return sorted(s) or ['unused']
res = {}
want = list(J['ports']) if ports == '*' else ports.split(',')
for pn in want:
    p = J['ports'][pn]
    cl = collections.Counter()
    for b in p['bits']:
        cl['/'.join([ocls(b)] if p['direction'] == 'output' else icls(b))] += 1
    res[pn] = dict(direction=p['direction'], width=len(p['bits']), classes=dict(cl))
json.dump(dict(top=top, params=params, files=files, ports=res), open(out, 'w'), indent=1)
for pn, v in res.items():
    print(f"{pn:28s} {v['direction']:6s} {v['width']:5d} {v['classes']}")
