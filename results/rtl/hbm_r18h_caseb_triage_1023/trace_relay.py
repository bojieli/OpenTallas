#!/usr/bin/env python3
"""trace relay chains (rf/rh/l12p) backward from instance ports in a cut slice.v; prints stage masters per path."""
import re, sys, json
from collections import Counter
src = open(sys.argv[1]).read()
inst = {}
for m in re.finditer(r'^\s*(\w+)\s*(?:#\((?:[^()]|\([^()]*\))*\))?\s+(\w+)\s*\((.*?)\n\s*\);', src, re.S | re.M):
    master, name, body = m.groups()
    ports = dict(re.findall(r'\.(\w+)\((.*?)\)(?:,\s*$|\s*$)', body, re.M))
    inst[name] = (master, ports)
json.dump({k: v for k, v in inst.items()}, open(sys.argv[2], 'w'))
print(len(inst))
