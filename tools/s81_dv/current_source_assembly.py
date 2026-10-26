#!/usr/bin/env python3
"""Prepare the current repository S81 source assembly, without frozen fleet paths."""
import argparse
import json
import hashlib
from pathlib import Path
import shutil
import adopt_eng_split

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'physical/die_plan/s81/bind/asbuilt_b178_coll.json'
BOOT = Path('physical/die_plan/s81/bind/source_modules/dsdv_eng_rr_boot_source.sv')
SPLIT = Path('rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr_split.sv')
GENERATED = Path('physical/die_plan/s81/bind/generated/dsdv_eng_rr.sv')


def paths(manifest):
    result = []
    for field in ('files', 'prefer', 'netlist', 'hard_params', 'rtl_roots'):
        for name in manifest.get(field, []):
            p = Path(name)
            if p.is_absolute() or '..' in p.parts:
                raise ValueError('source path must stay repository-relative: ' + name)
            if not (ROOT / p).exists():
                raise ValueError('required current source absent: ' + name)
            result.append(p)
    for field in ('map_file',):
        # bind.py --asbuilt resolves a relative map_file against the manifest directory, not the repository root
        p = Path(manifest[field])
        if p.is_absolute() or '..' in p.parts or not (MANIFEST.parent / p).is_file():
            raise ValueError('invalid current ' + field + ': ' + str(p))
        result.append(MANIFEST.parent.relative_to(ROOT) / p)
    if (MANIFEST.parent / manifest['base']).resolve() != ROOT:
        raise ValueError('manifest base does not resolve to this repository')
    if manifest.get('rtl_roots'):
        raise ValueError('source assembly requires an explicit file set, not a mutable search root')
    for name in ('internal_primitive_constants', 'glue_source_names', 'pack_by_sink', 'type_canon'):
        if manifest.get(name) is not True:
            raise ValueError('required source assembly mechanism missing: ' + name)
    profile = manifest.get('core_profile') or {}
    if profile.get('kind') != 'S81_CTLA_TIMED_RESET_NATIVE_LOAD_STAGE':
        raise ValueError('current source assembly requires qualified timed hcore profile')
    qpath = Path(profile['component_qualification'])
    if qpath.is_absolute() or '..' in qpath.parts:
        raise ValueError('qualification must be repository-relative')
    q = json.loads((ROOT / qpath).read_text())
    if q.get('miter') != 'PASS' or q.get('mutant') != 'CAUGHT' or q.get('reset_input_timed') is not True:
        raise ValueError('current timed hcore component is not qualified')
    for rel, expected in q['source_sha256'].items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != expected:
            raise ValueError('current hcore differs from qualified source: ' + rel)
    if not {'OT_S81C_HCORE_CTLA', 'OT_S81C_HCORE_RST_TIMED'} <= set(manifest['defines']):
        raise ValueError('qualified timed source flags are missing')
    if {'OT_S81C_HCORE_RSTE', 'OT_S81C_HCORE_WPRE'} & set(manifest['defines']):
        raise ValueError('legacy hcore profile must not be selected')
    result.append(qpath)
    return list(dict.fromkeys(result + [BOOT, SPLIT, GENERATED, MANIFEST.relative_to(ROOT), Path('physical/die_plan/s81/die_plan.json')]))


PLAN = Path('physical/die_plan/s81/die_plan.json')


def plan_inputs():
    """[(repo-relative path, bytes)] of every repository file the die plan names."""
    import subprocess

    def strings(o):
        if isinstance(o, dict):
            for v in o.values():
                yield from strings(v)
        elif isinstance(o, list):
            for v in o:
                yield from strings(v)
        elif isinstance(o, str):
            yield o
    tracked = None
    out = {}
    for s in set(strings(json.loads((ROOT / PLAN).read_text()))):
        if '/' not in s or len(s) > 400 or s.startswith('/') or '..' in Path(s).parts:
            continue
        for rel in (Path(s), PLAN.parent / s):
            if (ROOT / rel).is_file():
                out[rel] = (ROOT / rel).read_bytes()
                break
            if tracked is None:
                r = subprocess.run(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'HEAD'],
                                   capture_output=True, text=True)
                tracked = set(r.stdout.split()) if r.returncode == 0 else set()
            if str(rel) in tracked:
                out[rel] = subprocess.run(['git', '-C', str(ROOT), 'show', 'HEAD:' + str(rel)],
                                          capture_output=True, check=True).stdout
                break
    return sorted(out.items())


def prepare(check=False, stage=None):
    manifest = json.loads(MANIFEST.read_text())
    emitted = adopt_eng_split.emit((ROOT / BOOT).read_text(), (ROOT / SPLIT).read_text())
    generated = ROOT / GENERATED
    if check:
        if generated.read_text() != emitted:
            raise ValueError('split Eng boot master is stale; run current_source_assembly.py')
    else:
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(emitted)
    source_paths = paths(manifest)
    if stage:
        stage = Path(stage).resolve()
        for p in source_paths:
            dest = stage / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / p, dest)
        # The bind step also reads plan inputs (hard-core pin tables, reference LEF views, macro views): stage every
        # repository file the die plan names (repo-relative or plan-relative), from the checkout or, when a sparse
        # checkout lacks it, from git HEAD, so the cohort is closed for strict bind and not only for ELAB.
        for rel, data in plan_inputs():
            dest = stage / rel
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
        # Use the complete matching tool package, not a different host checkout.
        shutil.copytree(ROOT / 'tools/die_plan', stage / 'tools/die_plan', dirs_exist_ok=True)
        (stage / 'tools/s81_dv').mkdir(parents=True, exist_ok=True)
        for name in ('adopt_eng_split.py', 'current_source_assembly.py'):
            shutil.copy2(ROOT / 'tools/s81_dv' / name, stage / 'tools/s81_dv' / name)
    return dict(source_assembly='CURRENT_REPOSITORY', files=len(source_paths), generated_eng_boot_decoder=True,
                source_defines=manifest['defines'], stage=str(stage) if stage else None,
                scope='SOURCE_PREPARATION_ONLY; strict binding and actual RTL token still required')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--stage', help='copy this exact selected source/tool closure to a small fleet run root')
    a = ap.parse_args()
    print(json.dumps(prepare(a.check, a.stage)))


if __name__ == '__main__':
    main()
