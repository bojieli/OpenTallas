#!/usr/bin/env python3
"""Explicit head-host link successor; no change to the live three-layer linker."""
import qwen_rom_combined_link_hierarchy as hierarchy
import qwen_rom_combined_head_runtime_emit as head


def main():
    # Existing hierarchy/default/source/archive guards and link flags remain.
    # Called only by the sole link owner after selecting full-token inputs.
    emitter=hierarchy.predecessor.emitter
    original=emitter.emit
    try:
        emitter.emit=head.emit
        return hierarchy.main()
    finally:
        emitter.emit=original


if __name__=='__main__':raise SystemExit(main())
