#!/usr/bin/env python3
"""v21 pins of the three Engram MIX copy-cluster leaves that are not arithmetic roots (S-ELEM-C 2026-10-15, MIX4 home
771.12 x 3229.2, clusters stacked N-S with rows N->S shell | add8 | mul4 | mul4 | chunk8 | chunk8+sum | scalar row):
  ot_s81_engram_mixq_shell  742.284 x 54.0 (height: room for the pin flops + hold stages of both dense faces): N face = the top / VM side (start, desc, requests, returns, writes, done,
                            fault); S face = four column groups at the mul4 / add8 column pitch 186.84 (h, kv, w,
                            result slices 256c..256c+255) + the scalar control bits; W = clock / reset.
  ot_s81_engram_mix_control 90.72 x 64.8 (scalar row): N = relay leaf + sums; W = norms + signed_sqrt; E = sigmoid.
  ot_s81_engram_rly         43.2 x 21.6 (mid-cluster): N = shell / add8 / mul4 side, S = control side.
Same rule as the die tools: M5 on N/S, M4 on E/W, 2 tracks (0.096 um) a bit, 0.96 um between ports."""
import json, re
from pathlib import Path
import v19_pins_1014 as V
R = Path(__file__).resolve().parents[2]
SRC = R / 'rtl/dsrom_sys/engram/mix'
OUT = R / 'physical/s81_die_pins/v21_engram_arithmetic'


def ports(module, text):
    m = re.search(r'module\s+%s\s*#\s*\(.*?\)\s*\((.*?)\);' % module, text, re.S) or re.search(r'module\s+%s\s*\((.*?)\);' % module, text, re.S)
    body = re.sub(r'//[^\n]*', '', m.group(1)); out = {}; d = None; w = 1
    for tok in [t.strip() for t in body.replace('\n', ' ').split(',')]:
        mm = re.match(r'(input|output)\s+(?:wire|reg)?\s*(\[[^\]]+\])?\s*(\w+)$', tok)
        if mm:
            d = mm.group(1); w = mm.group(2); name = mm.group(3)
        else:
            mm = re.match(r'(\[[^\]]+\])?\s*(\w+)$', tok); name = mm.group(2)
            if mm.group(1): w = mm.group(1)
        out[name] = (d, w)
    return out


def bits(w, env):
    if not w: return 1
    hi, lo = w[1:-1].split(':')
    return int(eval(hi, {}, env)) - int(eval(lo, {}, env)) + 1


def place(groups, L, pitch=.096):
    pp = {}
    for face, seq in groups.items():
        for start, names in seq:
            cur = start
            for n, b in names:
                pp[n] = [[face, 'M5' if face in 'NS' else 'M4', round(cur + pitch * i, 3), .084] for i in range(b)]; cur += pitch * b + .96
            assert cur <= (L[0] if face in 'NS' else L[1]) - 1, (face, cur)
    return pp


def main():
    t4 = (SRC / 'dsfd_engram_mix4_c.sv').read_text(); tm = (SRC / 'ot_s81_engram_mix.sv').read_text()
    env = dict(N=32, VM_LAT=3)
    sh = {k: bits(w, env) for k, (d, w) in ports('ot_s81_engram_mixq_shell', t4).items()}
    ol = [742.284, 54.0]; P = 186.84
    cols = [(4.032 + P * c, [(f'{n}#{c}', 256) for n in ('h', 'kv', 'w', 'result')]) for c in range(4)]
    # the scalar control bits sit at the middle of the S face, between the column-1 and column-2 groups, under the
    # mid-cluster relay leaf
    misc = [(n, sh[n]) for n in ('go', 'iv', 'phase', 'copy', 'eps', 'scale', 'gv', 'gc', 'ov', 'oc', 'mf')]
    cols.append((300.0, misc))
    north = [(n, sh[n]) for n in ('start', 'desc', 'rq_v', 'rq_row', 'vtag', 'rs_v', 'rs_d', 'wq_v', 'wq_row', 'wq_mask', 'wq_d', 'done', 'fault')]
    pp = place({'N': [(4.032, north)], 'S': cols}, ol)
    # merge the column slices of h / kv / w / result into whole buses (bit 256c + i)
    for n in ('h', 'kv', 'w', 'result'):
        pp[n] = [b for c in range(4) for b in pp.pop(f'{n}#{c}')]
    pp['ck'] = [['W', 'M4', 4.032, .084]]; pp['rst'] = [['W', 'M4', 4.992, .084]]
    assert {p: len(v) for p, v in pp.items()} == sh, set(sh) ^ set(pp)
    meta = lambda ck, rs: {'source': 'tools/s81/engram_mix4_leaf_pins_v21.py', 'clock_entries': {'stream': [ck]}, 'reset_entries': {'stream': [rs]},
                           'adoption': 'actual source native CTS/TT/FF/DRC required; parent / calendar qualification open'}
    V.write(OUT, 'ot_s81_engram_mixq_shell', ol, pp, 'ck', 'N = top/VM side; S = column groups at the mul4/add8 pitch + scalar bits; W clock/reset', 'v21_engram_mix4', meta('ck', 'rst'))
    ct = {k: bits(w, dict(N=32)) for k, (d, w) in ports('ot_s81_engram_mix_control', tm).items()}
    ol = [90.72, 64.8]
    pp = place({'N': [(4.032, [(n, ct[n]) for n in ('go', 'phase', 'in_v', 'copy', 'scale', 'mvalid', 'mfault', 'avalid', 'af', 'add_copy',
                                                      'gate_v', 'gate_copy', 'fault', 'a_gate', 'rv', 'rf', 'rhh', 'rkk', 'rdd')])],
                'W': [(4.032 + 1.92, [(n, ct[n]) for n in ('nv', 'nf', 'norm_rstd', 'g_v', 'g_x')])],
                'E': [(4.032, [(n, ct[n]) for n in ('eg_valid', 'gy', 'g_fault')])],
                'S': [(4.032, [(n, ct[n]) for n in ('gate', 'hh', 'kk', 'dd')])]}, ol)
    pp['clk'] = [['W', 'M4', 4.032, .084]]; pp['arst_n'] = [['W', 'M4', 4.992, .084]]
    assert {p: len(v) for p, v in pp.items()} == ct, set(ct) ^ set(pp)
    V.write(OUT, 'ot_s81_engram_mix_control', ol, pp, 'clk', 'N relay+sums, W norms/signed_sqrt, E sigmoid, S unused gate/hh/kk/dd outputs', 'v21_engram_mix4', meta('clk', 'arst_n'))
    ry = {k: bits(w, {}) for k, (d, w) in ports('ot_s81_engram_rly', tm).items()}
    ol = [43.2, 21.6]
    pp = place({'N': [(2.016, [('up_i', 69), ('dn_o', 36)])], 'S': [(2.016, [('up_o', 69), ('dn_i', 36)])]}, ol, pitch=.336)
    pp['clk'] = [['W', 'M4', 4.032, .084]]; pp['arst_n'] = [['W', 'M4', 4.992, .084]]
    assert {p: len(v) for p, v in pp.items()} == ry
    V.write(OUT, 'ot_s81_engram_rly', ol, pp, 'clk', 'N shell/add8/mul4 side, S control side', 'v21_engram_mix4', meta('clk', 'arst_n'))
    print('pins written: shell', sum(sh.values()), 'control', sum(ct.values()), 'rly', sum(ry.values()))


if __name__ == '__main__':
    main()
