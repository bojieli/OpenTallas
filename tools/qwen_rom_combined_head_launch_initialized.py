#!/usr/bin/env python3
"""Full36 input adapter requiring the actual initialized HEAD source to be linked."""
import hashlib
import json
from pathlib import Path
import qwen_rom_combined_head_launch as predecessor
import qwen_rom_combined_head_runtime_emit_initialized as composed

ROOT=Path(__file__).resolve().parents[1]
SOURCES=('tools/qwen_rom_combined_head_runtime_emit.py',
         'tools/qwen_rom_combined_runtime_emit_initialized.py',
         'tools/qwen_rom_combined_head_runtime_emit_initialized.py')


def validate_selection(book,root=ROOT):
    base=predecessor.predecessor
    binary=predecessor.BASE_VALIDATE(book,root)
    base.require(book.get('head_host_abi')==composed.HEAD_ABI,'compiled HEAD host required')
    base.require(book.get('initialization_abi')==composed.INITIALIZATION_ABI,'initial-eval HEAD host required')
    for path in SOURCES:
        base.require(book['source_sha256'].get(path)==base.sha(root/path),'initialized HEAD source pin required: '+path)
    path=Path(book['head_link_record'])
    base.require(base.sha(path)==book['head_link_record_sha256'],'initialized HEAD link record changed')
    link=json.loads(path.read_text())
    expected=hashlib.sha256(composed.emit(root).encode()).hexdigest()
    base.require(link.get('returncode')==0 and link.get('archives_stable') is True
                 and link.get('generated_runtime_sha256')==expected
                 and link.get('executable_sha256')==book['executable_sha256'],
                 'actual initialized HEAD runtime source/binary link required')
    return binary


def prepare_from_inputs(book_path,inputs_path,output,root=ROOT):
    """Same pinned cache API; no legacy-PASS fabrication or automatic execution."""
    original=predecessor.validate_head_runtime
    try:
        predecessor.validate_head_runtime=validate_selection
        return predecessor.prepare_from_inputs(book_path,inputs_path,output,root)
    finally:
        predecessor.validate_head_runtime=original


def main():
    """Prepare-only CLI; the existing sole runtime owner launches the command."""
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('selection','inputs','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    command,_=prepare_from_inputs(args.selection,args.inputs,args.output)
    print(json.dumps(dict(status='prepared',command=command)))
    return 0


if __name__=='__main__':raise SystemExit(main())
