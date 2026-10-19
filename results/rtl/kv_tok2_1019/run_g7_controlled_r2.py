#!/usr/bin/env python3
"""KV-TOK2 r2: resume the TERMINAL controlled G7 u1 continuation after its GCC15 ICE.

Cause of controlled_u1 compile rc2: cc1plus SIGSEGV on Vtb_qwk_stk_WS__Syms__Slow.o (22 MB Syms.h)
under the default 8 MB stack -- the same GCC15 Syms__Slow ICE that old QK fixed with an unlimited
compiler stack (resume_cpp_stack_20261019).  Not an RTL or fixture fault.
r2 copies (no hardlinks) the immutable controlled_u1 obj + fixture into a NEW dir, verifies the
generated sources are byte-identical, recompiles with `ulimit -s unlimited`, then runs the exact
original u1 case and applies the strict application verdict.  controlled_u1 is never touched.
"""
import hashlib, json, shlex, shutil, subprocess, sys
from pathlib import Path
mon = Path('/srv/opentallas-scratch/claude/kv-token-authority-monitor-1019')
sys.path.insert(0, str(mon))
from identity_verdict import parse_verdict
src = mon / 'controlled_u1'
old = Path('/srv/opentallas-scratch/claude/kv-tok/veh/g7/WSQK')
run = Path(__file__).resolve().parent / 'controlled_r2'
if run.exists(): raise SystemExit('REFUSED: r2 already exists')
cj = json.loads((src / 'compile.json').read_text())
assert cj['state'] == 'TERMINAL' and cj['returncode'] == 2, cj
assert 'internal compiler error' in (src / 'compile.log').read_text(errors='replace')
run.mkdir()
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''): h.update(b)
    return h.hexdigest()
def stage(name, state, **kw):
    (run / f'{name}.json').write_text(json.dumps({'stage': name, 'state': state, **kw}, indent=2) + '\n')
shutil.copytree(src / 'fixture', run / 'fixture', copy_function=shutil.copy2, symlinks=False)
shutil.copytree(src / 'obj', run / 'obj', copy_function=shutil.copy2, symlinks=False)
gen = sorted(p.relative_to(src / 'obj') for p in (src / 'obj').rglob('*') if p.is_file() and p.suffix in ('.cpp', '.h', '.mk'))
bad = [str(r) for r in gen if sha(src / 'obj' / r) != sha(run / 'obj' / r)]
if bad: raise SystemExit(f'copy mismatch {bad[:5]}')
(run / 'copy_receipt.json').write_text(json.dumps({'source': str(src), 'generated_files_checked': len(gen),
    'fixture_receipt': json.loads((src / 'fixture/receipt.json').read_text()), 'cause': 'GCC15 cc1plus SIGSEGV Syms__Slow.o, 8MB stack'}, indent=2) + '\n')
cmd = ['bash', '-c', 'ulimit -s unlimited && ulimit -s && make -f Vtb_qwk_stk_WS.mk -j8 Vtb_qwk_stk_WS']
stage('compile', 'RUNNING', argv=cmd)
with (run / 'compile.log').open('wb') as f:
    r = subprocess.run(['/usr/bin/time', '-v', '-o', str(run / 'compile.time')] + cmd, cwd=run / 'obj', stdout=f, stderr=subprocess.STDOUT)
stage('compile', 'TERMINAL', returncode=r.returncode, argv=cmd)
if r.returncode: raise SystemExit(f'compile rc{r.returncode}; preserved')
cases = [l for l in (old / 'run/cases.txt').read_text().splitlines() if l.startswith('u1 ')]
assert len(cases) == 1
sim = [str(run / 'obj/Vtb_qwk_stk_WS'), '+verilator+rand+reset+2', '+verilator+seed+1', '+verilator+error+limit+1000000'] + shlex.split(cases[0])[1:]
stage('simulation', 'RUNNING', argv=sim)
with (run / 'u1.log').open('wb') as f:
    r = subprocess.run(['/usr/bin/time', '-v', '-o', str(run / 'u1.time')] + sim, cwd=run, stdout=f, stderr=subprocess.STDOUT)
passed, reason = parse_verdict((run / 'u1.log').read_text(errors='replace'), r.returncode)
stage('simulation', 'TERMINAL', returncode=r.returncode, application_verdict={'application_pass': passed, 'reason': reason},
      log_sha256=sha(run / 'u1.log'), argv=sim)
print(json.dumps({'application_pass': passed, 'reason': reason}))
raise SystemExit(0 if passed else 1)
