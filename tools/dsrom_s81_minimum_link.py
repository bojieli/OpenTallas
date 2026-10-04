#!/usr/bin/env python3
"""Link the minimum native pair host using completed archives only."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pq', type=Path, required=True)
    parser.add_argument('--pb', type=Path, required=True)
    parser.add_argument('--verilator-include', type=Path, required=True)
    parser.add_argument('--rom-client-dir', type=Path, required=True)
    parser.add_argument('--include-dir', type=Path, action='append', default=[])
    parser.add_argument('--model-archive', type=Path, action='append', default=[],
                        help='completed minimum model archive; exported from host')
    parser.add_argument('--source', type=Path, action='append', default=[],
                        help='actual source factory/provider translation unit')
    parser.add_argument('--link-library', action='append', default=[],
                        help='required native host library, e.g. crypto for pinned target-entry SHA256')
    parser.add_argument('--linked-source', action='store_true',
                        help='link selected source factory/prefix/embedding directly; select caller "-"')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cxx', default='g++')
    args = parser.parse_args()
    support = Path(__file__).resolve().parent / 'runtime' / 'dsrom'
    required = [args.pq / 'Vpq.h', args.pb / 'Vpb.h',
                args.pq / 'libVpq.a', args.pb / 'libVpb.a',
                args.pq / 'libverilated.a',
                args.verilator_include / 'verilated.h',
                args.rom_client_dir / 'dsrom_s81_rom_client.hpp',
                *args.model_archive, *args.source]
    for path in required:
        if not path.is_file():
            parser.error(f'completed native input missing: {path}')
    args.output.mkdir(parents=True, exist_ok=False)
    includes = [support, args.pq, args.pb, args.verilator_include,
                args.verilator_include / 'vltstd', args.rom_client_dir,
                *args.include_dir]
    sources = list(args.source)
    if args.linked_source:
        sources += [support / 's81_minimum_source.cpp',
                    support / 's81_minimum_source_factory.cpp',
                    support / 's81_minimum_prefix.cpp',
                    support / 's81_minimum_embedding.cpp']
    models = []
    if args.model_archive:
        models = ['-Wl,--whole-archive', *map(str, args.model_archive),
                  '-Wl,--no-whole-archive']
    obj = args.output / 's81_minimum_element.o'
    commands = [
        [args.cxx, '-std=c++17', '-O2', '-pthread',
         *[f'-I{p}' for p in includes], '-c',
         str(support / 's81_minimum_element.cpp'), '-o', str(obj)],
        [args.cxx, '-std=c++17', '-O2', '-pthread', '-rdynamic', str(obj),
         *[f'-I{p}' for p in includes], *map(str, sources),
         str(args.pq / 'libVpq.a'), str(args.pb / 'libVpb.a'),
         *models,
         str(args.pq / 'libverilated.a'), '-ldl',
         *[f'-l{name}' for name in args.link_library],
         '-o', str(args.output / 'minimum_element')],
    ]
    with (args.output / 'link.log').open('x') as log:
        for command in commands:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    print(args.output / 'minimum_element')


if __name__ == '__main__':
    main()
