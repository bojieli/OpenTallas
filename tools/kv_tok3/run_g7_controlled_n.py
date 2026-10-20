#!/usr/bin/env python3
"""KV-TOK3 10-19: controlled G7 WSQK fixture generalised to N-step (4-user) programmes: u4pack (NSTEP 4) + u4cal (NSTEP 8).

Reuses the r2 continuation's hierarchical CHILD objects unchanged (copied, sha-checked against the monitor lane's
reuse audit; no child is regenerated or recompiled).  Only the top (tb + fixture) is re-verilated and compiled, because the
identity adapter is compiled into the top: the exact-u1 adapter $fatals at NSTEP != 1 (g7_identity_bind.svh), so u4 cases
cannot run on the r2 binary.  Fixture delta vs r2: g7_identity_bind.svh -> kva_identity_bind_n.svh and
kva_identity_scoreboard.sv -> kva_identity_scoreboard_n.sv (runtime n_active); driver, tb, authority, fault binds,
RTL, gold, programme, deadlines unchanged.  Runs u4pack, u4cal and u1 (N-adapter regression vs r2 u1) in parallel.
"""
import hashlib, json, shlex, shutil, subprocess, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
mon = Path('/srv/opentallas-scratch/claude/kv-token-authority-monitor-1019')
sys.path.insert(0, str(mon))
from identity_verdict import parse_verdict
here = Path(__file__).resolve().parent
r2 = Path('/srv/opentallas-scratch/claude/kv-tok2-1019/controlled_r2')
old = Path('/srv/opentallas-scratch/claude/kv-tok/veh/g7/WSQK')
run = here / 'controlled_n'
if run.exists(): raise SystemExit('REFUSED: controlled_n already exists')
run.mkdir(); obj = run / 'obj'; obj.mkdir()
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''): h.update(b)
    return h.hexdigest()
def stage(name, state, **kw):
    (run / f'{name}.json').write_text(json.dumps({'stage': name, 'state': state, **kw}, indent=2) + '\n')
def call(name, cmd, cwd):
    stage(name, 'RUNNING', argv=cmd)
    with (run / f'{name}.log').open('wb') as f:
        r = subprocess.run(['/usr/bin/time', '-v', '-o', str(run / f'{name}.time')] + cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    stage(name, 'TERMINAL', returncode=r.returncode, argv=cmd)
    if r.returncode: raise SystemExit(f'{name} failed rc{r.returncode}; logs preserved')
audit = json.loads((mon / 'controlled_u1/reuse_audit.json').read_text()); assert audit['status'] == 'PASS'
TOPDIR = 'Vtb_qwk_stk_WS__hier.dir'   # the TOP's own frontend dependency file (rewritten by every top frontend), not a child
for q in sorted((r2 / 'obj').glob('V*')):
    if q.is_dir() and q.name != TOPDIR: shutil.copytree(q, obj / q.name, copy_function=shutil.copy2, symlinks=False)
child = {n: p for n, p in audit['reusable_files'].items() if Path(n).relative_to(old / 'run/obj').parts[0] != TOPDIR}
assert len(child) == len(audit['reusable_files']) - 1, len(child)
nchk = 0
for name, pin in child.items():
    rel = Path(name).relative_to(old / 'run/obj'); c = obj / rel
    if sha(c) != pin['sha256']: raise SystemExit(f'reused child mismatch {rel}')
    nchk += 1
fx = run / 'fixture'; shutil.copytree(r2 / 'fixture', fx, copy_function=shutil.copy2)
for n in ['kva_identity_bind_n.svh', 'kva_identity_scoreboard_n.sv']: shutil.copy2(here / n, fx / n)
d = (fx / 'drive_qwk_slice_attn_mu.svh').read_text()
assert sha(fx / 'drive_qwk_slice_attn_mu.svh') == json.loads((fx / 'receipt.json').read_text())['driver']
a = '`include "g7_identity_bind.svh"'; assert d.count(a) == 1
(fx / 'drive_qwk_slice_attn_mu.svh').write_text(d.replace(a, '`include "kva_identity_bind_n.svh"'))
(fx / 'g7_identity_bind.svh').unlink(); (fx / 'kva_identity_scoreboard.sv').unlink()
args = [json.loads(l) for l in (mon / 'controlled_u1/top_args.f').read_text().splitlines() if l.strip()]
src_fx = str(mon / 'controlled_u1/fixture'); out = []
for i, x in enumerate(args):
    x = x.replace(src_fx, str(fx)).replace(str(mon / 'controlled_u1/obj'), str(obj))
    if x.endswith('/kva_identity_scoreboard.sv'): x = str(fx / 'kva_identity_scoreboard_n.sv')
    out.append(x)
assert not any('kv-token-authority-monitor-1019/controlled_u1' in x for x in out)
(run / 'top_args.f').write_text('\n'.join(json.dumps(x) for x in out) + '\n')
(run / 'receipt.json').write_text(json.dumps({'children_from': str(r2 / 'obj'), 'children_sha_checked': nchk,
    'fixture_from': str(r2 / 'fixture'), 'fixture_files': {p.name: sha(p) for p in sorted(fx.iterdir())},
    'delta': 'identity adapter + ledger generalised to runtime NSTEP; driver/tb/authority/fault/RTL/gold/deadlines unchanged',
    'status': 'SOURCE_ONLY_NOT_VALIDATED'}, indent=2) + '\n')
call('frontend', ['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator', '-f', str(run / 'top_args.f')], obj)
hier = (old / 'run/obj/Vtb_qwk_stk_WS_hier.mk').read_text().split('hier_build:', 1)[0]
(obj / 'Vtb_qwk_stk_WS_hier.mk').write_text(hier + '\nendif\n')
call('compile', ['bash', '-c', 'ulimit -s unlimited && make -f Vtb_qwk_stk_WS.mk -j16 Vtb_qwk_stk_WS'], obj)
for name, pin in child.items():
    rel = Path(name).relative_to(old / 'run/obj')
    if sha(obj / rel) != pin['sha256']: raise SystemExit(f'reused child changed during build {rel}')
cases = {l.split()[0]: l for l in (old / 'run/cases.txt').read_text().splitlines() if l.strip()}
def sim(c):
    argv = [str(obj / 'Vtb_qwk_stk_WS'), '+verilator+rand+reset+2', '+verilator+seed+1', '+verilator+error+limit+1000000'] + shlex.split(cases[c])[1:]
    stage(f'sim_{c}', 'RUNNING', argv=argv)
    with (run / f'{c}.log').open('wb') as f:
        r = subprocess.run(['/usr/bin/time', '-v', '-o', str(run / f'{c}.time')] + argv, cwd=run, stdout=f, stderr=subprocess.STDOUT)
    ok, why = parse_verdict((run / f'{c}.log').read_text(errors='replace'), r.returncode)
    stage(f'sim_{c}', 'TERMINAL', returncode=r.returncode, application_verdict={'application_pass': ok, 'reason': why},
          log_sha256=sha(run / f'{c}.log'), argv=argv)
    return c, ok, why
with ThreadPoolExecutor(3) as ex: res = list(ex.map(sim, ['u4pack', 'u4cal', 'u1']))
print(json.dumps(res)); raise SystemExit(0 if all(r[1] for r in res) else 1)
