#!/usr/bin/env python3
"""KV-ING-5 vF: splice the synthesized wa_fix netlist (cut 19) into the vE mapped netlist; st_wa_r D <- wa_fix.d."""
import re, sys, json
big_p, fix_p, out_p = sys.argv[1:4]
big = open(big_p).read()
fix = open(fix_p).read()
# ---- index flop pins in the big netlist
inst_re = re.compile(r'^  (\w+) (\\\S+|\w+)\s*\(\n(.*?)\n  \);', re.M | re.S)
pin_re = re.compile(r'\.(\w+)\(([^()]*)\)')
flops = {}
for m in inst_re.finditer(big):
    name = m.group(2)
    if 'u_rf_core.u_eng.' not in name: continue
    pins = {p: v.strip() for p, v in pin_re.findall(m.group(3))}
    flops[name.lstrip('\\')] = (m.group(1), pins, m.start(3), m.end(3))
def fl(reg, bit=None):
    pref = 'u_rf_core.u_eng.%s' % reg + ('' if bit is None else '[%d]' % bit) + '$'
    c = [k for k in flops if k.startswith(pref)]
    assert len(c) == 1, (pref, c)
    return flops[c[0]], c[0]
def net(reg, bit, pin):
    (cell, pins, s, e), n = fl(reg, bit)
    v = pins[pin]
    return v if v.startswith('\\') is False else v + ' '
conn = {}
for i in range(32):
    k = ('ap_kscal', 0) if i == 0 else ('ap_kcode', i)
    conn['kq_n[%d]' % i] = net(*k, 'QN')
    conn['sq_n[%d]' % i] = net('ap_kscal', i, 'QN')
    conn['rq_n[%d]' % i] = net('ap_raddr', i, 'QN'); conn['waq_n[%d]' % i] = net('st_wa_r', i, 'QN')
    conn['d[%d]' % i] = '_kv5f_d%d_' % i
for i in range(5): conn['secq_n[%d]' % i] = net('st_sec', i, 'QN')
for i in range(3): conn['phq_n[%d]' % i] = net('st_ph', i, 'QN'); conn['mdq_n[%d]' % i] = net('st_mode', i, 'QN')
conn['mdq_n[3]'] = net('st_d', 3, 'QN')
conn['actq_n'] = net('st_act', None, 'QN'); conn['padq_n'] = net('st_pad', None, 'QN')
# ---- wa_fix body
fm = re.search(r'module wa_fix\(.*?\);\n(.*)endmodule', fix, re.S)
body = fm.group(1)
ports = set()
for d in re.findall(r'^\s*(?:input|output)\s+(?:\[(\d+):(\d+)\]\s+)?(\w+);', body, re.M):
    ports.add(d[2])
lines_out = []; wires = []
for ln in body.split('\n'):
    s = ln.strip()
    if not s or s.startswith(('input', 'output')): continue
    if s.startswith('wire'):
        mm = re.match(r'wire\s+(?:\[(\d+):(\d+)\]\s+)?(\S+)\s*;', s)
        nm = mm.group(3)
        if nm in ports: continue
        if nm.startswith('\\'): nn = '\\kv5f.' + nm[1:] + ' '
        else:
            assert re.fullmatch(r'_\d+_', nm), nm
            nn = '_kv5f' + nm
        wires.append('  wire ' + (('[%s:%s] ' % (mm.group(1), mm.group(2))) if mm.group(1) else '') + nn + ';')
        continue
    lines_out.append(ln)
txt = '\n'.join(lines_out)
def sub_net(v):
    v = v.strip()
    if v in conn: return conn[v]
    mm = re.fullmatch(r'(\w+)\[(\d+)\]', v)
    if mm and v in conn: return conn[v]
    if v in ports: return conn[v]
    if v.startswith('\\'): return '\\kv5f.' + v[1:] + ' '
    mm = re.fullmatch(r'(_\d+_)(\[\d+\])?', v)
    if mm: return '_kv5f' + mm.group(1) + (mm.group(2) or '')
    if v.startswith("1'h") or v.startswith("1'b"): return v
    raise SystemExit('unmapped net %r' % v)
txt = re.sub(r'\.(\w+)\(([^()]*)\)', lambda m: '.%s(%s)' % (m.group(1), sub_net(m.group(2))), txt)
# instance names
txt = re.sub(r'^(  \w+ )\\(ap_k\w+\[\d+\]\$_DFF_PN[01]_) ', lambda m: m.group(1) + '\\u_rf_core.u_eng.' + m.group(2) + ' ', txt, flags=re.M)
txt = re.sub(r'^(  \w+ )(_\d+_) ', lambda m: m.group(1) + '_kv5f' + m.group(2) + ' ', txt, flags=re.M)
assert 'assign' not in txt, 'assigns in wa_fix netlist: handle'
# ---- rewire st_wa_r D
old = {}
edits = []
for i in range(32):
    (cell, pins, s, e), n = fl('st_wa_r', i)
    blk = big[s:e]
    nb = re.sub(r'\.D\(([^()]*)\)', '.D(_kv5f_d%d_)' % i, blk, count=1)
    assert nb != blk
    old[i] = pins['D']; edits.append((s, e, nb))
for s, e, nb in sorted(edits, reverse=True):
    big = big[:s] + nb + big[e:]
# ---- insert into top module (last endmodule)
k = big.rfind('endmodule')
ins = '  // KV-ING-5 vF cut 19 splice (wa_fix, exact, 0 cycles)\n' + '\n'.join(wires) + '\n' + '\n'.join('  wire _kv5f_d%d_;' % i for i in range(32)) + '\n' + txt + '\n'
big = big[:k] + ins + big[k:]
open(out_p, 'w').write(big)
json.dump({'conn': conn, 'old_st_wa_r_D': old, 'wires': len(wires), 'cells': len(re.findall(r'^  \w+_ASAP7_75t_R ', txt, re.M))}, open(out_p + '.splice.json', 'w'), indent=1)
print('SPLICE cells', len(re.findall(r'^  \w+_ASAP7_75t_R ', txt, re.M)), 'wires', len(wires))
