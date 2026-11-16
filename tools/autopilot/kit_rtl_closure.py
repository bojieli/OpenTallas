#!/usr/bin/env python3
"""Package the producer's validated kit RTL input closure before a roam copy."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def package(directory, source):
    kd = Path(directory).absolute()
    actual_kd = kd.resolve()
    mf = kd / 'kit_rtl.json'
    meta = json.loads(mf.read_text()) if mf.is_file() else {}
    roots = [Path(source).resolve(), actual_kd]
    bind_root = Path(meta['bind_out']).resolve() if meta.get('bind_out') else None
    if bind_root:
        roots.append(bind_root)
    fl = kd / 'kit_rtl.f'
    files = [Path(s).resolve() for s in fl.read_text().splitlines() if s.strip()]
    for p in files:
        if not p.is_file() or not any(p.is_relative_to(r) for r in roots):
            raise ValueError(f'KIT_RTL_CLOSURE invalid source {p}; allowed roots {roots}')
    dest = kd / 'closure'
    origins = {}
    def stage(p):
        p = Path(p).resolve()
        if p.is_relative_to(actual_kd):
            target = kd / p.relative_to(actual_kd)
        else:
            target = dest / 'root' / str(p).lstrip('/')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)
        origins[str(target.relative_to(kd))] = dict(original=str(p), sha256=digest(target))
        return str(target)
    newfiles = [stage(p) for p in files]
    # Explicit physical/simulation view paths and the selected asbuilt metadata are inputs too.
    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k,v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str) and x.startswith('/') and Path(x).is_file():
            return stage(x)
        return x
    updated = walk(meta)
    bo = dest / 'bind'
    bo.mkdir(parents=True, exist_ok=True)
    for name in ('bind_report.json', 'bind_parent_id_straps.json'):
        p = bind_root / name if bind_root else None
        if p and p.is_file():
            shutil.copyfile(p, bo / name)
    updated['bind_out'] = str(bo)
    updated['files'] = newfiles
    updated['input_closure'] = dict(schema='opentallas.kit_rtl_closure.v1', roots=[str(r) for r in roots], producer_directory=str(kd), files=origins)
    # Originals are retained as history; mutations apply only to this newly emitted attempt.
    if mf.is_file():
        shutil.copyfile(mf, kd / 'kit_rtl.producer.json')
    fl.write_text('\n'.join(newfiles) + '\n')
    mf.write_text(json.dumps(updated, indent=1) + '\n')
    return dict(files=len(newfiles), closure_files=len(origins))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('directory')
    ap.add_argument('--source', required=True)
    a = ap.parse_args()
    print('KIT_RTL_CLOSURE ' + json.dumps(package(a.directory, a.source)))
