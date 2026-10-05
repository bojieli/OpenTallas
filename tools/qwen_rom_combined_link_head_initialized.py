#!/usr/bin/env python3
"""Select HEAD + initial eval for a fresh owner-controlled host-only link."""
import argparse
import json
from pathlib import Path
import qwen_rom_combined_head_runtime_emit_initialized as composed


def main():
    import qwen_rom_combined_link_hierarchy as hierarchy
    emitter=hierarchy.predecessor.emitter
    original=emitter.emit
    try:
        emitter.emit=composed.emit
        rc=hierarchy.main()
    finally:
        emitter.emit=original
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--out',type=Path,required=True)
    args,_=parser.parse_known_args()
    modules=(composed,composed.head,composed.initialized)
    record=dict(head_host_abi=composed.HEAD_ABI,initialization_abi=composed.INITIALIZATION_ABI,
                source_sha256={str(Path(m.__file__).resolve()):hierarchy.predecessor.sha(m.__file__) for m in modules},
                link_record_sha256=hierarchy.predecessor.sha(args.out/'link.json'),returncode=rc,
                scope='Explicit initialized HEAD host only; existing RTL/archive models untouched')
    with (args.out/'head_initialization.json').open('x') as output:
        output.write(json.dumps(record,indent=2)+'\n')
    return rc


if __name__=='__main__':raise SystemExit(main())
