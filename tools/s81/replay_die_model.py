#!/usr/bin/env python3
"""Run an existing emitter from an exact source-bound finalized model.

Construction reuse only. Scripts keep their ordinary port, control, pin and view
checks. Any change in the die options, generator, source identity or recipe is
refused. The immutable source snapshot must remain at its captured location.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shlex
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    if isinstance(value, Path):
        return str(value)
    return value


def validate(source, capture, metadata):
    if str(source) != metadata['source_root']:
        raise ValueError('captured source root differs')
    if (source / 'SOURCE_SHA').read_text().strip() != metadata['source_commit']:
        raise ValueError('captured source commit differs')
    if digest(source / 'tools/dsrom_s81_fulldie.py') != metadata['generator_sha256']:
        raise ValueError('captured generator differs')
    if digest(source / metadata['recipe_path']) != metadata['recipe_sha256']:
        raise ValueError('captured recipe differs')
    if digest(capture) != metadata['capture_sha256']:
        raise ValueError('captured model digest differs')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--capture', type=Path, required=True)
    ap.add_argument('--script', type=Path, required=True)
    ap.add_argument('args', nargs=argparse.REMAINDER)
    args = ap.parse_args()
    source, capture = args.source.resolve(), args.capture.resolve()
    metadata = json.loads(capture.with_suffix('.json').read_text())
    validate(source, capture, metadata)
    script = (source / args.script).resolve()
    if not script.is_relative_to(source):
        raise ValueError('emitter must belong to the immutable source snapshot')
    sys.path.insert(0, str(source / 'tools'))
    os.chdir(source)
    import cloudpickle
    import dsrom_s81_fulldie as generator
    with capture.open('rb') as stream:
        saved = cloudpickle.load(stream)
    provenance = saved['provenance']
    for key, value in provenance.items():
        if metadata[key] != value:
            raise ValueError('model and metadata provenance differ: ' + key)
    expected = vars(generator.die_options(argparse.ArgumentParser()).parse_args(
        shlex.split((source / metadata['recipe_path']).read_text())))
    original_apply = generator.apply_options
    checked = [False]
    def apply(options):
        differences = {key: [canonical(value), canonical(getattr(options, key, None))]
                       for key, value in expected.items()
                       if canonical(getattr(options, key, None)) != canonical(value)}
        if differences:
            raise ValueError('captured die options differ: ' + json.dumps(differences, default=str))
        original_apply(options)
        vars(generator).update(saved['state'])
        checked[0] = True
    def build():
        if not checked[0]:
            raise ValueError('emitter must apply the captured die options before construction reuse')
        return saved['model']
    def finalize(model):
        if model is not saved['model']:
            raise ValueError('finalize requested on a different model')
        return model['pdir']
    generator.apply_options = apply
    generator.build = build
    generator.finalize_r8 = finalize
    rest = args.args[1:] if args.args[:1] == ['--'] else args.args
    sys.argv = [str(script), *rest]
    print('OT_FINAL_MODEL_REPLAY ' + json.dumps(dict(source_commit=metadata['source_commit'],
          capture_sha256=metadata['capture_sha256'], emitter=str(args.script),
          replay_tool_sha256=digest(__file__), scope='construction reuse; all emitter gates still required')), flush=True)
    if script == source / 'tools/dsrom_s81_fulldie.py':
        generator.main(rest)
    else:
        runpy.run_path(str(script), run_name='__main__')
    if not checked[0]:
        raise ValueError('emitter never validated the captured die options')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
