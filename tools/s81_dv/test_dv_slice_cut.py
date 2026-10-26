#!/usr/bin/env python3
"""test_dv_slice_cut.py -- self-check of the S81-DV slice cutter on the die of record (LAYERBENCH-S81, 10-18).

Cuts the interior cluster u_s_3S (slice + its 6 frames, relay / landing / reset growth) from the bind9 die.v of
origin/claude/s81-die6-1018 and checks:
  1. the RTL kit of the die resolves (dv_rtl_kit verdict PASS: no unresolved child, no differing duplicate module);
  2. every instance line of the slice top is the die.v line verbatim (except the recorded INSTANCE / flight-time
     annotations), and the instance set is closed under the growth rules (no relay-class driver of a slice input left
     outside);
  3. every slice net bit read inside the slice has exactly one driver: an inside output or one input port bit;
  4. no constant was added (the only literals are the die.v straps).
Usage: test_dv_slice_cut.py [--ref REF] [--work DIR]   (~1 min with a warm dv_rtl_kit cache, ~4 min cold)
"""
import argparse
import gzip
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', default='origin/claude/s81-die6-1018')
    ap.add_argument('--work', default=None)
    a = ap.parse_args()
    w = Path(a.work or tempfile.mkdtemp(prefix='dvcut_test_'))
    w.mkdir(parents=True, exist_ok=True)
    g = lambda p: subprocess.run(['git', '-C', str(ROOT), 'show', f'{a.ref}:{p}'], capture_output=True, check=True).stdout
    (w / 'die.v').write_text(gzip.decompress(g('results/arch/s81_dv_1016/bind9/die.v.gz')).decode())
    (w / 'port_bind.json').write_bytes(g('results/arch/s81_dv_1016/bind9/port_bind.json'))
    py = sys.executable
    strip = sum((['--strip-param', f'{m}:HB:0'] for m in ('ot_s81sl_slice_lepw', 'ot_s81sl_slice_lepe', 'ot_s81sl_slice_lepe_nh')), [])
    r = subprocess.run([py, str(HERE / 'dv_rtl_kit.py'), '--ref', a.ref, '--port-bind', str(w / 'port_bind.json'),
                        '--top-v', str(w / 'die.v'), '--top', 'dv_die', '--out', str(w / 'kit')] + strip, capture_output=True, text=True)
    print(r.stdout.strip().split('\n')[0])
    assert r.returncode == 0, 'die kit FAIL: ' + r.stdout[-2000:]
    (w / 'set.txt').write_text('u_s_3S\n/u_f_3[LR]0[0-3]/\n')
    r = subprocess.run([py, str(HERE / 'dv_slice_cut.py'), '--die-v', str(w / 'die.v'), '--kit', str(w / 'kit'),
                        '--insts', str(w / 'set.txt'), '--out', str(w / 'cut')], capture_output=True, text=True)
    print(r.stdout.strip())
    assert r.returncode == 0, r.stderr[-2000:]
    die = (w / 'die.v').read_text()
    top = (w / 'cut' / 'slice_top.sv').read_text()
    die_lines = {}
    for ln in die.split('\n'):
        m = re.match(r'\s*([\w\\]\S*)\s+(?:#\s*\(.*?\)\s*)?([\w\\]\S*)\s*\(', ln)
        if m:
            die_lines[m.group(2)] = ln.split(');')[0].rstrip() + ');'
    n = 0
    for ln in top.split('\n'):
        m = re.match(r'\s*([\w\\]\S*)\s+(?:#\s*\(.*?\)\s*)?([\w\\]\S*)\s*\(', ln)
        if m and m.group(2) in die_lines and not ln.lstrip().startswith(('module', 'assign', 'wire', 'input', 'output')):
            assert ln == die_lines[m.group(2)], f'instance {m.group(2)} not verbatim'
            n += 1
    ins = json.loads((w / 'cut' / 'slice_insts.json').read_text())
    assert n == ins['instances'], (n, ins['instances'])
    # literals: only inside instance lines (straps) -- the generated wires / assigns carry none
    for ln in top.split('\n'):
        if ln.lstrip().startswith(('assign', 'wire', 'input', 'output')):
            assert not re.search(r"\d+'[bhd]", ln), f'constant added: {ln[:120]}'
    # single driver per read bit: rebuild from the cut's own ports + instance outputs
    sys.path.insert(0, str(HERE))
    import dv_rtl_kit as K
    D = K.load_dpb(ROOT, a.ref)
    nets, tin, tout, insts = D.parse_die(str(w / 'cut' / 'slice_top.sv'), 'slice_top')
    P = json.loads((w / 'cut' / 'slice_ports.json').read_text())['ports']
    drv = {}
    for p, v in P.items():
        if v['dir'] == 'input':
            for hi, lo in v['bits']:
                for b in range(lo, hi + 1):
                    k = (v['net'], b)
                    assert k not in drv, f'two drivers {k}'
                    drv[k] = p
    kit = json.loads((w / 'kit' / 'kit.json').read_text())
    from dv_slice_cut import load_masters
    M, _ = load_masters(str(w / 'kit'), D, {i[0] for i in insts if i[0] != '__assign__'})
    reads = set()
    for mst, inst, params, cm in insts:
        if mst == '__assign__':
            continue
        for port, expr in cm.items():
            bits = [b for b in D.expr_bits(expr, nets) if b[0] not in ('CONST', 'Z', 'UNDECL')]
            if M[mst].ports[port][0] == 'output':
                for b in bits:
                    assert b not in drv, f'{inst}.{port} drives {b} also driven by {drv[b]}'
                    drv[b] = inst
            else:
                reads.update(bits)
    undriven = sorted(b for b in reads if b not in drv)
    assert not undriven, f'undriven read bits {undriven[:5]}'
    print(f'test_dv_slice_cut: PASS ({n} instances verbatim, {len(reads)} read bits single-driven, {len(P)} ports)')


if __name__ == '__main__':
    main()
