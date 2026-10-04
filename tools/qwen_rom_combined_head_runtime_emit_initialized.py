#!/usr/bin/env python3
"""Explicit HEAD + common initial-eval composition; all predecessors unchanged."""
import argparse
from pathlib import Path
import qwen_rom_combined_head_runtime_emit as head
import qwen_rom_combined_runtime_emit_initialized as initialized

ROOT=Path(__file__).resolve().parents[1]
HEAD_ABI=head.HEAD_ABI
INITIALIZATION_ABI=initialized.INITIALIZATION_ABI


def emit(root=ROOT):
    return initialized.initialize_source(head.emit(root))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    text=emit()
    with args.out.open('x') as output:output.write(text)


if __name__=='__main__':main()
