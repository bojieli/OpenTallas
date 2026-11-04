#!/usr/bin/env python3
"""Link per-slice XS programme images to explicit original-path selectors.

Input JSON: [{"original_xgt_path": "s_0S.u_xg", "program_dir": "..."}, ...].
The caller supplies the actual bind identity and programme correspondence.
"""
import argparse
import json
from pathlib import Path

SELECTORS = ('pq_calendar_action', 'pq_calendar_time', 'pq_phase0',
             'pq_stream0', 'pq_stream1', 'pq_stream2', 'pq_stream3')


def link(mapping, out, base_rom_dir=None):
    # Close the entire source set before creating any output directory.
    links = {}
    if base_rom_dir is not None:
        for source in Path(base_rom_dir).resolve(strict=True).glob("*.viamap.hex"):
            links[source.name] = str(source.resolve(strict=True))
    for entry in mapping:
        prefix = entry['original_xgt_path']
        if not prefix or any(c in prefix for c in '/\\"\n\r'):
            raise ValueError('need a safe original elaborated xgt_xo path')
        directory = Path(entry['program_dir']).resolve(strict=True)
        for selector in SELECTORS:
            source = directory / (selector + '.viamap.hex')
            if not source.is_file():
                raise ValueError(f'missing XS programme image: {source}')
            name = prefix + '.' + selector + '.viamap.hex'
            if name in links:
                raise ValueError(f'duplicate original identity: {prefix}')
            links[name] = str(source.resolve(strict=True))
    if not mapping:
        raise ValueError('no slice programmes supplied')
    out.mkdir(parents=True, exist_ok=False)
    for name, source in links.items():
        (out / name).symlink_to(source)
    result = dict(status='XS_ROM_DIRECTORY_LINKED_SOURCE_ASSETS_ONLY',
                  slices=len(mapping), images=len(links), links=links,
                  original_identity_and_programme_correspondence='caller supplied; not inferred',
                  production_bind_changed=False, mission_programmes_qualified=False,
                  full_token=False)
    (out / 'xs_rom_dir.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mapping', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--base-rom-dir', type=Path)
    a = p.parse_args()
    result = link(json.loads(a.mapping.read_text()), a.out, a.base_rom_dir)
    print(result['status'], result['slices'], result['images'])


if __name__ == '__main__':
    main()
