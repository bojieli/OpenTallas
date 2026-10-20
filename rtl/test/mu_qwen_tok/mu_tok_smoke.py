#!/usr/bin/env python3
"""MU-ADOPT-TOK 2026-10-19: MU.TOK.QW command-plane smoke (the MU RTL composition driven by the compiled calendar).

    mu_tok_smoke.py --work DIR [--mut NAME] [--verilator PATH] [--jobs N]

DUT (tb_mu_tok_compose.sv): qfd_dv_cmd_cal_mu NU 4 + qfd_dv_amax_mu NU 4 + qkd_kv_mu_wrow/rrow, the image and every
start from tools/qwen_static_schedule/mu_tok_cases.py.  Cases:
  solo   variant rtl_layer, user 0 only                     (the latency user alone)
  pos2   variant rtl_layer: the of-record resources at layer granularity (what this RTL can play: users 0 and 1)
  pos4   variant cmdplane4: 4 users on the command plane (STRESS: me/su/kv/coll windows dropped; rates not production)
  neg    pos2 with user 1's starts shifted so one of its entries lands on a user-0 entry edge -> fault_code[1] must rise
Checks (PASS needs all):
  K1 pos2/pos4/solo: no calendar fault, no amax mu_fault, no KV range fault, no station result clash, no empty emit
  K2 user 0's events (CMD/SUI/XCI/EMB/SEG/DONE/AM/KV) in pos2 == solo (latency user cycle-identical to single-user)
  K3 every user's events == the compiled starts + image entries (+ C) with its relocation, exact cycles
  K4 every emitted argmax == the golden single-shot argmax of that user's token (2,048 logits, 8 chunks x 16 words, ties -> lower idx)
  K5 every attention q record's KV row (rrow, wrow xa, wrow lane) == 64 + layer + 256 user (mu_calendar.kv_user_rows)
  K6 per-user token period MEASURED on the RTL command plane (argmax emit spacing) == the calendar's token_period
  K7 neg sets fault_code[1]
Mutants (--mut, each must FAIL): cal11 (qfd_dv_cmd_cal_mu MUT 11: relocation/tag/cmd_user of the wrong user),
amax1 (qfd_dv_amax_mu MUT 1: a tie goes to the later chunk), [amax2 (MUT 2: results merge into the current STN user) is
EQUIVALENT once the calendar keeps the station exclusive (cp.stn, F-TOK-1); runnable as a diagnostic, not in the set],
glue1 (bench glue: KV row user = the last START's user, not the issuing playhead), glue2 (STN user field not applied).
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from qwen_static_schedule import mu_tok_cases as MT          # noqa: E402
from qwen_static_schedule import mu_calendar as MC           # noqa: E402

SOURCES = ['rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv', 'rtl/qwen_dv/mu/qfd_dv_amax_mu.sv',
           'rtl/qwen_sys/mu_qwen_20261018/qkd_kv_mu_rowoff.sv',
           'rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv',
           'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']
TB = HERE / 'tb_mu_tok_compose.sv'
MUTS = {'0': {}, 'cal11': dict(MUT=11), 'amax1': dict(AMUT=1), 'amax2': dict(AMUT=2), 'glue1': dict(GLUE_MUT=1),
        'glue2': dict(GLUE_MUT=2)}
S0 = 1100
M32 = 0xffffffff


def logit(u, tok, idx):
    h = ((u * 0x9E3779B1) & M32) ^ ((tok * 0x85EBCA77) & M32) ^ ((idx * 0xC2B2AE3D) & M32)
    h ^= h >> 15
    h = (h * 0x2C1B3C6D) & M32
    h ^= h >> 12
    return (0x3f0000 << 7) | (h & 0x7f)


def okey(v):
    return (~v) & M32 if v >> 31 else v | 0x80000000


def golden(u, tok, chunks=8):
    best = None
    for idx in range(16 * MT.RW * chunks):
        k = okey(logit(u, tok, idx))
        if best is None or k > best[0]:
            best = (k, idx)
    return best[1], logit(u, tok, best[1])


def build(work, vl, mut, jobs):
    d = work / f'b_{mut}'
    exe = d / 'Vtb_mu_tok_compose'
    if exe.exists():
        return exe
    g = [f'-G{k}={v}' for k, v in MUTS[mut].items()]
    cmd = [vl, '--binary', '--timing', '-O2', '-j', str(jobs), '-Wno-fatal', '-Wno-lint', '-Wno-style',
           '-Wno-TIMESCALEMOD', '-Wno-WIDTHCONCAT', '--x-assign', '0', '--x-initial', '0', '--top-module',
           'tb_mu_tok_compose', f'-GSTN_LAT={MT.STN_LAT}', f'-GRW={MT.RW}', f'-GRW_GAP={MT.RW_GAP}', f'-GUVM_STRIDE={MT.UVM_STRIDE}',
           f'-GPIDX_STRIDE={MT.PIDX_STRIDE}', '-Mdir', str(d)] + g + [str(ROOT / s) for s in SOURCES] + [str(TB)]
    d.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    (d / 'build.log').write_text(' '.join(cmd) + '\n' + r.stdout + r.stderr)
    if r.returncode != 0 or not exe.exists():
        r = subprocess.run(cmd, capture_output=True, text=True)       # one retry (PCH race)
        if r.returncode != 0 or not exe.exists():
            sys.exit(f'BUILD FAILED {mut}: see {d}/build.log\n' + (r.stdout + r.stderr)[-3000:])
    return exe


def run(work, exe, name, events, ncyc):
    evf, lg = work / f'{name}.ev', work / f'{name}.log'
    evf.write_text(''.join(f'{c} {k} {v:x}\n' for c, k, v in sorted(events, key=lambda e: (e[0], e[1]))))
    r = subprocess.run([str(exe), f'+EV={evf}', f'+LOG={lg}', f'+NCYC={ncyc}'], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'RUN FAILED {name}: {r.stdout[-2000:]} {r.stderr[-2000:]}')
    out = dict(ev=[], faults=[], muf=0, rf=0, rcol=0, empty=[], am=[], kv=[], end=None)
    for ln in lg.read_text().split('\n'):
        p = ln.split()
        if not p:
            continue
        c, k = int(p[0]), p[1]
        if k in ('CMD', 'SUI', 'SEG'):
            out['ev'].append((c, k, int(p[2]), int(p[3], 16)))
        elif k in ('XCI', 'EMB', 'DONE'):
            out['ev'].append((c, k, int(p[2]), 0))
        elif k == 'FAULT':
            out['faults'].append((c, p[2]))
        elif k == 'MUF':
            out['muf'] += 1
        elif k == 'RF':
            out['rf'] += 1
        elif k == 'RCOL':
            out['rcol'] += 1
        elif k == 'EMPTY':
            out['empty'].append((c, int(p[2])))
        elif k == 'AM':
            out['am'].append((c, int(p[2]), int(p[3]), int(p[4]), int(p[5], 16)))
        elif k == 'KV':
            out['kv'].append((c, int(p[2]), int(p[3]), int(p[4]), int(p[5]), int(p[6])))
        elif k == 'END':
            out['end'] = (int(p[2]), p[3], int(p[4]))
    return out


def expected(sts, segs, C):
    ev = []
    for c, u, stg, _ in sts:
        ent = segs[0] if stg == 0 else segs[2] if stg == MT.LAST_STAGE else segs[1]
        for T, w in ent:
            t = c + T + C
            dst, kind = (w >> 112) & 15, (w >> 1) & 7
            if dst == 14:
                ev.append((t, 'EMB', u, 0) if kind == 1 else (t, 'SEG', u, (w >> 4) & 0xfff))
            else:
                x = MT.reloc(w, u)
                ev.append((t, 'CMD', u, x))
                if kind == 1:
                    ev.append((t, 'SUI', u, (x >> 4) & 0x1ff))
                if kind == 0:
                    ev.append((t, 'XCI', u, 0))
        ev.append((c + ent[-1][0] + C, 'DONE', u, 0))
    return sorted(ev)


def neg_shift(sts, segs, lim=30000):
    """shift of user 1's starts (|d| <= 400, start edges kept distinct) whose first entry edge on a user-0 entry edge
    comes earliest; returns (d, that edge)"""
    def edges(u, d=0):
        e, s = set(), set()
        for c, uu, stg, _ in sts:
            if uu != u or c > S0 + lim:
                continue
            ent = segs[0] if stg == 0 else segs[2] if stg == MT.LAST_STAGE else segs[1]
            s.add(c + d)
            e |= {c + d + T for T, _ in ent}
        return e, s
    e0, s0 = edges(0)
    best = None
    for d in range(-400, 401):
        e1, s1 = edges(1, d)
        hit = e0 & e1
        if d and hit and not (s0 & s1) and (best is None or min(hit) < best[1]):
            best = (d, min(hit))
    if best is None:
        raise SystemExit('no negative shift found')
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    ap.add_argument('--mut', default='0', choices=sorted(MUTS))
    ap.add_argument('--verilator', default=os.environ.get('VERILATOR', 'verilator'))
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--tokens', type=int, default=3)
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    exe = build(work, a.verilator, a.mut, a.jobs)
    res, fails, meta = {}, [], {}
    for case, var, users in (('solo', 'rtl_layer', [0]), ('pos2', 'rtl_layer', None), ('pos4', 'cmdplane4', None)):
        cs = MT.cases(var, a.tokens)
        (work / f'cases_{case}.json').write_text(json.dumps({k: v for k, v in cs.items() if k != 'users'}, indent=1))
        ev, sts, segs = MT.bench_events(cs, c0=2, s0=S0, users=users)
        ncyc = S0 + cs['horizon_cycles'] + 50
        res[case] = run(work, exe, case, ev, ncyc)
        meta[case] = dict(cs=cs, sts=sts, segs=segs)
    # negative control
    cs, sts, segs = meta['pos2']['cs'], meta['pos2']['sts'], meta['pos2']['segs']
    d, d_edge = neg_shift(sts, segs)
    nsts = [(c + (d if u == 1 else 0), u, st, n) for c, u, st, n in sts]
    ev, _, _ = MT.bench_events(cs, c0=2, s0=S0, users=[])
    ev += [(c, 2, (u << 6) | st) for c, u, st, _ in nsts]
    res['neg'] = run(work, exe, 'neg', ev, d_edge + 100)

    # C = issue offset of the playheads (measured on solo: first layer CMD of user 0)
    first = min(c for c, u, st, _ in meta['solo']['sts'])
    cmds = [e for e in res['solo']['ev'] if e[1] == 'CMD' and e[0] >= first]
    C = cmds[0][0] - first - meta['solo']['segs'][1][0][0] if cmds else 0
    summ = dict(mut=a.mut, C_issue_offset=C, cases={})
    for case in ('solo', 'pos2', 'pos4'):
        r, m = res[case], meta[case]
        # K1
        if r['faults'] or r['muf'] or r['rf'] or r['rcol'] or r['empty'] or (r['end'] and r['end'][0]):
            fails.append(f'K1 {case}: faults {r["faults"][:3]} muf {r["muf"]} rf {r["rf"]} rcol {r["rcol"]} '
                         f'empty {r["empty"][:3]} end {r["end"]}')
        # K3
        got = sorted(e for e in r['ev'] if e[0] >= S0)
        want = expected(m['sts'], m['segs'], C)
        if got != want:
            sg, sw = set(got), set(want)
            fails.append(f'K3 {case}: events != compiled (missing {len(sw - sg)} e.g. {sorted(sw - sg)[:2]}; '
                         f'extra {len(sg - sw)} e.g. {sorted(sg - sw)[:2]})')
        # K4
        nh = {}
        for _, u, st, _ in m['sts']:
            if st == 0:
                nh[u] = nh.get(u, 0) + 1
        bad = [(c, u, t, i, v, golden(u, t)) for c, u, t, i, v in r['am'] if (i, v) != golden(u, t)]
        cnt = {u: sum(1 for x in r['am'] if x[1] == u) for u in nh}
        if bad or cnt != nh:
            fails.append(f'K4 {case}: {len(bad)} wrong argmax e.g. {bad[:2]}; emits {cnt} want {nh}')
        # K5
        rows = MC.kv_user_rows(4)
        kbad = [k for k in r['kv'] if not (k[3] == k[4] == k[5] == rows[(k[1], k[2])])]
        nkv = sum(1 for _, u, st, _ in m['sts'] if 1 <= st <= 36)
        if kbad or len(r['kv']) != nkv:
            fails.append(f'K5 {case}: {len(kbad)} wrong KV rows e.g. {kbad[:2]}; records {len(r["kv"])} want {nkv}')
        # K6 measured per-user token period (argmax emit spacing) vs the calendar
        per = {}
        for u in sorted(nh):
            ts = [x[0] for x in r['am'] if x[1] == u]
            per[u] = (ts[-1] - ts[0]) / (len(ts) - 1) if len(ts) > 1 else None
        cal = {x['user']: x['token_period'] for x in m['cs']['users']}
        kbad6 = {u: (per[u], cal[u]) for u in per if per[u] is not None and abs(per[u] - cal[u]) > 0.5}
        if kbad6:
            fails.append(f'K6 {case}: measured token period != calendar {kbad6}')
        agg = sum(MT.CLK / v for v in per.values() if v)
        summ['cases'][case] = dict(variant=m['cs']['variant'], production_calendar=m['cs']['production_calendar'],
                                   starts=len(m['sts']), events=len(got), argmax_emits=cnt, kv_records=len(r['kv']),
                                   measured_token_period=per, calendar_token_period={u: cal[u] for u in per},
                                   measured_tok_s={u: (MT.CLK / v if v else None) for u, v in per.items()},
                                   measured_aggregate_tok_s=agg, end=r['end'])
    # K2 latency-user identity
    u0 = lambda r: sorted([e for e in r['ev'] if e[2] == 0 and e[0] >= S0] + [x for x in r['am'] if x[1] == 0] +
                          [x for x in r['kv'] if x[1] == 0], key=str)
    if u0(res['solo']) != u0(res['pos2']):
        fails.append('K2 user 0 events in pos2 differ from solo')
    # K7
    fc = res['neg']['end'][1] if res['neg']['end'] else '000000'
    if fc[-2] != '1':
        fails.append(f'K7 neg (user 1 shifted {d}) did not set fault_code[1]: {fc}')
    summ.update(neg_shift=d, neg_first_clash_edge=d_edge, neg_fault_code=fc, verdict='PASS' if not fails else 'FAIL', fails=fails)
    (work / f'summary_{a.mut}.json').write_text(json.dumps(summ, indent=1, default=str))
    print(f"MU_TOK_SMOKE_{summ['verdict']} mut {a.mut}" + ('' if not fails else ': ' + ' | '.join(fails)))
    print(json.dumps({k: v for k, v in summ.items() if k != 'fails'}, default=str))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
