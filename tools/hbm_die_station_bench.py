#!/usr/bin/env python3
"""Bench of the HBM die station views (CLAUDE HBM-ABSTRACTS stations): one Icarus run per master, one seed.

  tb    --gen DIR --master M --out DIR [--mutant]   write tb_<M>.sv: every forwarded clock at its own static phase
                                                    against ck (same period), random data on every input bit each
                                                    period of its domain, every output sampled mid-eye of its domain
                                                    (falling edge of its forwarded clock / of ck), logged
  check --gen DIR --master M --log FILE             every output bit must equal its mapped source bit (map.json) at
                                                    ONE constant latency per output domain for every sampled period
                                                    after the meso placement window; exit 1 on any mismatch
"""
import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

PER = 10.0          # ns, behavioural period (all clocks equal; phases static)
NCYC = 400
WARM = 80


def load(gen, m):
    d = Path(gen) / m
    mp = json.loads((d / 'map.json').read_text())
    ports = {}
    src = (d / f'{m}.sv').read_text()
    for dr, hi, nm in re.findall(r'(input|output|inout) wire \[(\d+):0\] (\w+)', src):
        ports[nm] = (dr, int(hi) + 1)
    return mp, ports


def bitsplit(s):
    p, i = re.match(r'(\w+)\[(\d+)\]', s).groups()
    return p, int(i)


def cmd_tb(a):
    mp, ports = load(a.gen, a.master)
    rnd = random.Random(1062026)
    clk_in = mp['clk_in']
    ins = mp['ins']               # input bit -> domain ('ck' or clock bit)
    outdom = defaultdict(list)    # output domain clock (bit or 'ck') -> [output bits]
    for o, v in mp['map'].items():
        outdom[v['dom']].append(o)
    L = ['`timescale 1ns/1ps', f'module tb_{a.master};']
    for p, (dr, w) in ports.items():
        L.append(f'  wire [{w - 1}:0] {p};')
    L.append(f'  {a.master} dut (' + ', '.join(f'.{p}({p})' for p in ports) + ');')
    has_ck = 'ck' in ports
    L.append('  reg ck_r = 0; reg rst_r = 0;')
    if has_ck:
        L.append('  assign ck[0] = ck_r;')
    if 'rst' in ports:
        L.append('  assign rst[0] = rst_r;')
    L.append(f'  always #{PER / 2} ck_r = ~ck_r;')
    L.append(f'  initial begin rst_r = 0; #({PER} * 6 + 0.3); rst_r = 1; end')
    phases = {}
    for k, c in enumerate(clk_in):
        p, i = bitsplit(c)
        ph = round((2.3 + 1.37 * k) % PER, 3)
        phases[c] = ph
        L.append(f'  reg fc_{p}_{i} = 0; assign {c} = fc_{p}_{i};')
        L.append(f'  initial begin #{ph}; forever begin fc_{p}_{i} = 1; #{PER / 2}; fc_{p}_{i} = 0; #{PER / 2}; end end')
    # input data domains
    dom_bits = defaultdict(list)
    for b, dmn in ins.items():
        dom_bits[dmn].append(b)
    L.append('  integer fd; initial fd = $fopen("trace.log", "w");')
    for j, (dmn, bits) in enumerate(sorted(dom_bits.items())):
        bits = sorted(bits, key=lambda s: (bitsplit(s)[0], bitsplit(s)[1]))
        w = len(bits)
        vn = f'iv{j}'
        L.append(f'  reg [{w - 1}:0] {vn} = 0; integer ic{j} = 0;')
        for k, b in enumerate(bits):
            L.append(f'  assign {b} = {vn}[{k}];')
        clk = 'ck_r' if dmn == 'ck' else 'fc_{}_{}'.format(*bitsplit(dmn))
        words = (w + 31) // 32
        rnds = ', '.join('$random(seed)' for _ in range(words))
        L.append(f'  always @(posedge {clk}) begin #0.5; {vn} = {{{rnds}}}; '
                 f'$fwrite(fd, "I {j} %0d %h\\n", ic{j}, {vn}); ic{j} = ic{j} + 1; end')
        mp.setdefault('_in_order', {})[str(j)] = dict(dom=dmn, bits=bits)
    L.insert(2, '  integer seed = 1062026;')
    for j, (dmn, bits) in enumerate(sorted(outdom.items())):
        bits = sorted(bits, key=lambda s: (bitsplit(s)[0], bitsplit(s)[1]))
        clk = 'ck_r' if dmn == 'ck' else dmn
        L.append(f'  integer oc{j} = 0;')
        L.append(f'  always @(negedge {clk}) begin $fwrite(fd, "O {j} %0d %h\\n", oc{j}, '
                 f'{{{", ".join(reversed(bits))}}}); oc{j} = oc{j} + 1; end')
        mp['_in_order'][f'o{j}'] = dict(dom=dmn, bits=bits)
    L.append(f'  initial begin #({PER} * {NCYC}); $fclose(fd); $display("TB_DONE"); $finish; end')
    L.append('endmodule')
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f'tb_{a.master}.sv').write_text('\n'.join(L) + '\n')
    (out / 'order.json').write_text(json.dumps(mp['_in_order']))
    print(out / f'tb_{a.master}.sv')


def cmd_check(a):
    mp, ports = load(a.gen, a.master)
    order = json.loads((Path(a.log).parent / 'order.json').read_text())
    seqs = defaultdict(dict)
    for ln in Path(a.log).read_text().split('\n'):
        f = ln.split()
        if len(f) != 4:
            continue
        key = f[1] if f[0] == 'I' else 'o' + f[1]
        seqs[key][int(f[2])] = int(f[3], 16) if 'x' not in f[3] and 'z' not in f[3] else None
    # per input bit: sequence
    inbit = {}
    for j, v in order.items():
        if j.startswith('o'):
            continue
        for k, b in enumerate(v['bits']):
            inbit[b] = (j, k)
    res = dict(master=a.master, domains={}, mismatches=0, checked_bits=0)

    def expect(src, c, lat):
        if src == "1'b0":
            return 0
        if src == 'rst':
            return 1
        ij, ik = inbit[src]
        iv = seqs[ij].get(c - lat)
        return None if iv is None else (iv >> ik) & 1

    for j, v in order.items():
        if not j.startswith('o'):
            continue
        osq = seqs[j]
        cyc = sorted(c for c in osq if WARM <= c < NCYC - 10)
        groups = defaultdict(list)          # source input domain -> [(k, out bit, src)]
        for k, b in enumerate(v['bits']):
            src = mp['map'][b]['src']
            groups[inbit[src][0] if src in inbit else 'const'].append((k, b, src))
        for g, lst in sorted(groups.items()):
            best = None
            for lat in range(-2, 16):
                bad = sum(1 for k, b, src in lst[:64] for c in cyc[:40]
                          if osq[c] is None or expect(src, c, lat) != (osq[c] >> k) & 1)
                if best is None or bad < best[1]:
                    best = (lat, bad)
                if bad == 0:
                    break
            lat = best[0]
            bad, badbits = 0, set()
            for k, b, src in lst:
                for c in cyc:
                    ov = osq[c]
                    o = None if ov is None else (ov >> k) & 1
                    e = expect(src, c, lat)
                    if e is None or o is None or e != o:
                        bad += 1
                        badbits.add(b)
            res['domains'][f"{v['dom']}<-{order[g]['dom'] if g in order else g}"] = dict(
                bits=len(lst), latency_periods=lat, cycles=len(cyc), mismatches=bad, bad_bits=sorted(badbits)[:6])
            res['mismatches'] += bad
            res['checked_bits'] += len(lst) * len(cyc)
    res['verdict'] = 'PASS' if res['mismatches'] == 0 and res['checked_bits'] > 0 else 'FAIL'
    print(json.dumps(res))
    return 0 if res['verdict'] == 'PASS' else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['tb', 'check'])
    ap.add_argument('--gen', required=True)
    ap.add_argument('--master', required=True)
    ap.add_argument('--out')
    ap.add_argument('--log')
    a = ap.parse_args()
    return (cmd_tb if a.mode == 'tb' else cmd_check)(a) or 0


if __name__ == '__main__':
    raise SystemExit(main())
