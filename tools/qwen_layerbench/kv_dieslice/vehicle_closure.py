#!/usr/bin/env python3
"""TOK-KV-1 10-28: close a staged kv_dieslice vehicle over its leaf modules and packages WITH THE BINDER'S OWN CLOSURE.

A bound KV top (tools/die_plan/bind.py) lists only the partitions and the as-built parents (bind.f); the leaves below
them are resolved by the binder's index + closure (the one the verify lint and every G3 kit use: bind_elab.module_index
over the manifest's rtl_roots / files + the bind's extra_lib, prefer = manifest prefer + extra_lib + bind.f, then
bind.kit_closure + bind.kit_packages).  This tool runs exactly that closure for the vehicle, so the bench compiles the
leaves the bind was verified with -- no hand-kept leaf dirs, no lint-log loop, no copy of an older bind's list:
  - needed modules = instantiations in the staged bound RTL (files.f) and in the bench sources (--bench: host board port,
    compute-die end, PHY models), minus every module those files define themselves (the bench's off-die PHY models
    replace the hard-macro black boxes);
  - a hard memory macro (macro view dir) takes its behavioural model <m>.v (simulation view), else its black box;
  - packages first (kit_packages dependency order), then modules; files already listed are not added twice;
  - every added file is copied into VDIR/src/close__<repo path> (self-contained vehicle) and recorded in
    VDIR/vehicle_closure.json.  rc 2 when a needed module has no source.
The manifest is the bind's own (BIND/provenance_bind.json "manifest", repository-relative), read from TREE.
    vehicle_closure.py VDIR TREE [--bench FILE ...]   (VDIR holds the staged bind_report.json + provenance_bind.json)"""
import argparse, json, os, re, shutil, sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vdir'); ap.add_argument('tree'); ap.add_argument('--bench', nargs='*', default=[])
    a = ap.parse_args()
    V, T = Path(a.vdir).resolve(), Path(a.tree).resolve()
    sys.path.insert(0, str(T / 'tools/die_plan'))
    import bind_elab as E
    import bind as B
    prov = json.loads((V / 'provenance_bind.json').read_text())['provenance']
    rep = json.loads((V / 'bind_report.json').read_text())
    mpath = T / prov['manifest']
    ab = json.loads(mpath.read_text())
    base = B.plan_base(str(mpath), {'asbuilt': ab})
    rd = lambda n: [l.strip() for l in open(V / n) if l.strip()] if (V / n).exists() else []
    files, host = rd('files.f'), rd('hostside.f')
    own = files + host + list(a.bench)
    defined, used = set(), set()
    for f in own:
        t = E._strip(Path(f).read_text(errors='replace'))
        defined |= {m.group(1) for m in E.MOD_RE.finditer(t)}
    idx = E.module_index(ab.get('rtl_roots', ['rtl']), list(ab.get('files', [])) + list(rep.get('extra_lib', [])), base)
    prefer = [str(Path(base) / f) if not Path(f).is_absolute() else f for f in ab.get('prefer', [])] + \
        rep.get('extra_lib', []) + B.bindf_prefer(V, base)
    views = B.macro_views(base)
    known = set(idx) | set(views)
    for f in own:
        t = E._strip(Path(f).read_text(errors='replace'))
        for m in E.MOD_RE.finditer(t):
            used |= E.instantiated(E.module_body(f, m.group(1)), known)
    need = sorted(used - defined)
    # the closure must not descend into or re-add what the vehicle defines itself (bound partitions, bench PHY models)
    sub = {k: v for k, v in idx.items() if k not in defined}
    picks = {}
    cl, missing, macros = B.kit_closure(need, sub, prefer, picks, views={k: v for k, v in views.items() if k not in defined})
    sim = {m['bb']: m['model'] for m in macros.values() if m.get('bb') and m.get('model')}
    cl = [sim.get(f, f) for f in cl]
    pkgs = [str(p) for p in B.kit_packages([Path(f) for f in own + cl], ab.get('rtl_roots', ['rtl']), base)]
    have = {os.path.realpath(f) for f in own}
    haveb = {}
    for f in own:
        haveb.setdefault(os.path.basename(f), []).append(f)

    def listed(f):
        if os.path.realpath(f) in have:
            return True
        return any(Path(g).read_bytes() == Path(f).read_bytes() for g in haveb.get(os.path.basename(f), []))

    def stage(f):
        p = Path(f).resolve()
        try:
            rel = p.relative_to(Path(base).resolve())
        except ValueError:
            rel = Path(str(p).lstrip('/'))
        d = V / 'src' / ('close__' + str(rel.parent).replace('/', '__'))
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, d / p.name)
        return str(d / p.name), str(rel)
    add_p, add_m, rec = [], [], {'manifest': prov['manifest'], 'bind_commit': prov.get('commit'), 'base': str(base),
                                 'packages': [], 'modules': [], 'macros_sim_model': sorted(sim), 'missing': missing}
    for f in pkgs:
        if not listed(f):
            q, r = stage(f); add_p.append(q); rec['packages'].append(r); have.add(os.path.realpath(f))
    for f in cl:
        if not listed(f):
            q, r = stage(f); add_m.append(q); rec['modules'].append(r); have.add(os.path.realpath(f))
    (V / 'files.f').write_text('\n'.join(add_p + files + add_m) + '\n')
    (V / 'vehicle_closure.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f'VEHICLE_CLOSURE manifest {prov["manifest"]} needed {len(need)} packages +{len(add_p)} files +{len(add_m)} '
          f'macros(sim model) {len(sim)} missing {len(missing)} {missing[:10]}')
    return 2 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
