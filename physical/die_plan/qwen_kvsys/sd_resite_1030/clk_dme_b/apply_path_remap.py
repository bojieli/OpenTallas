#!/usr/bin/env python3
"""Apply the sd47b START path remap to a KV CA bind file (bind_ca_wc.json or nativeB_full.json).

The CA bind keys START stages by clock-tree path (base36 h-paths). Option (b) rebuilds the sys_SW/sys_SE
subtrees with region DME, so the SD subtree paths change; each old path is replaced by the sd47b path of
the SAME node cell. K/PAD values are untouched. Usage: apply_path_remap.py path_remap.json IN OUT
"""
import json, re, sys

remap, src, dst = sys.argv[1:4]
m = json.load(open(remap))["map"]
text = open(src).read()
total = 0
for node, (old, new) in sorted(m.items(), key=lambda kv: -len(kv[1][0])):
    text, n = re.subn(r"(?<![0-9a-z])" + re.escape(old) + r"(?![0-9a-z])", new, text)
    total += n
open(dst, "w").write(text)
print(f"{len(m)} paths, {total} replacements -> {dst}")
