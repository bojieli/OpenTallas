#!/usr/bin/env python3
"""KV-PARAMS2 10-19: paired-initial-state reset base for the frozen joint preludes (ktree/lane8, kv-native-joint-proof-1019).

Root cause of the 213 u_cc mismatches (2c2bd3c92): joint_base.ys left the gold (RTL) and gate (routed netlist) initial
states INDEPENDENT.  Both sides hold the same unreset 7-register datapath (kp_r -> ca -> s1 -> cb -> cd -> s2 -> cc), so
two independent power-up words disagree until the pipe flushed (7 edges > 6 reset edges); RTL-vs-itself fails the same
way (selftest).  The chip has ONE power-up state -- the routed netlist's -- and the RTL admits it on the same registers
(correspondence = routed flop names; every gate flop is paired, gate_only=0, replicas=0).  So: each paired register is
equal at step 1 (gold.S__x == gate.S__x); every gold-only register (incl. the 95/96 metadata bits) stays FREE; all
original comparisons + the metadata observations are miter outputs; same six reset-low target edges, other inputs
arbitrary; steps 7..10 checked (>= the 3 steps equiv_induct assumes).  Nothing removed, no reset extension, no exemption.
usage: make_paired_base.py joint_prelude.ys out.ys cex.json [gate.v mutated-gate.v FLOP NEWNET]
"""
import re, sys
from pathlib import Path

src, out, cex = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
pre = src.read_text()
gold = pre.split('cd gold\n', 1)[1].split('\ncd\n', 1)[0]
names = [m for m in re.findall(r'^add -wire (S__\S+) 1$', gold, re.M) if not m.startswith('S__proof_meta_')]
assert len(names) == len(set(names)) and names
head = pre.split('async2sync\n', 1)[0]
assert head.rstrip().endswith('rename -hide w:* @keep %d')
if len(sys.argv) > 4:   # native mutant control: rewire one routed flop's D in a COPY of gate.v
    gv, mv, flop, net = Path(sys.argv[4]), Path(sys.argv[5]), sys.argv[6], sys.argv[7]
    t = gv.read_text()
    i = t.index(' ' + flop + ' ')
    j = t.index('.D(', i)
    k = t.index(')', j)
    t = t[:j] + '.D(' + net + ' ' + t[k:]
    mv.write_text(t)
    head = head.replace('read_verilog gate.v\n', f'read_verilog {mv.name}\n', 1)
reset = ' '.join(f'-set-at {i} in_rst_n 0' for i in range(1, 7))
pair = ' '.join(f'-set-at 1 gold.{n} gate.{n}' for n in names)
body = (head + 'async2sync\nexpose gold/w:S__* gate/w:S__*\nmiter -equiv -flatten -make_assert gold gate miter\n'
        'hierarchy -top miter\nopt_clean\n'
        f'sat -seq 10 -prove-asserts -prove-skip 6 -set-def-inputs {reset} {pair} '
        f'-show-inputs -show-outputs -dump_json {cex} -verify\n')
out.write_text(body)
print(f'{out}: {len(names)} paired initial-state equalities, 6 reset-low edges, checked steps 7..10')
