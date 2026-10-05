#!/usr/bin/env python3
"""Host-only link against Laplace's sole nearbaseline model and retained models."""
import argparse
import json
from pathlib import Path
import re
import shlex
import qwen_rom_combined_link_source_defaults as predecessor
import qwen_rom_combined_nearbaseline_access as access
import qwen_rom_combined_nearbaseline_runtime_emit as emitter


def require_selected_models(build, die_build):
    d = predecessor.resolved_parameters(build, 'die')
    predecessor.require(d.get('NEAR_HBM') == 1, 'mandatory compiled NEAR_HBM=1 required')
    files = list(Path(die_build).glob('Vdie*__verFiles.dat'))
    predecessor.require(len(files) == 1 and emitter.TOP in files[0].read_text(),
                        'actual compiled nearbaseline top required')
    text = (Path(die_build)/'Vdie_hier.mk').read_text().replace('\\\n', ' ')
    matches = re.findall(r'^VM_HIER_LIBS\s*:=\s*(.*)$', text, re.MULTILINE)
    predecessor.require(len(matches) == 1, 'actual generated hierarchy required')
    names = shlex.split(matches[0])
    predecessor.require(len(names) == len(set(names)), 'duplicate hierarchy archive')
    for name in ['Vdie__ALL.a', *names]:
        p = Path(name)
        predecessor.require(not p.is_absolute() and '..' not in p.parts and p.suffix == '.a',
                            'generated hierarchy path outside selected model')
        with (Path(die_build)/p).open('rb') as stream:
            predecessor.require(stream.read(8) == b'!<arch>\n', 'actual hierarchy archive missing/invalid')
    return d


def main():
    parser = argparse.ArgumentParser(add_help=False)
    for key in ('die-build', 'compiled-params', 'out'):
        parser.add_argument('--'+key, type=Path, required=True)
    args, _ = parser.parse_known_args()
    require_selected_models(json.loads(args.compiled_params.read_text()), args.die_build)
    old_emitter, old_access = predecessor.emitter, predecessor.access
    try:
        predecessor.emitter = emitter
        predecessor.access = access
        rc = predecessor.main()
    finally:
        predecessor.emitter = old_emitter
        predecessor.access = old_access
    record = dict(runtime_abi=emitter.ABI, top=emitter.TOP,
                  initialization_abi=emitter.initialized.INITIALIZATION_ABI,
                  returncode=rc, context_limit=8192, maximum_stages=1,
                  source_sha256={str(Path(m.__file__).resolve()): predecessor.sha(m.__file__)
                                 for m in (emitter, access, emitter.initialized)},
                  link_record_sha256=predecessor.sha(args.out/'link.json'),
                  scope='One actual decoder layer; token cost by composition; no full-array or physical qualification')
    with (args.out/'nearbaseline_runtime.json').open('x') as stream:
        stream.write(json.dumps(record, indent=2)+'\n')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
