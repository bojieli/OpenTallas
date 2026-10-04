#!/usr/bin/env python3
"""Explicit additive head launcher hooks; the existing three-layer path is unchanged.

Confucius can consume layers_from_stages() and validate_head_runtime() in the
full-36 cached-input hook. main retains the predecessor's frozen-PASS requirement;
it never fabricates a full-token baseline from E-only or a three-layer PASS.
"""
import json
from pathlib import Path
import qwen_rom_combined_launch as predecessor
import qwen_rom_combined_head_runtime_emit as head

ROOT=Path(__file__).resolve().parents[1]
BASE_VALIDATE=predecessor.validate_selection


def layers_from_stages(path):
    stages=[]
    for line in Path(path).read_text().splitlines():
        words=line.split()
        if not words or words[0].startswith('#'):continue
        predecessor.require(len(words)==6,'head stage ABI requires four actual rank paths and reset')
        name,*directories,reset=words
        predecessor.require(reset in ('0','1'),'invalid stage reset')
        predecessor.require(all(Path(p).is_dir() for p in directories),'missing released stage image directory')
        if name in ('E','head'):predecessor.require(reset=='0','E/head have no KV reset')
        stages.append(name)
    predecessor.require(stages==['E']+[f'L{l}' for l in range(36)]+['head'],
                        'full token requires E, L0..L35, head exactly once in order')
    return list(range(36))


def validate_head_runtime(book, root=ROOT):
    binary=BASE_VALIDATE(book,root)
    predecessor.require(book.get('head_host_abi')==head.HEAD_ABI,'compiled head host selection required')
    emitter='tools/qwen_rom_combined_head_runtime_emit.py'
    predecessor.require(book['source_sha256'].get(emitter)==predecessor.sha(root/emitter),'head emitter source pin required')
    path=Path(book['head_link_record'])
    predecessor.require(predecessor.sha(path)==book['head_link_record_sha256'],'head link record changed')
    link=json.loads(path.read_text())
    import hashlib
    expected=hashlib.sha256(head.emit(root).encode()).hexdigest()
    predecessor.require(link.get('returncode')==0 and link.get('archives_stable') is True
                        and link.get('generated_runtime_sha256')==expected
                        and link.get('executable_sha256')==book['executable_sha256'],
                        'actual linked head source/binary identity required')
    return binary


def main():
    old_layers,old_validate=predecessor.layers_from_stages,predecessor.validate_selection
    try:
        predecessor.layers_from_stages=layers_from_stages
        predecessor.validate_selection=validate_head_runtime
        return predecessor.main()
    finally:
        predecessor.layers_from_stages=old_layers
        predecessor.validate_selection=old_validate


if __name__=='__main__':raise SystemExit(main())
