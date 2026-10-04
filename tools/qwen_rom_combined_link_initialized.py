#!/usr/bin/env python3
"""Explicit initialized host-only link; keeps all actual archive/source guards."""
from pathlib import Path
import json
import qwen_rom_combined_link_hierarchy as hierarchy
import qwen_rom_combined_runtime_emit_initialized as initialized


def main():
    emitter = hierarchy.predecessor.emitter
    original = emitter.emit
    try:
        emitter.emit = initialized.emit
        rc = hierarchy.main()
    finally:
        emitter.emit = original
    # Output provenance is additive; the predecessor's link.json is untouched.
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--out', type=Path, required=True)
    args, _ = parser.parse_known_args()
    producer = Path(initialized.__file__)
    record = {'initialization_abi': initialized.INITIALIZATION_ABI,
              'source': str(producer), 'source_sha256': hierarchy.predecessor.sha(producer),
              'link_record_sha256': hierarchy.predecessor.sha(args.out/'link.json'),
              'returncode': rc, 'scope': 'All-model initial eval before first load/preload; no RTL or arithmetic change'}
    with (args.out/'initialization.json').open('x') as output:
        json.dump(record, output, indent=2); output.write('\n')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
