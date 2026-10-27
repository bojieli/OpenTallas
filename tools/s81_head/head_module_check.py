#!/usr/bin/env python3
"""HEAD-RTL 2026-10-26: whole-die content-module check of an s81_head plan (canonical or candidate).

Generates the die top + every partition wrapper with tools/die_plan/gen.py rtl (no --rtl-root, so it never needs the
leaf sources checked out), then resolves every instantiated module to a real RTL definition in the git tree REV:
  * a wrapper that instantiates its own name as u_core (plan type module == content module) is a MISSING provider;
  * any other module must be defined (`module NAME`) in a tracked .sv/.v file of REV, excluding archived results/
    readsets and *_bb.v black boxes (a blackbox is not RTL; macro models live in physical/asap7_memory_macros_v2).
Prints one JSON verdict; exit 0 iff 0 missing.  Leaf port binding is checked separately by gen.py rtl --rtl-root.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
INST = re.compile(r'^\s*([A-Za-z_]\w*)\s*(?:#\s*\((?:[^;]*?)\))?\s+([A-Za-z_]\w*)\s*\(\s*$', re.M)
KEYWORDS = {'module', 'input', 'output', 'wire', 'reg', 'assign', 'always', 'if', 'else', 'begin', 'end', 'for',
            'generate', 'localparam', 'parameter', 'function', 'task', 'case', 'endmodule'}


def defined(rev, name, cache={}):
    if name in cache: return cache[name]
    r = subprocess.run(['git', '-C', str(ROOT), 'grep', '-l', '-E', rf'^\s*(\(\*.*\*\)\s*)?module\s+{name}\b', rev, '--',
                        '*.sv', '*.v', ':!results/**', ':!*_bb.v', ':!docs/**'], capture_output=True, text=True)
    files = [l.split(':', 1)[1] for l in r.stdout.split() if ':' in l]
    cache[name] = files
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan'); ap.add_argument('--rev', default='HEAD'); ap.add_argument('--out')
    a = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as td:
        g = subprocess.run([sys.executable, str(ROOT / 'tools/die_plan/gen.py'), 'rtl', a.plan, '--out', td],
                           capture_output=True, text=True)
        if g.returncode: print(g.stdout[-2000:], g.stderr[-2000:]); return 2
        gen = {p.name: p.read_text() for p in Path(td).glob('*.sv')}
    genmods = {m for t in gen.values() for m in re.findall(r'^\s*module\s+(\w+)', t, re.M)}
    plan = json.loads(Path(a.plan).read_text())
    rows, missing = [], []
    for tn, t in plan['partition_types'].items():
        for c in t.get('contents', []):
            mod = c['module']
            if mod == t['module']:
                files, why = [], 'content module == generated wrapper name (no provider)'
            elif '.' in mod:
                files, why = [], 'not a module name'
            else:
                files = defined(a.rev, mod); why = None if files else 'no RTL definition in ' + a.rev
            rows.append(dict(type=tn, inst=c['inst'], module=mod, files=files, missing=why))
            if why: missing.append(dict(type=tn, module=mod, reason=why))
    # every module instantiated in the generated wrappers/top resolves (generated or RTL)
    inst = sorted({m for t in gen.values() for m, _ in INST.findall(t)} - KEYWORDS)
    unres = [m for m in inst if m not in genmods and not defined(a.rev, m)]
    v = dict(schema='opentallas.s81_head.module_check.v1', plan=a.plan, rev=a.rev,
             verdict='PASS' if not missing and not unres else 'FAIL', missing_modules=len(missing), missing=missing,
             unresolved_instances=unres, types=len(plan['partition_types']), contents=rows)
    s = json.dumps(v, indent=1)
    if a.out: Path(a.out).write_text(s + '\n')
    print('HEAD_MODULE_CHECK', v['verdict'], 'missing', len(missing), json.dumps(missing), 'unresolved', unres)
    return 0 if v['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
