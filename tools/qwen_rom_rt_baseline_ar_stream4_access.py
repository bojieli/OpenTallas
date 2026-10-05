#!/usr/bin/env python3
"""Existing preload-only accessor, bound to the selected W12 tagged AR top.

Use only on the owner's actual generated headers. No model, clock, memory
response, payload conversion or archive substitution is provided here.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = 'ot_qwen_rom_rt_die_w12_stream4_tagged_ar'


def main():
    spec = importlib.util.spec_from_file_location(
        '_plain_ar_rm_access', ROOT / 'tools/qwen_rom_rt_rm_access.py')
    access = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(access)
    original_find = access.find

    def find(names, pattern, what):
        pattern = pattern.replace('ot_qwen_rom_rt_die_w12_rm__DOT__', TOP+'__DOT__')
        hits = original_find(names, pattern, what)
        # Never silently select one of two independent backing stores.
        if what == 'HBM mem' and len(hits) != 1:
            raise SystemExit('plain AR requires one actual tagged STREAM4 backing array')
        return hits

    access.find = find
    access.main()


if __name__ == '__main__':
    main()
