#!/usr/bin/env python3
"""TOK-QW xdie_bound: source closure for a bound-top carve with the BINDER's own resolver (tools/die_plan/bind_smoke.py
Sources = bind_elab module_index / pick / closure: <bound>/rtl first, then the as-built recipe's prefer files, then the
macro models, then the rtl_roots index of REV).  Stages the files under WORK/src/<die>/ and writes WORK/<die>_files.f,
WORK/<die>_inc.f, WORK/<die>_defines.f and WORK/<die>_closure.json.

    stage_closure.py --die qc --bound BOUND --asbuilt RECIPE.json --rev REV --carve DIR/<name>.json --work WORK
"""
import argparse, json, shutil, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'tools/die_plan'))
import bind_smoke as B  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--die', required=True)
ap.add_argument('--bound', required=True, type=Path)
ap.add_argument('--asbuilt', required=True, type=Path)
ap.add_argument('--rev', required=True)
ap.add_argument('--repo', type=Path, default=Path.home() / 'OpenTallas')
ap.add_argument('--carve', required=True, type=Path)
ap.add_argument('--work', required=True, type=Path)
ap.add_argument('--extra-mod', action='append', default=[])
a = ap.parse_args()
c = json.loads(a.carve.read_text())
S = B.Sources(a.bound.resolve(), a.asbuilt.resolve(), a.rev, a.repo)
mods = sorted(set(c['seeds'].values()) | set(a.extra_mod))
files, amb, missing = S.closure(mods)
incs, incdirs = S.includes(files)
W = a.work / 'src' / a.die
if W.exists():
    shutil.rmtree(W)
def rel(f):
    f = Path(f)
    if f.is_relative_to(S.bound):
        return Path('src') / a.die / 'bound' / f.relative_to(S.bound)
    return Path('src') / a.die / f.relative_to(S.base)
for f in list(files) + list(incs):
    d = a.work / rel(f)
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(f, d)
fl = [str(rel(f)) for f in files]
il = sorted({str(rel(Path(d) / 'x').parent) for d in incdirs})
(a.work / f'{a.die}_files.f').write_text('\n'.join(fl) + '\n')
(a.work / f'{a.die}_inc.f').write_text(''.join(d + '\n' for d in il))
(a.work / f'{a.die}_defines.f').write_text(''.join(f'+define+{d}\n' for d in S.defines))
(a.work / f'{a.die}_closure.json').write_text(json.dumps(dict(
    die=a.die, bound=str(a.bound), asbuilt=str(a.asbuilt), rev=a.rev, src_tree=str(S.base), modules=mods, files=fl,
    includes=[str(rel(i)) for i in incs], incdirs=il, defines=S.defines, missing=missing,
    ambiguous={k: [str(x) for x in v] for k, v in amb.items()}), indent=1) + '\n')
print(f'{a.die}: {len(fl)} files, {len(incs)} includes, missing {missing}, ambiguous {sorted(amb)}')
