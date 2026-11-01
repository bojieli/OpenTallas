#!/usr/bin/env python3
"""Stage real QC code masks beside the KV vehicle's original calendar ROM.

The optional direct include loads only actual QC code-ROM macro VIAMAPs. It
keeps the tile's ROM_TILE/strap assertion while avoiding global OT_ROM_DIR,
which would also require the still-uncompiled QC programme ROMs. Other macro
initialization and the KV calendar are unchanged. This is image integration,
not a token or programme qualification.
"""
import argparse
import errno
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
import qc_vehicle as Q


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def link_images(output, entries):
    output.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, source, expected in entries:
        if Path(name).name != name or not name.endswith('.viamap.hex'):
            raise ValueError(f'invalid image basename: {name}')
        source = source.resolve(strict=True)
        target = output / name
        if name in records:
            if sha(source) != sha(target):
                raise ValueError(f'different ROM payloads collide at {name}')
            records[name]['identical_sources'].append(str(source))
            continue
        try:
            os.link(source, target)
        except OSError as error:
            if error.errno != errno.EXDEV:
                raise
            shutil.copyfile(source, target)
        records[name] = dict(source=str(source), sha256=expected,
                             bytes=source.stat().st_size, identical_sources=[])
    return records


def profile(closure):
    wanted = {'qfd_tile_nk_rp2_romleaf_rr', 'qfd_tile_nl_rp2_romleaf_rr',
              'qfd_tile_nk_rp2_45', 'qfd_tile_nl_rp2_45', 'ot_qwen_rom_tile_nk',
              'ot_qwen_rom_tile_w12', 'ot_qwen_rom_tile_logic_w12', 'ot_qwen_tile_romleaf'}
    found = {}
    for name in (closure / 'files.f').read_text().splitlines():
        path = closure / name
        text = path.read_text()
        for module in re.findall(r'^\s*module\s+(\w+)', text, re.M):
            if module in wanted:
                if module in found:
                    raise ValueError(f'ambiguous selected ROM module: {module}')
                found[module] = (path, text)
    if set(found) != wanted:
        raise ValueError(f'unsupported ROM closure: missing {sorted(wanted - set(found))}')
    for name in ('qfd_tile_nk_rp2_romleaf_rr', 'qfd_tile_nl_rp2_romleaf_rr'):
        if '.RPH(3)' not in re.sub(r'\s+', '', found[name][1]):
            raise ValueError(f'{name}: direct image loader requires selected RPH3 source')
    text = found['ot_qwen_rom_tile_logic_w12'][1]
    for part in ('begin : g_rom_pipe', 'begin : g_rph', 'begin : g_rb',
                 'begin : g_single', 'begin : g_col', 'u_leaf'):
        if part not in text:
            raise ValueError(f'direct ROM hierarchy changed: {part}')
    return {name: dict(path=str(path), sha256=sha(path)) for name, (path, _) in found.items()}


def direct_include(bound, top, closure, rom_top, output, masks):
    evidence = profile(closure)
    names = json.loads((bound / 'bind_names.json').read_text())
    lines = Q.rom_lines(bound / 'rtl', top, names, rom_top)
    parents = []
    for line in lines:
        match = re.fullmatch(r'defparam (\S+)\.ROM_TILE = (\d+);', line)
        if not match:
            raise ValueError(f'unexpected source ROM identity: {line}')
        parents.append((match[1], int(match[2])))
    if len(parents) != 768 or {identity for _, identity in parents} != set(range(768)):
        raise ValueError('direct loader needs exactly the 768 bound source identities')
    sv = ['// Exact source tile IDs; original tile strap assertions stay enabled.', *lines,
          '// Only ROMleaf simulation labels are disabled: these actual macro VIAMAPs initialize the arrays directly.']
    count = 0
    for parent, identity in parents:
        for bank in range(5):
            for column in range(2):
                name = f'qtile_t{identity}_b{bank}_c{column}.viamap.hex'
                path = (masks / name).resolve(strict=True)
                leaf = (f'{parent}.u_g.u_tile.u_tile.u_logic.g_rom_pipe.g_rph.'
                        f'g_rb[{bank}].g_single.g_col[{column}].u_leaf')
                sv += [f'defparam {leaf}.ROM_TILE = -1;',
                       f'defparam {leaf}.u_rom.VIAMAP = {json.dumps(str(path))};']
                count += 1
    output.write_text('\n'.join(sv) + '\n')
    return dict(tiles=len(parents), macros=count, selected_source=evidence,
                global_ot_rom_dir=False, tile_strap_assertions=True,
                scope='Actual QC code macro initialization only; programme and token unqualified.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-rank', type=Path, required=True, help='rankN directory containing manifest.json and masks/')
    parser.add_argument('--kv-run', type=Path, required=True, help='original KV runtime directory containing runtime_rom.json/physical')
    parser.add_argument('--kv-instance', default='kv_dcal', help='compiled KV calendar INSTANCE (current selected source: kv_dcal)')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--bound', type=Path)
    parser.add_argument('--top', type=Path)
    parser.add_argument('--closure', type=Path)
    parser.add_argument('--rom-top', default='tb_kvslice.u_qc')
    args = parser.parse_args()
    rank = json.loads((args.code_rank / 'manifest.json').read_text())
    kv = json.loads((args.kv_run / 'runtime_rom.json').read_text())
    calendar = (args.kv_run / kv['runtime_path']).resolve(strict=True)
    if sha(calendar) != kv['sha256']:
        raise ValueError('original KV runtime calendar payload changed')
    entries = [(args.kv_instance + '.viamap.hex', calendar, kv['sha256'])]
    for pair in rank['pairs']:
        for column in pair['columns']:
            entries.append((column['file'], args.code_rank / 'masks' / column['file'], column['sha256']))
    if len(entries) != 7681:
        raise ValueError(f'expected one actual KV calendar plus 7680 QC macros, got {len(entries)}')
    records = link_images(args.out, entries)
    direct = None
    if any((args.bound, args.top, args.closure)):
        if not all((args.bound, args.top, args.closure)):
            parser.error('--bound, --top and --closure are required together')
        direct = direct_include(args.bound, args.top, args.closure, args.rom_top,
                                args.out / 'rom_bind_direct.vh', args.out)
    report = dict(schema='opentallas.qc-kv-rom-image-union.v1', rank=rank['rank'],
                  checkpoint_revision=rank['checkpoint_revision'], images=records,
                  actual_kv_calendar=kv, partial_stages=rank.get('partial_stages'), direct=direct,
                  global_directory_complete=False,
                  global_missing='QC programme/calendar/table ROMs must be supplied before using global OT_ROM_DIR.',
                  scope='Actual code/KV mask staging; no programme or token verdict.')
    (args.out / 'union.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(dict(images=len(records), rank=rank['rank'], direct=direct), sort_keys=True))


if __name__ == '__main__':
    main()
