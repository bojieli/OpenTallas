#!/usr/bin/env python3
"""Link the actual combined runtime only after all generated hierarchy archives exist.

Additive entrypoint: pinned original and source-default linker remain unchanged.
"""
import argparse
from pathlib import Path
import re
import shlex
import qwen_rom_combined_link_source_defaults as predecessor

EXPECTED = (
    'Vot_hdc_fmul/libot_hdc_fmul.a',
    'Vot_hdc_vstream_lane_a/libot_hdc_vstream_lane_a.a',
    'Vot_hdc_qadd/libot_hdc_qadd.a',
)


def require_hierarchy_archives(die_build):
    root = Path(die_build)
    makefile = root/'Vdie_hier.mk'
    text = makefile.read_text().replace('\\\n', ' ')
    matches = re.findall(r'^VM_HIER_LIBS\s*:=\s*(.*)$', text, re.MULTILINE)
    predecessor.require(len(matches) == 1, 'missing or ambiguous generated VM_HIER_LIBS')
    names = shlex.split(matches[0])
    predecessor.require(len(names) == len(EXPECTED) and set(names) == set(EXPECTED),
                        'generated hierarchy differs from selected three-library source')
    archives = [root/'Vdie__ALL.a', *(root/name for name in names)]
    for archive in archives:
        predecessor.require(archive.is_file(), 'required generated archive missing: '+str(archive))
        with archive.open('rb') as stream:
            predecessor.require(stream.read(8) == b'!<arch>\n', 'invalid archive header: '+str(archive))
    return archives


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--die-build', type=Path, required=True)
    args, _ = parser.parse_known_args()
    require_hierarchy_archives(args.die_build)
    return predecessor.main()


if __name__ == '__main__':
    raise SystemExit(main())
