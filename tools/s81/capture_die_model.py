#!/usr/bin/env python3
"""Capture the exact finalized model of one ordinary real-mode generator run.

The normal generator and every gate still execute. This records a source-bound
continuation artifact so subsequent emitters can be compared to the same model.
It grants no native, physical or scheduling qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import types


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--recipe', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--capture', type=Path, required=True)
    args = ap.parse_args()
    source = args.source.resolve()
    recipe = source / args.recipe
    sys.path.insert(0, str(source / 'tools'))
    os.chdir(source)
    import cloudpickle
    import dsrom_s81_fulldie as generator
    emit = generator.case_real
    source_sha = (source / 'SOURCE_SHA').read_text().strip()
    provenance = dict(source_commit=source_sha, source_root=str(source),
                      generator_sha256=digest(source / 'tools/dsrom_s81_fulldie.py'),
                      recipe_path=str(args.recipe), recipe_sha256=digest(recipe),
                      scope='Exact construction continuation; all qualification gates remain required')
    def capture(model, work):
        # Save before expensive emission too: a failed gate remains a failed gate,
        # but its unique generated model can be diagnosed without rebuilding it.
        args.capture.parent.mkdir(parents=True, exist_ok=True)
        state = {key: value for key, value in vars(generator).items()
                 if key.isupper() and not key.startswith('_NEAR_')
                 and not isinstance(value, types.ModuleType) and not callable(value)}
        temporary = args.capture.with_suffix('.temporary')
        with temporary.open('wb') as stream:
            cloudpickle.dump(dict(model=model, state=state, provenance=provenance), stream, protocol=5)
        temporary.replace(args.capture)
        metadata = dict(provenance, capture_sha256=digest(args.capture),
                        instances=len(model['insts']), buses=len(model['buses']))
        args.capture.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')
        print('OT_FINAL_MODEL_CAPTURE ' + json.dumps(metadata), flush=True)
        return emit(model, work)
    generator.case_real = capture
    return generator.main(['real', *shlex.split(recipe.read_text()), '--cfifo-colck', '--work', str(args.work)])


if __name__ == '__main__':
    raise SystemExit(main())
