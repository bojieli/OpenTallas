#!/usr/bin/env python3
"""Port-identical stub of ot_dsrom_window_source_ctl for a cheap IO-placement check (el1011-ds-misc 2026-10-11):
the real header (parameters + ports), every output driven by one flop, so floorplan + place_pins see the real
13.5k-pin boundary at a few seconds of synthesis.  usage: pincheck_m3.py <out.sv>"""
import re, sys
src = open('rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_dsrom_window_source_ctl.sv').read()
i = src.index('module ot_dsrom_window_source_ctl #(')
hdr = src[i:src.index(');', src.index(') (', i)) + 2]
outs = []
for m in re.finditer(r'output\s+wire\s*(\[[^\]]*\])?\s*([^;\n]*)', hdr):
    for n in m.group(2).split(','):
        n = n.strip().rstrip(',')
        if re.fullmatch(r'[A-Za-z_]\w*', n): outs.append(n)
body = ['    reg q;', '    always @(posedge clk) q <= prime_v ^ blk_v ^ start_v;']
body += ['    assign %s = {$bits(%s){q}};' % (o, o) for o in outs]
open(sys.argv[1], 'w').write('`timescale 1ns/1ps\n' + hdr + '\n' + '\n'.join(body) + '\nendmodule\n')
print(len(outs), 'outputs')
