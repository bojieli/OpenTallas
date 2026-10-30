#!/usr/bin/env python3
"""DIE-HEAD-30 10-29: head_die_portbind END-TO-END on a REALIZED HEAD source (COORD condition 10-29 on the DIE-HEAD-28
closure patch).  Same steps as tools/s81_head/head_die_portbind.py, with the plan-generation step replaced by the
realized source copy (Codex codex-head-ca-0840/prepare_source_bind.py logic, unchanged, made path-parametric):

  run_source_portbind.py SRC_DIR OUT_DIR FULL_CLONE REV     (cwd = repo root of a checkout at REV)

0. head_module_check.py SRC/source_plan.json --rev REV (module definitions grepped in FULL_CLONE at REV: the sparse
   blobless checkout cannot git-grep every blob)
1. copy SRC -> OUT/source; 2. non-ANSI die top (header syntax only); 3. pads = actually-open rst_o_/start_o_ outs +
   report.json unused_uniform_exports; 6. straps.json = parent ID straps + count straps; tie audit + count-strap audit
4. manifest = tools/s81_head/head_source_bind_manifest.py (repo-relative + landing closure)
5. tools/die_port_bind.py --manifest-only --logic-free-stub --pad-file --strap-file
7. nested leaf-pin check = tools/s81_head/head_source_nested_check.py (main port_bind_gate.nested_check)
Exit 0 iff all PASS."""
import json, re, shutil, subprocess, sys
from pathlib import Path

src, out, full, rev = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, 'tools/die_plan'); sys.path.insert(0, 'tools/s81_head')
import head_module_check as HM  # noqa: E402
r = subprocess.run(['git', '-C', full, 'grep', '-n', '-E', r'^\s*(\(\*.*\*\)\s*)?module\s+[A-Za-z_]\w*', rev, '--',
                    '*.sv', '*.v', ':!results/**', ':!*_bb.v', ':!docs/**'], capture_output=True, text=True, check=True)
d = {}
for line in r.stdout.splitlines():
    _, path, _, text = line.split(':', 3)
    m = re.search(r'module\s+([A-Za-z_]\w*)', text)
    if m: d.setdefault(m.group(1), []).append(path)
HM._DEFS[rev] = d
mrc = HM.main([str(src / 'source_plan.json'), '--rev', rev, '--out', str(out / 'module_check.json')])
mc = json.loads((out / 'module_check.json').read_text())

o = out / 'source'
if o.exists(): shutil.rmtree(o)
shutil.copytree(src, o)
p = json.load(open(o / 'source_plan.json')); side = json.load(open(o / 'source_sidecar.json')); report = json.load(open(o / 'report.json'))
import schema as S, gen_rtl as G, clock_landings as CL, straps as STR  # noqa: E402
P = S.Plan(p, o / 'source_plan.json'); L = CL.Landings(p, side)
top = o / 's81_head_top.sv'; text = top.read_text(); m = re.search(r'module\s+s81_head_top\s*\((.*?)\);', text, re.S)
decl = [x.strip() for x in m[1].split(',') if x.strip()]; names = [x.split()[-1] for x in decl]
text = text[:m.start()] + 'module s81_head_top (' + ', '.join(names) + ');\n' + ''.join('    ' + x + ';\n' for x in decl) + text[m.end():]
(o / 's81_head_top_nonansi.sv').write_text(text)
man = G.parent_id_manifest(P)
for tn, ports in L.strap_declarations().items():
    man['types'].setdefault(tn, {}).update({sp: dict(width=w, kind='count_strap') for sp, w in ports.items()})
for part, ports in L.strap_expected().items():
    man['instances'].setdefault(part, {}).update({sp: dict(width=w, value=v, kind='count_strap') for sp, (w, v) in ports.items()})
(o / 'straps.json').write_text(json.dumps({'straps': sorted([P.types[tn]['module'], sp] for tn, ps in man['types'].items() for sp in ps)}, indent=1))
aud = STR.audit_top_ties(text, man, {t['module']: tn for tn, t in P.types.items()})
(out / 'tie_audit.json').write_text(json.dumps(dict(aud, rows=len(aud['rows'])), indent=1))
cnt = STR.audit_count_strap_values(text, {CL.ident(q): v for q, v in L.strap_expected().items()})
(out / 'count_audit.json').write_text(json.dumps(cnt, indent=1))
pads = {'instances': {}}; inst = pads['instances']
for im in re.finditer(r'^\s{4}(\w+)(?:\s*#\(.*?\))?\s+(\w+)\s*\((.*?)\n\s{4}\);', text, re.S | re.M):
    mod, iname, body = im.groups(); opn = re.findall(r'\.((?:rst|start)_o_\d+)\(\s*\)', body)
    if opn: inst[iname] = dict(master=mod, reason='actual emitted no-child output of a uniform reset/START wavefront type', ports={q: [[0, 0]] for q in opn})
for u in report['unused_uniform_exports']:
    part = u['part']; iname = G.sv_id(part); mod = P.ptype(part)['module']
    row = inst.setdefault(iname, dict(master=mod, reason=u['reason'], ports={}))
    raw = next(q for q in P.ptype(part)['reset_start_raw_exports'] if q['port'] == u['port'])
    row['ports'][raw.get('existing_port') or u['port']] = [[0, 0]]
(o / 'pads.json').write_text(json.dumps(pads, indent=1))
print('TIE_AUDIT %s accepted=%d rejected=%d COUNT_AUDIT %s pads=%d inst/%d ports' % (aud['verdict'], len(aud['accepted']), len(aud['rejected']),
      cnt['verdict'], len(inst), sum(len(v['ports']) for v in inst.values())))
mf = subprocess.run([sys.executable, 'tools/s81_head/head_source_bind_manifest.py', str(o), str(out / 'manifest.f')], capture_output=True, text=True)
print(mf.stdout.strip(), mf.stderr[-800:])
pb = subprocess.run([sys.executable, 'tools/die_port_bind.py', str(o / 's81_head_top_nonansi.sv'), '--top', 's81_head_top', '-f', str(out / 'manifest.f'),
                     '--pad-file', str(o / 'pads.json'), '--strap-file', str(o / 'straps.json'), '--out', str(out / 'port_bind_strict.json'),
                     '--logic-free-stub', '--manifest-only'], capture_output=True, text=True)
(out / 'port_bind_strict.txt').write_text(pb.stdout + pb.stderr)
print(pb.stdout[-2500:], pb.stderr[-800:])
ns = subprocess.run([sys.executable, 'tools/s81_head/head_source_nested_check.py', str(o.resolve()), str(out / 'manifest.f'), str(out / 'nested_portbind.json')],
                    capture_output=True, text=True)
print(ns.stdout[-1500:], ns.stderr[-800:])
nest = json.loads((out / 'nested_portbind.json').read_text()) if (out / 'nested_portbind.json').exists() else {'verdict': 'ERROR'}
ok = mrc == 0 and aud['verdict'] == 'PASS' and cnt['verdict'] == 'PASS' and mf.returncode == 0 and pb.returncode == 0 and nest['verdict'] == 'PASS'
print('HEAD_DIE_PORTBIND_SOURCE %s module_check=%s missing=%s tie_audit=%s count_audit=%s manifest_rc=%d port_bind_rc=%d nested=%s' % (
    'PASS' if ok else 'FAIL', mc['verdict'], mc['missing_modules'], aud['verdict'], cnt['verdict'], mf.returncode, pb.returncode, nest['verdict']))
sys.exit(0 if ok else 1)
