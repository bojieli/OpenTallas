#!/usr/bin/env python3
"""Prepare a fresh hierarchical argument file with the 5.050 substitution trigger.

No existing argument file is changed and no compiler/build process is launched.
Measured scope: results/rtl/s81_hierarchy_substitution_0310.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex

STUB = '// Empty type declarations: enable integer/default hierarchical replacement.\n'


def prepare(input_file: Path, output_file: Path, stub_file: Path) -> dict:
    input_file, output_file, stub_file = (p.resolve() for p in (input_file, output_file, stub_file))
    if len({input_file, output_file, stub_file}) != 3:
        raise ValueError('input, fresh output, and stub must be distinct paths')
    original = input_file.read_bytes()
    tokens = shlex.split(original.decode())
    existing = any(t == '--hierarchical-params-file' or t.startswith('--hierarchical-params-file=')
                   for t in tokens)
    if not any(t in ('--hierarchical-child', '--hierarchical-block') for t in tokens):
        raise ValueError('expected generated hierarchical child/final-top arguments')
    if not existing and any(t in ('-f', '-F') or t.startswith('@') for t in tokens):
        raise ValueError('nested arguments may contain genuine type files; inspect them first')
    if output_file.exists():
        raise FileExistsError(f'fresh output required: {output_file}')
    if existing:
        result = original
    else:
        if stub_file.exists():
            if stub_file.read_text() != STUB:
                raise ValueError('existing stub differs; preserve it and choose a fresh path')
        else:
            stub_file.parent.mkdir(parents=True, exist_ok=True)
            with stub_file.open('x') as f:
                f.write(STUB)
        result = original + ('\n--hierarchical-params-file ' + json.dumps(str(stub_file)) + '\n').encode()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open('xb') as f:
        f.write(result)
    return dict(input=str(input_file), output=str(output_file), stub=None if existing else str(stub_file),
                preserved_existing_type_option=existing, added_empty_type_option=not existing,
                input_sha256=hashlib.sha256(original).hexdigest(),
                output_sha256=hashlib.sha256(result).hexdigest(),
                launched_build=False, changed_input=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--stub', type=Path, required=True)
    a = p.parse_args()
    try:
        print(json.dumps(prepare(a.input, a.output, a.stub), indent=2))
    except (OSError, ValueError) as e:
        p.exit(1, str(e) + '\n')


if __name__ == '__main__':
    main()
