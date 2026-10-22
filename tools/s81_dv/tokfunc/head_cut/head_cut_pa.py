#!/usr/bin/env python3
"""RTLGAP2-HEADTB: golden.json (head_die_images.py) -> tb_s81hd_diecut plusargs (local / peers / token)."""
import json
import sys

g = json.load(open(sys.argv[1]))
a = [f"+LROW={g['local']['row']}", f"+LBITS={g['local']['bits']}", f"+TROW={g['token']['row']}", f"+TBITS={g['token']['bits']}"]
for i, q in enumerate(g["peers"], 1):
    a += [f"+P{i}ROW={q['row']}", f"+P{i}BITS={q['bits']}"]
print(" ".join(a))
