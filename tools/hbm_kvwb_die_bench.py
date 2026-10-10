#!/usr/bin/env python3
"""hbm-system 2026-10-08 (T3 gap 3): die-level KV / CKV / index-key WRITE PATH bench.

RTL: rtl/hbm_accel/service/ot_hbm_kvwb_hub.sv (dskv_wb ALL_STACKS + ot_hbm_kport_map + 4 credit-flowed sector links)
-> physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv WB=1 (x4) -> rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv (x4, timed
HBM3E stack with REFpb and the write rules).  Bench rtl/test/hbm_accel/tb_hbm_kvwb_die.sv (Verilator).

The checker is independent of the RTL: the expected sectors come from the Python address map of
tools/hbm_accel_dskv_wb.py (sector_addr / owner_k, the map the 768/768 dskv_wb record was checked with) and the
controller decode (pc_of / bank_of / row_of of ot_hdc_v41x_idx_hbm, re-written here).  Checks per case:
  * every PHY write lands on the pseudo-channel its address decodes to (pc_of(s) == port), full strobes;
  * the multiset of (stack, pc, bank, row, col, data) writes equals the expected one (no missing / extra / wrong);
  * at the first fence_ok after the last row, DRAM holds the expected final bytes at every written location;
  * concurrent KV reads (+rd) on the e link return DRAM content (no read is lost or corrupted by the writes).
Negative controls: MUT=1 (one data bit flipped in the hub) and +early=1 (DRAM read before the fence) must FAIL.

    python3 tools/hbm_kvwb_die_bench.py --work DIR --out RECORD.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_accel_dskv_wb as D  # noqa: E402

VERILATOR = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
SOURCES = ['rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv', 'rtl/hbm_accel/service/ot_hbm_accel_dskv_wb.sv',
           'rtl/hbm_accel/service/ot_hbm_kport_map.sv', 'rtl/hbm_accel/service/ot_hbm_kvwb_hub.sv',
           'physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',
           'rtl/test/hbm_accel/tb_hbm_kvwb_die.sv']
TOP = 'tb_hbm_kvwb_die'
WR0, CR0, KR0 = 0, 80, 96                      # bench row bases (the 30-bit K address holds rows < 2^15)
D.WIN_ROW0, D.CKV_ROW0, D.KEY_ROW0 = WR0, CR0, KR0
SRC_LAYERS, RATIO = D.SRC_LAYERS, D.RATIO


# ---- controller decode (ot_hdc_v41x_idx_hbm, NPC 32, LPC 5, ROW_SHIFT 15)
def pc_of(s):
    return ((s >> 2) ^ (s >> 7) ^ (s >> 12)) & 31


def bank_of(s):
    row = s >> 15
    return ((((s >> 12) ^ (row >> 2)) & 7) << 2) | ((s ^ row) & 3)


def decode(s):
    return pc_of(s), bank_of(s), s >> 15, (s >> 7) & 31


class Plan:
    """Rows in feed order and the expected writes (stack, pc, bank, row, col, data32) of one die."""

    def __init__(self, die):
        self.die, self.rows, self.writes, self.shadow = die, [], [], {}

    def window(self, pos, L, data):
        data = data + bytes(544 - len(data))
        self.rows.append((0, L, 0, pos, 0, data))
        w = pos % 128
        for t in range(17):
            self.writes.append((w >> 5, w & 31, *D.sector_addr(0, L, t), data[32 * t:32 * t + 32]))

    def shadow_load(self, slot, blk):
        self.rows.append((0, slot, 0, 0, 1, blk))
        self.shadow[slot] = bytearray(blk)

    def ckv(self, pos, L, data):
        slot, r2 = SRC_LAYERS.index(L), RATIO[L] == 2
        self.rows.append((1, slot, int(r2), pos, 0, data + bytes(544 - len(data))))
        own, k, n = D.owner_k(pos, r2)
        if own == self.die:
            for t in range(9):
                S = 9 * k + t
                self.writes.append(((S % 128) >> 5, S % 32, *D.sector_addr(1, slot, S >> 7), data[32 * t:32 * t + 32]))

    def key(self, pos, L, data):
        slot, r2 = SRC_LAYERS.index(L), RATIO[L] == 2
        self.rows.append((2, slot, int(r2), pos, 0, data + bytes(544 - len(data))))
        own, k, n = D.owner_k(pos, r2)
        blk = self.shadow.setdefault(slot, bytearray(544))
        i = n & 7
        blk[68 * i:68 * i + 68] = data          # the unit merges into its shadow on accept, owner or not
        if own == self.die:
            kb = 17 * (k >> 3)
            for S in range((68 * k) >> 5, ((68 * k + 67) >> 5) + 1):
                t = S - kb
                self.writes.append(((S % 128) >> 5, S % 32, *D.sector_addr(2, slot, S >> 7), bytes(blk[32 * t:32 * t + 32])))


def kaddr(pc, bank, row, col):
    bhi, blo = (bank >> 2) ^ ((row >> 2) & 7), (bank & 3) ^ (row & 3)
    hi5 = ((row & 3) << 3) | bhi
    return (row << 15) | (bhi << 12) | (col << 7) | ((pc ^ col ^ hi5) << 2) | blo


def cases(rng):
    out = {}
    # golden rows of the W17 1M reference: L20 (ratio 1) on its owner die 31, L2 (ratio 2) on die 63, + a non-owner
    for name, L, die in (('golden_L20_owner31', 20, 31), ('golden_L2_owner63', 2, 63), ('golden_L20_nonowner0', 20, 0)):
        g = D.golden_rows(L)
        p = Plan(die)
        slot = SRC_LAYERS.index(L)
        p.shadow_load(slot, bytes(rng.randrange(256) for _ in range(544)))
        p.window(D.POS, L, g['win'])
        p.ckv(D.POS, L, g['ckv'])
        p.key(D.POS, L, g['key'])
        out[name] = p
    # a full token: 40 window rows + every KV-source layer's CKV / key, at random positions, on a die that owns some
    for name, die, npos in (('token_die5', 5, 3), ('token_die77', 77, 2)):
        p = Plan(die)
        base = rng.randrange(1 << 19) & ~7
        # put the first block on this die for ratio 1: n = pos, b = n >> 3, owner b mod 96
        base = ((base >> 3) // 96 * 96 + die) << 3
        for slot in range(8):
            p.shadow_load(slot, bytes(rng.randrange(256) for _ in range(544)))
        for j in range(npos):
            pos = base + j
            for L in range(40):
                p.window(pos, L, bytes(rng.randrange(256) for _ in range(528)))
                if L in SRC_LAYERS:
                    p.ckv(pos, L, bytes(rng.randrange(256) for _ in range(288)))
                    p.key(pos, L, bytes(rng.randrange(256) for _ in range(68)))
        out[name] = p
    return out


def hx(b):
    return format(int.from_bytes(b, 'little'), 'x')


def build(work, mut):
    d = work / f'obj_mut{mut}'
    exe = d / f'V{TOP}'
    if exe.exists():
        return exe
    cmd = [VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-j', '8', '-O2', '--top-module', TOP,
           '--Mdir', str(d), f'-GMUT={mut}', f'-GWR0={WR0}', f'-GCR0={CR0}', f'-GKR0={KR0}'] + [str(ROOT / s) for s in SOURCES]
    d.mkdir(parents=True, exist_ok=True)
    with open(work / f'build_mut{mut}.log', 'w') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True, cwd=work)
    return exe


def run(exe, work, name, plan, early=0, rd=1, tag=''):
    d = work / f'{name}{tag}'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'rows.txt').write_text(''.join(f'{k} {s} {r} {pos} {sh} {hx(b)}\n' for k, s, r, pos, sh, b in plan.rows))
    exp_final = {}
    for st, pc, bk, rw, cl, b in plan.writes:
        exp_final[(st, kaddr(pc, bk, rw, cl))] = b
    (d / 'peek.txt').write_text(''.join(f'{st} {a}\n' for st, a in sorted(exp_final)))
    out = d / 'out.txt'
    subprocess.run([str(exe), f'+rows={d}/rows.txt', f'+die={plan.die}', f'+out={out}', f'+peek={d}/peek.txt',
                    f'+early={early}', f'+rd={rd}'], capture_output=True, text=True, timeout=3600, cwd=d)
    txt = out.read_text() if out.exists() else ''
    bad = []
    got = Counter()
    for m in re.finditer(r'^W (\d+) (\d+) (\d+) ([0-9a-f]+) ([0-9a-f]+) (\d+)$', txt, re.M):
        st, pc, s, strb, data = int(m[1]), int(m[2]), int(m[3]), int(m[4], 16), int(m[5], 16)
        dpc, bk, rw, cl = decode(s)
        if dpc != pc:
            bad.append(f'write on PC {pc} decodes to PC {dpc}')
        if strb != 0xffffffff:
            bad.append(f'partial strobe {strb:x}')
        got[(st, pc, bk, rw, cl, data.to_bytes(32, 'little'))] += 1
    want = Counter(plan.writes)
    if got != want:
        miss, extra = want - got, got - want
        bad.append(f'writes: {sum(miss.values())} missing, {sum(extra.values())} unexpected')
    dram_bad = 0
    for m in re.finditer(r'^M (\d+) (\d+) ([0-9a-f]+)$', txt, re.M):
        if int(m[3], 16).to_bytes(32, 'little') != exp_final[(int(m[1]), int(m[2]))]:
            dram_bad += 1
    if dram_bad:
        bad.append(f'{dram_bad} DRAM words differ at the fence')
    if len(re.findall(r'^M ', txt, re.M)) != len(exp_final):
        bad.append('DRAM peek incomplete')
    f = re.search(r'^F rows=(\d+) issued=(\d+) acked=(\d+) fence_ok=(\d+) map_fault=(\d+) t_rows_ps=(\d+) '
                  r't_fence_ps=(\d+)', txt, re.M)
    if not f:
        bad.append('no fence line')
        fr = {}
    else:
        fr = dict(zip(('rows', 'issued', 'acked', 'fence_ok', 'map_fault', 't_rows_ps', 't_fence_ps'),
                      map(int, f.groups())))
        if fr['issued'] != len(plan.writes) or fr['acked'] != fr['issued'] or fr['map_fault']:
            bad.append(f"fence counts {fr}")
    r = re.search(r'^R sent=(\d+) got=(\d+)', txt, re.M)
    rderr = len(re.findall(r'^RDERR', txt, re.M))
    if rd and (not r or r[1] != r[2] or rderr):
        bad.append(f'concurrent reads: {r.groups() if r else None}, {rderr} mismatches')
    return dict(case=name + tag, die=plan.die, rows=len(plan.rows), sectors=len(plan.writes),
                kinds=dict(Counter(k for k, *_ in plan.rows)), fence=fr,
                reads=dict(sent=int(r[1]), got=int(r[2])) if r else None,
                verdict='PASS' if not bad else 'FAIL', problems=bad[:6])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    a.work.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261008)
    cs = cases(rng)
    with ThreadPoolExecutor(2) as ex:
        exe0, exe1 = ex.map(lambda m: build(a.work, m), (0, 1))
    jobs = [(exe0, n, p, 0, 1, '') for n, p in cs.items()]
    jobs += [(exe1, 'golden_L20_owner31', cs['golden_L20_owner31'], 0, 0, '_neg_mut1_bitflip'),
             (exe0, 'token_die5', cs['token_die5'], 1, 0, '_neg_early_no_fence')]
    with ThreadPoolExecutor(min(8, len(jobs))) as ex:
        res = list(ex.map(lambda j: run(j[0].resolve(), a.work.resolve(), j[1], j[2], early=j[3], rd=j[4], tag=j[5]),
                          jobs))
    pos_ = [r for r in res if '_neg_' not in r['case']]
    neg = [r for r in res if '_neg_' in r['case']]
    rec = dict(schema='opentallas.hbm_system.kvwb_die.v1',
               source_commit=subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True,
                                            text=True).stdout.strip(),
               source_dirty=bool(subprocess.run(['git', 'status', '--porcelain', '--'] + SOURCES, cwd=ROOT,
                                                capture_output=True, text=True).stdout.strip()),
               input_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES + ['tools/hbm_kvwb_die_bench.py']},
               simulator='Verilator 5.050', clocks_ps=dict(hub=833, svc_and_phy=1024),
               cases=res,
               verdict='PASS' if all(r['verdict'] == 'PASS' for r in pos_) and all(r['verdict'] == 'FAIL' for r in neg)
               else 'FAIL',
               summary=dict(positive=f"{sum(r['verdict'] == 'PASS' for r in pos_)}/{len(pos_)} PASS",
                            sectors=sum(r['sectors'] for r in pos_),
                            negatives_fail=f"{sum(r['verdict'] == 'FAIL' for r in neg)}/{len(neg)}"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec['summary']), rec['verdict'])
    for r in res:
        print(r['case'], r['verdict'], r['sectors'], r['fence'].get('t_fence_ps') if r['fence'] else None, r['problems'][:2])
    return 0 if rec['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
