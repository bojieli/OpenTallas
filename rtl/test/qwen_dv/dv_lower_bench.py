#!/usr/bin/env python3
"""QLB-C4 10-18 (G-C4): the DV slice lowering (tools/qwen_layerbench/dv_lower.py) on the 12-slice qfd_dv_slice2 die
chain (tb_qfd_dv2.sv N 12, the die's cmd / scalar hop structure: dv2f14bq has no relay on any slice-to-slice cmd / sc
hop), Verilator 5.050.

    dv_lower_bench.py --work DIR [--calibrate] [--mutant rso1|broadcast] [--seed N]

Stimulus = ONLY what the compiler emitted: the per-slice PROG images as kind-3 stream table words (driven on
dvs_W5.st_wi -- on the die that port is tied idle: die gap, see dv_lower die_gaps), every command on its compiled edge
at dvs_W5.cmd_wi, x loaded into each slice's compiled local X region over the AR return chain (bench stimulus: the
residual x a layer leaves; PORTS arm one slice at a time).
Checks (PASS needs all): (1) the RB word r every slice passes upward equals the golden
rsqrt(reduce_chunked(x * x) * 2^-12 + eps) (hdc_golden: R-ARITH csum8 blocks + pairwise top in the golden order);
(2) every PSUM leaves every slice on the edge and with the tag the compiler scheduled (static schedule, no collision);
(3) no slice fault.  --calibrate measures the SSQ PSUM leave offsets (each slice alone) -> slice_ages.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_layerbench'))
import dv_bench as B          # noqa: E402
import dv_bench2 as B2        # noqa: E402
import dv_lower as D          # noqa: E402

G, F = B.G, B.F
N = D.NSLICE
P_CMD, P_ARET, P_SWI = 0, 1, 41
T0 = 16


class Events:
    def __init__(self):
        self.ev, self.cmd_edges = [], set()

    def cmd(self, t, c):
        if t in self.cmd_edges:
            raise SystemExit(f'BENCH ERROR: two commands at the chain entry on edge {t}')
        self.cmd_edges.add(t)
        self.ev.append((t, P_CMD, c))

    def at(self, t, p, v):
        self.ev.append((t, p, v))

    def write(self, path):
        with open(path, 'w') as f:
            for t, p, v in sorted(self.ev, key=lambda e: (e[0], e[1])):
                f.write(f'{t} {p} {v:x}\n')


def build(work):
    obj = work / 'obj_n12'
    exe = obj / 'Vtb'
    if not exe.exists():
        cmd = ['verilator', '--cc', '--exe', '--build', '-O2', '-j', '16', '-Wno-fatal', '-Wno-lint', '-Wno-style',
               '-Wno-TIMESCALEMOD', '--x-assign', '0', '--x-initial', '0', '--top-module', 'tb_qfd_dv2', '--prefix', 'Vtb',
               '-GMUT=0', f'-GN={N}', '-Mdir', str(obj), str(HERE / 'main2.cpp')] + [str(ROOT / s) for s in B2.SRCS2]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (work / 'build.log').write_text(r.stdout)
        if r.returncode:
            raise SystemExit(f'BENCH ERROR: build failed (see {work}/build.log)')
    return exe


def run(work, name, ev, ncyc):
    exe = build(work)
    evf, lgf = work / f'{name}.ev', work / f'{name}.log'
    ev.write(evf)
    subprocess.run([str(exe), f'+EV={evf}', f'+LOG={lgf}', f'+NCYC={ncyc}'], check=True, stdout=subprocess.DEVNULL)
    out = {}
    for line in lgf.read_text().split('\n'):
        if line.strip():
            c, n, h = line.split()
            out.setdefault(n, []).append((int(c), int(h.replace('x', '0').replace('X', '0').replace('z', '0'), 16)))
    return out


def load_prog_and_x(ev, lw, x, t):
    """PROG words (kind 3) for every slice on W5.st_wi, then x of every slice's owned blocks into its X region."""
    ev.cmd(t, D.cmd_setid(0))                       # ids first: table words and commands are taken by dst = id
    t += 2 * N + 6
    for s in range(N):
        for w in lw['prog_stream'][s]:
            ev.at(t, P_SWI, D.stream_table_word(3, s, w['eaddr'], int(w['payload'], 16)))
            t += 1
    t += 2 * N + 8
    blocks = lw['ownership']['residual']['blocks_per_slice']
    xb = lw['vm']['X']['base']
    for s in range(N):
        ev.cmd(t, D.cmd_ports(s, ar_base=xb, ar_en=1))
        t += 2 * s + 6
        vals = np.concatenate([x[D.BLOCK * b:D.BLOCK * (b + 1)] for b in blocks[s]])
        for w in range(0, len(vals), 16):
            ev.at(t, P_ARET, B.ar_word(vals[w:w + 16]))
            t += 1
        t += s + 6
        ev.cmd(t, D.cmd_ports(s, ar_base=xb, ar_en=0))
        t += 2 * s + 8
    return t


def psums(log):
    """{(slice, edge): tag} of PSUM words leaving each slice downward"""
    out = {}
    for name, lst in log.items():
        if name.startswith('S') and name.endswith('SD'):
            s = int(name[1:-2])
            for c, w in lst:
                if (w >> 44) & 7 == 1:
                    out[(s, c)] = (w >> 32) & 0xFFF
    return out


def calibrate(work, seed):
    """each slice alone (one SSQ at a time, wide gaps): PSUM j leave edge at the slice's own dn_o - cmd landing"""
    lw = D.lower(ages=dict(ssq_psum_out=[0, 100, 200], root_cfg_lead=4, source='calibration placeholder (PROG / ROOT fields only)'))
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(4096).astype(F)
    ev = Events()
    t = load_prog_and_x(ev, lw, x, T0)
    smap = lw['slice_map']
    for s in range(N):
        ev.cmd(t + s, D.cmd_root(s, int(s == 0), 32, lw['vm']['SSX']['base'], fuse=int(s == 0), rx=lw['vm']['RX']['base'],
                                 eps=lw['root']['eps'] if s == 0 else 0, k=lw['root']['k'] if s == 0 else 0))
    t += N + 40
    probe = {}
    for s in (N - 1, 1):
        probe[s] = t
        ev.cmd(t, D.cmd_su(0, s))
        t += 600
    log = run(work, 'cal', ev, t + 100)
    ps = psums(log)
    meas = {}
    for s, te in probe.items():
        own = sorted(c for (m, c), tag in ps.items() if m == s and tag in lw['ssq'][s]['tags'])
        meas[s] = [c - (te + smap['cmd_arrival'][s]) for c in own]
    L = meas[1]                                      # slice 1 owns 3 blocks, slice 11 two
    if len(L) != 3 or meas[N - 1] != L[:2]:
        raise SystemExit(f'CALIBRATE FAIL: PSUM offsets differ by slice {meas}')
    hop = sorted(c for (m, c), tag in ps.items() if m == N - 2 and tag == lw['ssq'][N - 1]['tags'][0])
    own0 = probe[N - 1] + smap['cmd_arrival'][N - 1] + L[0]
    rec = dict(schema='opentallas.qwen.dv-slice-ages.v1', ssq_psum_out=L, root_cfg_lead=4,
               sc_hop_measured=(hop[0] - own0) if hop else None, per_slice=meas,
               source='rtl/test/qwen_dv/dv_lower_bench.py --calibrate (tb_qfd_dv2 N 12, Verilator 5.050); offsets = '
                      'edge the PSUM j word leaves the slice dn_o (S<k>SD log) - (chain entry edge + cmd arrival)',
               root_cfg_lead_note='structural: the root slots clear on the ROOT cfg edge; PSUMs land >= 4 edges later')
    (work / 'slice_ages.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f'CALIBRATE ssq_psum_out={L} sc_hop={rec["sc_hop_measured"]} per_slice={meas}')
    if rec['sc_hop_measured'] != D.SC_HOP:
        print(f'CALIBRATE FAIL: measured scalar hop {rec["sc_hop_measured"]} != compiler SC_HOP {D.SC_HOP}')
        return 1
    return 0


def main_run(work, seed, mutant):
    lw = D.lower(mutant)
    (work / 'lowering.json').write_text(json.dumps(lw, indent=1) + '\n')
    rng = np.random.default_rng(seed)
    x = (rng.standard_normal(4096) * rng.choice([0.05, 1.0, 30.0])).astype(F)
    x[rng.integers(0, 4096, 8)] *= F(50)
    x = (x * np.repeat(F(10.0) ** rng.uniform(-1.5, 1.5, 32).astype(F), 128)).astype(F)  # block sums over decades
    eps = np.array([lw['root']['eps']], dtype=np.uint32).view(F)[0]
    r = G.rsqrt(G.add(G.mul(G.reduce_chunked(G.mul(x, x)), F(2.0 ** -lw['root']['k'])), eps))
    exp = B.u32(r)
    ev = Events()
    t = load_prog_and_x(ev, lw, x, T0)
    base = t + 8
    for c in lw['commands']:
        ev.cmd(base + c['edge'], int(c['cmd'], 16))
    end = base + max(c['edge'] for c in lw['commands']) + 900
    log = run(work, f'run_{mutant or "m0"}', ev, end)
    errs = B2.status_ok2(log)
    # (1) r at every slice
    ok = 0
    for s in range(N):
        rb = [w & 0xFFFFFFFF for _, w in log.get(f'S{s}SU', []) if (w >> 44) & 7 == 2]
        if rb == [exp]:
            ok += 1
        else:
            errs.append(f'slice {s}: RB words {[hex(v) for v in rb]} want [{exp:#010x}]')
    # (2) PSUMs on their compiled edges and tags
    ps = psums(log)
    smap, L = lw['slice_map'], lw['ages']['ssq_psum_out']
    want = {}
    for s in range(N):
        te = base + lw['ssq_entry'][s]
        for j, tag in enumerate(lw['ssq'][s]['tags']):
            lv = te + smap['cmd_arrival'][s] + L[j]
            for m in range(s, 0, -1):          # the root (0) absorbs: no dn_o word
                want[(m, lv + D.sc_down_edges(smap, s, m))] = tag
    miss = {k: v for k, v in want.items() if ps.get(k) != v}
    extra = {k: v for k, v in ps.items() if k not in want}
    if miss or extra:
        errs.append(f'PSUM schedule: {len(miss)} of {len(want)} words not on their compiled edge/tag '
                    f'(first {sorted(miss.items())[:3]}), {len(extra)} unscheduled (first {sorted(extra.items())[:3]})')
    else:
        ok += 1
    verdict = 'PASS' if ok == N + 1 and not errs else 'FAIL'
    print(f'DV_LOWER {verdict} {ok}/{N + 1} mutant={mutant or 0} r={exp:#010x} psums={len(want)} '
          f'commands={len(lw["commands"])}')
    for e in errs[:8]:
        print('   ', e)
    return 0 if verdict == 'PASS' else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    ap.add_argument('--calibrate', action='store_true')
    ap.add_argument('--mutant', choices=('rso1', 'broadcast'))
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    return calibrate(work, a.seed) if a.calibrate else main_run(work, a.seed, a.mutant)


if __name__ == '__main__':
    raise SystemExit(main())
