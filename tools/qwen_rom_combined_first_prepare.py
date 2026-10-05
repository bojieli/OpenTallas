#!/usr/bin/env python3
"""Prepare the FIRST full token through the owner's cached-input callable.

This caller does not link, launch, regenerate inputs or invent a PASS baseline.
Dewey owns actual execution after the in-flight three-layer job and explicit
future head link. The original head launcher main/PASS guard is not called.
"""
import argparse
import importlib
import json
from pathlib import Path
import sys


def prepare(selection, inputs, output, source_root, *, initialized_head=False):
    source_root = Path(source_root).resolve(strict=True)
    sys.path.insert(0, str(source_root/'tools'))
    module = 'qwen_rom_combined_head_launch_initialized' if initialized_head else 'qwen_rom_combined_head_launch'
    owner = importlib.import_module(module)
    if Path(owner.__file__).resolve() != source_root/'tools'/(module+'.py'):
        raise ValueError('head callable imported from a different selected source root')
    command, record = owner.prepare_from_inputs(selection, inputs, output, root=source_root)
    cache = json.loads(Path(inputs).read_text())
    checker = source_root/'tools/qwen_rom_combined_head_readback.py'
    if not checker.is_file():
        raise ValueError('existing full-token head readback checker missing')
    # Runtime owner writes terminal.json only after the real child terminates,
    # preserving record layers/frame/command and actual returncode/status.
    check_command = [sys.executable, str(checker), '--terminal', str(Path(output)/'terminal.json'),
                     '--oracle-root', cache['oracle']['root'],
                     '--oracle-sha256', cache['oracle']['sha256'],
                     '--run-dir', command[3], '--runtime-log', str(Path(output)/'runtime.log'),
                     '--output', str(Path(output)/'numerical.json')]
    result = dict(command=command, checker_command=check_command,
                  prepared_receipt=str(Path(output)/'launch.json'),
                  runtime_status='not_launched', fulltoken_rtl_pass=False,
                  runtime_owner='Dewey', source_root=str(source_root))
    with (Path(output)/'owner_commands.json').open('x') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('selection', 'inputs', 'output', 'source-root'):
        ap.add_argument('--'+name, type=Path, required=True)
    ap.add_argument('--initialized-head', action='store_true',
                    help='require the linked head host to initialize all models before preloads')
    a = ap.parse_args(argv)
    result = prepare(a.selection, a.inputs, a.output, a.source_root,
                     initialized_head=a.initialized_head)
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
