#!/usr/bin/env python3
"""mtp-lead 2026-10-09: a die view's abstract LEF against the routed netlist's top ports, bit for bit.

    port_check.py LEF PORTS_TXT   (PORTS_TXT = the `input|output|inout` lines of the routed 6_final.v)
Prints JSON: macro, size, per-port widths, lef_pin_bits, netlist_bits, missing / extra pin bits, verdict.
"""
import json
import re
import sys

lef, ports = sys.argv[1], sys.argv[2]
txt = open(lef).read()
macro = re.search(r'^MACRO\s+(\S+)', txt, re.M).group(1)
size = [float(x) for x in re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', txt).groups()]
pins = set()
for m in re.finditer(r'^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1', txt, re.M | re.S):
    if re.search(r'USE\s+(POWER|GROUND)', m.group(2)):
        continue
    pins.add(m.group(1).replace('\\', ''))
bits, widths = set(), {}
for line in open(ports):
    m = re.match(r'\s*(input|output|inout)\s*(?:\[(\d+):(\d+)\])?\s*(\S+?)\s*;', line)
    if not m:
        continue
    d, hi, lo, name = m.groups()
    if hi is None:
        bits.add(name)
        widths[name] = (d, 1)
    else:
        hi, lo = int(hi), int(lo)
        for i in range(min(hi, lo), max(hi, lo) + 1):
            bits.add(f'{name}[{i}]')
        widths[name] = (d, abs(hi - lo) + 1)
missing, extra = sorted(bits - pins), sorted(pins - bits)
print(json.dumps(dict(macro=macro, size_um=size, ports={k: dict(dir=v[0], bits=v[1]) for k, v in sorted(widths.items())},
                      lef_pin_bits=len(pins), netlist_bits=len(bits), missing=missing[:20], n_missing=len(missing),
                      extra=extra[:20], n_extra=len(extra), verdict='MATCH' if not missing and not extra else 'MISMATCH'),
                 indent=1))
