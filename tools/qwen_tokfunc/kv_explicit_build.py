#!/usr/bin/env python3
"""TOK.QW stage kv --explicit-r17 (TOKc-QW2 10-22, coordinator decision (a)): build the current r17 KV attention vehicle
tb_kvattn_rel ON THE SOURCE ASSEMBLY tree with the ROOT-approved explicit genuine-archive binding (b0cc8cdca).

Why: the implicit hierarchical top re-expands the native QK/PV arithmetic into the top frontend (r17 top OOM at
64/192/384 GiB; job4 peaked ~590 GB).  Naming the 5 real protected specialisations explicitly (kvattn_rel_dp.sv overlay +
kvattn_rel_pv_bound.sv wires-only alias) makes the top frontend ~1 s / ~100 MB.  The 35 child implementation archives are
reused, never rebuilt, and are admitted ONLY when (1) every archive sha256 equals the approved table and (2) every source
file of the approved child readset is byte-identical in THIS assembly tree.  Exempt: bench files (rtl/test/, tools/)
and qkd_native_attention_record.sv, which no hierarchical child instantiates (only qkd_native_attention_static_ctl*, which
is in the top): the top is regenerated here from the assembly's version.

  kv_explicit_build.py --tree T --out O --archives OBJDIR
"""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--tree', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--archives', type=Path, required=True)
# KV-P2-RTL 10-23: a named data-path overlay variant (e.g. kv_planframe/kvattn_rel_dp.sv, the KV die plan v3 PV frame);
# the tree's kvattn_rel_dp.sv must then hash to THIS file instead of the approved overlay; recorded in explicit_build.json.
ap.add_argument('--overlay-dp', type=Path, default=None)
a = ap.parse_args()
E = Path(__file__).resolve().parent / 'kv_explicit_r17'
spec = json.loads((E / 'spec.json').read_text())
T, O = a.tree.resolve(), a.out.resolve()
obj = O / 'obj'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
fail = lambda m: (print('EXPLICIT_BUILD_FAIL', m, flush=True), sys.exit(1))
TOP_ONLY = {'rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv'}

# 1. tree identity: selected r17 sources and the approved overlay/alias
B = 'rtl/test/qwen_kv_die/kvattn_rel_1019/'
for f, h in spec['selected_r17_sources'].items():
    if sha(T / f) != h: fail(f'assembly {f} differs from the approved r17 source')
dp_want = sha(a.overlay_dp) if a.overlay_dp else spec['overlay_dp_sha256']
if sha(T / (B + 'kvattn_rel_dp.sv')) != dp_want: fail('overlay dp sha')
if sha(T / (B + 'kvattn_rel_pv_bound.sv')) != spec['pv_alias_sha256']: fail('pv alias sha')
# 2. child readset == assembly bytes
rs = {}
for f, h in sorted(spec['child_readset'].items()):
    if f.startswith(('rtl/test/', 'tools/')) or f in TOP_ONLY:
        rs[f] = 'exempt (bench / top-only)'; continue
    p = T / f
    if not p.exists(): fail(f'child readset file missing from assembly: {f}')
    if sha(p) != h: fail(f'child readset file differs from assembly: {f}')
    rs[f] = 'identical'
# 3. genuine archives (child dirs only) + identity
obj.mkdir(parents=True, exist_ok=True)
for lib, h in spec['libraries'].items():
    d = lib.split('/')[0]
    if not (obj / d).exists(): shutil.copytree(a.archives / d, obj / d, symlinks=False)
    if sha(obj / lib) != h: fail(f'archive {lib} sha mismatch before frontend')
# 4. top-only frontend on the assembly tree
vl = str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator')
(O / 'top.f').write_text((E / 'top.f.in').read_text().replace('@MDIR@', str(obj)))
def call(args, log, cwd):
    print(' '.join(args), flush=True)
    with (O / log).open('w') as out:
        if subprocess.run(args, cwd=cwd, stdout=out, stderr=subprocess.STDOUT).returncode: fail(f'{log} (see {O / log})')
call([vl, '-f', str(O / 'top.f')], 'generate.log', T)
# top-only generation emits no _hier.mk; the hierarchical one is entirely inside ifndef VM_HIER_VERILATION_INCLUDED
(obj / 'Vtb_kvattn_rel_hier.mk').write_text('# explicit binding: children = the verified archives in VM_HIER_LIBS; no child rebuild\n')
libs = list(spec['libraries'])
flags = ['VM_HIER_VERILATION_INCLUDED=1', 'VM_HIER_LIBS=' + ' '.join(libs)]
call(['make', '-n', '-f', 'Vtb_kvattn_rel.mk', *flags, 'Vtb_kvattn_rel'], 'make_dry.log', obj)
dry = (O / 'make_dry.log').read_text()
if 'hier_launch_verilator' in dry or 'make -C' in dry or 'make -f' in dry: fail('make would rebuild children')
call(['make', '-j6', '-f', 'Vtb_kvattn_rel.mk', *flags, 'Vtb_kvattn_rel'], 'build.log', obj)
for lib, h in spec['libraries'].items():
    if sha(obj / lib) != h: fail(f'archive {lib} changed by make')
rec = dict(overlay_dp=(dict(variant=str(a.overlay_dp), sha256=dp_want) if a.overlay_dp else 'approved'), scope='current r17 KV attention vehicle built on the source assembly tree, explicit genuine-archive binding (b0cc8cdca)',
           binary_sha256=sha(obj / 'Vtb_kvattn_rel'), top_params=spec['top_params'], libraries=spec['libraries'],
           child_readset=rs, top_sources={l: sha(T / l) for l in (T / 'tools/qwen_layerbench/kvattn_rel/sources.txt').read_text().split()
                                           if l and not l.startswith('#')})
(O / 'explicit_build.json').write_text(json.dumps(rec, indent=1) + '\n')
print('EXPLICIT_BUILD_PASS', rec['binary_sha256'], flush=True)
