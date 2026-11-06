#!/usr/bin/env python3
"""Stage declared selected fixed-port hard views before shared kit assembly."""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from kit_assembly import dedupe_sources


def stage_resolved(rtl_dir, masters, macros, base):
    """Copy actual view BBs once; preserve every native/soft source and the alias guard."""
    import gen_phys as G
    root, base = Path(rtl_dir).resolve(), Path(base).resolve()
    manifest_path = root / 'kit_rtl.json'
    manifest = json.loads(manifest_path.read_text())
    files = [Path(p).resolve() for p in manifest['files']]
    views = {}
    for _, master, lef, *_ in macros:
        if master not in masters:
            continue
        actual_lef = Path(G._CR.resolve(lef, base)).resolve()
        bb = actual_lef.parent / (master + '_bb.v')
        if not bb.is_file():
            raise ValueError(f'{master}: selected hard view has no fixed-port BB: {bb}')
        if re.search(r'^\s*`include\b', bb.read_text(), re.M):
            raise ValueError(f'{master}: fixed-port BB needs a self-contained view before relocation: {bb}')
        if master in views and views[master].read_bytes() != bb.read_bytes():
            raise ValueError(f'{master}: selected instances resolve to different fixed-port views')
        views[master] = bb
    if set(views) != set(masters):
        raise ValueError(f'selected children lack declared physical hard views: {sorted(set(masters)-set(views))}')
    staged = []
    for master, source in sorted(views.items()):
        destination = root / source.name
        data = source.read_bytes()
        for old in files + ([destination] if destination.exists() else []):
            if old.name == destination.name and old.read_bytes() != data:
                raise ValueError(f'{master}: conflicting fixed-port BB basename: {old} vs {source}')
        if not destination.exists():
            shutil.copyfile(source, destination)
        # The binder may already list this view outside the kit directory. The
        # assembly helper deliberately inspects staged top-level sources.
        files = [destination if p.name == destination.name else p for p in files]
        if destination not in files:
            files.append(destination)
        if master in manifest.get('hard_macros', {}):
            manifest['hard_macros'][master]['bb'] = str(destination)
        staged.append(dict(master=master, source=str(source), staged=str(destination)))
    files = dedupe_sources(files, root / 'source_alias')
    manifest['files'] = [str(p) for p in files]
    manifest['staged_hard_views'] = staged
    filelist = root / 'kit_rtl.f'
    options = [line for line in filelist.read_text().splitlines() if line.lstrip().startswith(('+', '-'))]
    filelist.write_text('\n'.join(options + [str(p) for p in files]) + '\n')
    manifest_path.write_text(json.dumps(manifest, indent=1) + '\n')
    return staged


def stage_selected(plan, type_name, rtl_dir, contracts):
    import schema as S
    import gen_phys as G
    plan = Path(plan).resolve()
    physical = S.Plan(json.loads(plan.read_text()), str(plan))
    selected = {c['master'] for c in contracts['children']}
    return stage_resolved(rtl_dir, selected, G.type_macros(physical, type_name), plan.parent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--type', required=True)
    parser.add_argument('--rtl-dir', required=True)
    parser.add_argument('--contracts', required=True)
    args = parser.parse_args()
    print(json.dumps(stage_selected(args.plan, args.type, args.rtl_dir,
                                   json.loads(Path(args.contracts).read_text()))))


if __name__ == '__main__':
    main()
