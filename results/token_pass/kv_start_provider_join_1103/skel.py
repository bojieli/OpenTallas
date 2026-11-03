#!/usr/bin/env python3
"""DIE-KV-63/start: START-infrastructure skeleton of a bound KV partition.
Keeps the module header, declarations, assigns and every ot_dp_* infrastructure cell (relays, landings, stations,
rgate, rsync, collect); drops every core instance (their outputs become undriven = 0); replaces the C45 HOST u_host
by dkv63_host_stub wired to the SAME nets for mission_start / static_setup_ready / d2d_boot_begin / ck_ctl / por_n.
Optional --inject NET=EXPR adds 'assign NET = EXPR;' (used to drive hub_C's kvs_ctl setup_ready core output)."""
import re, sys, argparse, json
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('out'); ap.add_argument('--inject', action='append', default=[])
a = ap.parse_args()
lines = open(a.src).read().split('\n')
out = []; i = 0; stats = {}
# header: up to the first line that closes the port list
while i < len(lines):
    out.append(lines[i]); i += 1
    if re.match(r'^\s*\);\s*(//.*)?$', lines[i-1]): break
KEEP = ('wire', 'reg', 'input', 'output', 'assign', 'parameter', 'localparam', 'endmodule', '`')
buf = []
def flush(stmt):
    s = re.sub(r'\(\*.*?\*\)', '', stmt).strip()
    tok = re.match(r'[`\w]+', s).group(0) if re.match(r'[`\w]+', s) else ''
    if tok.startswith(KEEP) or tok.startswith('ot_dp_'):
        k = 'keep:' + (tok if tok.startswith('ot_dp_') else 'decl'); out.append(stmt)
    elif tok == 'qkd_host_root_admission_obsx_bo1_c45':
        conn = dict(re.findall(r'\.(\w+)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)', s))
        need = ['ck_ctl', 'por_n', 'mission_start', 'static_setup_ready', 'd2d_boot_begin']
        out.append('    dkv63_host_stub u_host (' + ', '.join(f'.{n}({conn[n].strip()})' for n in need) + ');')
        k = 'stub:u_host'
    elif tok in ('always', 'initial', 'generate', 'function', 'task'):
        raise SystemExit(f'unexpected behavioural statement in partition: {s[:80]}')
    else:
        k = 'drop:' + tok
    stats[k] = stats.get(k, 0) + 1
for ln in lines[i:]:
    code = ln.split('//')[0].rstrip()
    if not buf and not code.strip():
        continue
    if not buf and (code.strip() == 'endmodule' or code.strip().startswith('`')):
        out.append(ln); continue
    buf.append(ln)
    if code.endswith(';'):
        flush('\n'.join(buf)); buf = []
assert not buf, buf[:3]
if a.inject:
    j = max(k for k, l in enumerate(out) if l.strip() == 'endmodule')
    out[j:j] = [f'    assign {x.split("=",1)[0]} = {x.split("=",1)[1]};  // DIE-KV-63 skeleton injection' for x in a.inject]
open(a.out, 'w').write('\n'.join(out))
print(json.dumps({'src': a.src, 'stats': stats}))
