#!/usr/bin/env python3
"""QLB-PROG (10-18, G-C3) bench of the compiled qfd_tt_ctlm_dv deployment image (tools/qwen_layerbench/ctlm_image.py).

Loads the image into qfd_tt_ctlm_dv exactly as qfd_sys_face replays it, runs a token's stages (0, decode stages, LM head)
with the neighbours (W5 slice status ss5 / ag5, native59 native_ret) answering at their COMPILED cycles (the image's
status timeline), and checks against the compiled expectation:
  * every slice command (SU / XC / SETID) leaves tt_ctlm.cmd on its compiled edge, nothing else leaves;
  * every LOCAL start (EMB, ME segment SEG) pulses on its compiled edge;
  * every head fixed issue / END (pc, unit) fires on its compiled edge, the ROM command (hr ib go) and the native
    command (native_cmd go) leave on the compiled edge after it, every XPF arm leaves on its compiled edge;
  * the control stores seal (control_stores_ready) and no fault rises (cf), command_stage follows the running stage.
Edges are relative to each stage's edge 0 (the dh pin register captures h_start).

Mutants (all must FAIL; fail witnesses committed): --mut 1 (RTL: every calendar entry one edge late), --bmut 1 (the
slices report the SU op before the gate/up matvec done DEP + 1 edges late: the head's chase is unmet on its fixed cycle),
--bmut 2 (image: the first decode SU entry one edge late, the expectation unchanged).

    python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --img DIR [--mut N] [--bmut N] [--work DIR] [--decode 2]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOAD0 = 10



def lp_offsets(root):
    """QW-CTLM5 10-19: the landed cluster's port offsets from its lp record (not hard-coded): (out, tl, in pw, in other)."""
    import json as _j
    c = _j.load(open(root / 'results/arch/landed_parent_1018/qfd_tt_ctlm_dv_lpf/qfd_tt_ctlm_dv_lpf_lp_record.json'))['compiler']
    ii = c['input_port_offset_edges']
    ins = {v for k, v in ii.items() if v and k != 'pw'}
    outs = {v for k, v in c['output_port_offset_edges'].items() if k != 'tl'}
    assert len(ins) <= 1 and len(outs) == 1 and c['reset_release_added_edges'] == 3, ('lp record offsets', ins, outs, c['reset_release_added_edges'])
    return outs.pop(), c['output_port_offset_edges']['tl'], ii['pw'], (ins.pop() if ins else 0)

def slice_fields(gi_hr):
    """hr[452:73] as qfd_dv_slice2 / the tiles decode it (tools/qwen_split/hr_contract.py FIELDS)"""
    sys.path.insert(0, str(ROOT / 'tools' / 'qwen_split'))
    import hr_contract as HC
    out, pos = {'go': gi_hr >> HC.IBW}, HC.IBW
    for n, w in HC.FIELDS:
        pos -= w
        out[n] = (gi_hr >> pos) & ((1 << w) - 1)
    return out


def events_and_expect(img: dict, words: list, n_decode: int, bmut: int):
    C = img['constants']
    ev, exp = [], []
    c = LOAD0
    for a in range(1024):
        ev.append((c, 0, (a << 64) | words[a])); c += 1
    for a in range(8):
        ev.append((c, 1, (a << 64) | words[1024 + a])); c += 1
    dw7 = c - 1
    # BOOT: played once on the seal (qfd_dv_cmd_cal: S = the edge after the DW7 seal edge + 1)
    boot_s = dw7 + 2 - img['constants']['CAL_S']
    for x in img['expected']['boot_cmd_after_seal']:
        exp.append((boot_s + x['edge'], 'CMD', int(x['cmd'], 16)))
    ev.append((c + 4, 6, 0b11))                                   # kok / kwd levels (the T calendar's LEVEL)
    tok, pos = 0x1234, 4321
    # stage starts at the T calendar's compiled spacing (stage 0, the first n decode stages); the LM-head stage follows
    # the last simulated decode stage after one full window (compressed: the bench does not run all 36 layers)
    T = img['stage_starts_T']
    s0 = c + 64
    stages = [(s0 + x['cycle'] - T[0]['cycle'], x['stage']) for x in T[:1 + n_decode]]
    stages.append((stages[-1][0] + max(b['cycle'] - a_['cycle'] for a_, b in zip(T, T[1:]) if 1 <= a_['stage'] <= 36), 37))
    X = img['expected']
    prev_stage = 0
    for e0, stg in stages:
        ev.append((e0, 2, (1 << 42) | (stg << 36) | (tok << 18) | pos))
        if stg != prev_stage:
            exp.append((e0 + 1, 'STAGE', stg))   # command_stage latched on the stage start (STAGE_ME 1)
        prev_stage = stg
        if stg == 0:
            for x in X['stage0_local']:
                exp.append((e0 + x['edge'], 'LOC', ('EMB', 0)))
            continue
        if stg == 37:
            continue
        for x in img['expected']['cmd_at_tt_ctlm']:
            exp.append((e0 + x['edge'], 'CMD', int(x['cmd'], 16)))
        for x in img['expected']['local_at_tt_ctlm']:
            exp.append((e0 + x['edge'], 'LOC', (x['kind'], x['base'])))
        for x in img['expected']['me_issue']:
            exp.append((e0 + x['edge'], 'ISSUE', (x['pc'], x['unit'])))
        for x in X['xpf_arm_at_tt_ctlm']:
            exp.append((e0 + x['edge'], 'XPF', int(x['xpf72'], 16)))
        for x in X['rom_go_at_tt_ctlm']:
            exp.append((e0 + x['edge'], 'ROM', x['pc']))
        for x in X['native_go_at_tt_ctlm']:
            exp.append((e0 + x['edge'], 'NAT', x['pc']))
        # neighbour status at its compiled cycles (levels at the tt_ctlm pins)
        ag = dict(su_busy=0, stn_busy=0)
        ss = dict(su_prog=0)
        nat = dict(native_idle=1)
        late = None
        if bmut == 1:   # the SU op that the gate/up chase waits on reports done DEP + 1 edges late
            gu = next(p for p in img['plan'] if p['kind'] == 'ME' and p['window'] == 'gate_up')
            prev = max((p for p in img['plan'] if p['kind'] == 'SU' and p['pc'] < gu['pc']), key=lambda p: p['pc'])
            late = (prev['done'], C['DEP'] + 1)
        sts = []
        for s in img['status']:
            e = s['edge']
            if late and e == late[0] and s['field'] in ('su_busy', 'su_prog'):
                e += late[1]
            sts.append((e, s['field'], s['value']))
        sts.sort(key=lambda x: x[0])          # stable: the compiled order on one edge is kept
        for e, f, v in sts:
            if f in ag:
                ag[f] = v
                ev.append((e0 + e, 7, (ag['stn_busy'] << 9) | (ag['su_busy'] << 1)))
            elif f in ss:
                ss[f] = v
                ev.append((e0 + e, 8, (v << 45) | (v << 29)))
            else:
                nat[f] = v
                ev.append((e0 + e, 9, (v << 1) | 1))
    ncyc = stages[-1][0] + 200
    return ev, exp, ncyc, stages


def run(a):
    img = json.loads((Path(a.img) / 'ctlm_image.json').read_text())
    words = [int(w, 16) for w in (Path(a.img) / 'program.memh').read_text().split()]
    if a.bmut == 2:     # image mutant: the first decode SU entry one edge late (expectation from the unmodified image)
        base = img['cal']['base']
        first = img['cal']['segments']['1']['first']
        k = base + 2 * first
        w = words[k] | (words[k + 1] << 64)
        w += 1 << 116
        words[k], words[k + 1] = w & ((1 << 64) - 1), w >> 64
    ev, exp, ncyc, stages = events_and_expect(img, words, a.decode, a.bmut)
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    tag = f'm{a.mut}_b{a.bmut}' + (f'_hra{a.hra}' if a.hra else '')
    evf, lgf = work / f'ev_{tag}.txt', work / f'log_{tag}.txt'
    # stable sort: the image words first, then levels, in edge order
    with open(evf, 'w') as f:
        for cy, k, v in sorted(ev, key=lambda e: (e[0], e[1])):
            f.write(f'{cy} {k} {v:x}\n')
    obj = work / (f'obj_m{a.mut}_h{a.hard}' + (f'_l{a.lmut}' if a.landed else '') + (f'_hra{a.hra}' if a.hra else ''))
    srcs = [str(ROOT / l.strip()) for l in open(HERE / 'tt_ctlm_dv_sources.f') if l.strip()]
    if a.landed:    # HF-4 10-18: + the landed cluster (lp.py) in lockstep, LMUT = its mutant
        srcs += [str(ROOT / f) for f in ('rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv', 'rtl/common/landed_parent/ot_pl_land.sv',
                                         'rtl/qwen_dv/lp/qfd_tt_ctlm_dv_lpf_lp.sv')]
    srcs.append(str(HERE / 'tb_qfd_tt_ctlm_prog.sv'))
    if not (obj / 'Vtb').exists():
        cmd = ['verilator', '--cc', '--exe', '--build', '-O2', '-j', '8', '-Wno-fatal', '-Wno-lint', '-Wno-style',
               '-Wno-TIMESCALEMOD', '-Wno-WIDTHCONCAT', '--x-assign', '0', '--x-initial', '0',
               '--top-module', 'tb_qfd_tt_ctlm_prog', '--prefix', 'Vtb', f'-GMUT={a.mut}', f'-GHRA={a.hra}',
               f'-GXPF_EDGES={img["xpf_transport_edges"]}', '-GSTAGE_ME=1', f'-GHARD_HR={a.hard}', *(['+define+TB_HARD'] if a.hard else []),
               *(['+define+TB_LANDED', f'-GLMUT={a.lmut}', f'-GLOFF={lp_offsets(ROOT)[0]}', f'-GLIN_PW={lp_offsets(ROOT)[2]}', f'-GLIN={lp_offsets(ROOT)[3]}'] if a.landed else []), '-Mdir', str(obj), str(HERE / 'main2.cpp')] + srcs
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        (work / f'build_m{a.mut}.log').write_text(p.stdout + p.stderr)
        if p.returncode:
            print(p.stdout[-3000:], p.stderr[-3000:])
            raise SystemExit('verilator build failed')
    subprocess.run([str(obj / 'Vtb'), f'+EV={evf}', f'+LOG={lgf}', f'+NCYC={ncyc}'], cwd=work, check=True,
                   capture_output=True)
    got, errs, info = [], [], {}
    issues, roms, nats, rom_words = [], [], [], []
    for line in open(lgf):
        p = line.split()
        cy, k = int(p[0]), p[1]
        if k == 'CMD':
            got.append((cy, 'CMD', int(p[2], 16)))
        elif k == 'LOC':
            got.append((cy, 'LOC', (p[2], int(p[3]))))
        elif k == 'ISSUE':
            got.append((cy, 'ISSUE', (int(p[2]), int(p[3]))))
            issues.append((cy, int(p[2]), int(p[3])))
        elif k == 'XPF':
            got.append((cy, 'XPF', int(p[2], 16)))
        elif k == 'STAGE':
            got.append((cy, 'STAGE', int(p[2])))
        elif k == 'ROM':
            roms.append(cy)
            got.append((cy, 'ROM', None))
            rom_words.append((cy, slice_fields(int(p[2], 16))))
        elif k == 'ROMRAW':
            errs.append(f'ROM command at {cy} with go on hr[73] (the as-built cmd380 layout): the slice reads go = hr[452]')
        elif k == 'NAT':
            nats.append(cy)
            got.append((cy, 'NAT', None))
        elif k == 'CF':
            errs.append(f'fault rise at {cy}: {" ".join(p[2:])}')
        elif k == 'CSR':
            info['csr'] = cy
        elif k == 'END':
            info['end'] = line.strip()
        elif k == 'LANDED_LOCKSTEP':
            info['landed'] = ' '.join(p[1:])
        elif k == 'LANDED_MISMATCH':
            info.setdefault('landed_mismatch', []).append(' '.join(p))
    exp = [(cy, k, None) if k in ('ROM', 'NAT') else (cy, k, v) for cy, k, v in exp]
    se, sg = set(exp), set(got)
    miss, extra = sorted(se - sg), sorted(sg - se)
    for e in miss[:8]:
        errs.append(f'missing {e[1]} at {e[0]} {e[2] if not isinstance(e[2], int) else hex(e[2])[:40]}')
    for g in extra[:8]:
        errs.append(f'unexpected {g[1]} at {g[0]} {g[2] if not isinstance(g[2], int) else hex(g[2])[:40]}')
    if 'csr' not in info or info['csr'] >= stages[0][0]:
        errs.append(f'control stores not ready before the first stage (csr {info.get("csr")})')
    # ROM / native command go: one per ME issue, a fixed number of edges after it
    me = [(cy, pc) for cy, pc, u in issues if u == 1]
    nat_pcs = {p['pc'] for p in img['plan'] if p['kind'] == 'NATIVE'}
    rom_iss = [cy for cy, pc in me if pc not in nat_pcs]
    nat_iss = [cy for cy, pc in me if pc in nat_pcs]
    d_rom = sorted({r - i for r, i in zip(roms, rom_iss)}) if len(roms) == len(rom_iss) else None
    d_nat = sorted({r - i for r, i in zip(nats, nat_iss)}) if len(nats) == len(nat_iss) else None
    info['rom_go_minus_issue'] = d_rom
    # QW-DIEFIX 10-19: every ROM word decoded as the slice / tiles read it (hr_contract field table): a matvec op
    # (k, tiles, nout > 0, wsrc 0, split <= 9); stage-1 qkv / o / gu / down = the QW-XHEAD XT1 ops (bit-exact there)
    info['rom_fields'] = [dict(edge=cy, **{k: f[k] for k in ('nout', 'tiles', 'k', 'split', 'wbase', 'xbase')})
                          for cy, f in rom_words[:8]]
    for cy, f in rom_words:
        if not (f['k'] and f['tiles'] and f['nout'] and f['wsrc'] == 0 and f['split'] <= 9):
            errs.append(f'ROM word at {cy} does not decode as a matvec in the slice layout: {f}')
            break
    xt1 = [dict(nout=768, tiles=1, k=8, wbase=0, xbase=4096), dict(nout=4096, tiles=3, k=2, wbase=64, xbase=50672),
           dict(nout=3072, tiles=1, k=32, wbase=112, xbase=4096), dict(nout=4096, tiles=3, k=6, wbase=368, xbase=55280)]
    info['stage1_matches_xt1_ops'] = [all(f[k] == o[k] for k in o) for (_, f), o in zip(rom_words[:4], xt1)]
    info['nat_go_minus_issue'] = d_nat
    if d_rom is None or len(d_rom) != 1:
        errs.append(f'ROM command go count {len(roms)} vs ROM issues {len(rom_iss)} (offsets {d_rom})')
    if d_nat is None or len(d_nat) != 1:
        errs.append(f'native command go count {len(nats)} vs native issues {len(nat_iss)} (offsets {d_nat})')
    n = len(se) + 3
    ok = len(se & sg) + (not miss and not extra) * 0 + ('csr' in info) + (d_rom is not None and len(d_rom) == 1) + \
        (d_nat is not None and len(d_nat) == 1)
    return ok, n, errs, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--img', required=True)
    ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--bmut', type=int, default=0)
    ap.add_argument('--hra', type=int, default=0, help='qfd_tt_ctlm_dv HR_ASBUILT (mutant: the as-built hr layout)')
    ap.add_argument('--decode', type=int, default=2)
    # Q-H16C 10-18: 1 = the hard head leaf ot_qfd_tt_ctlm_static_hr (h16c h17, running-stage port), 0 = inline head
    ap.add_argument('--hard', type=int, default=0)
    ap.add_argument('--work', default='/tmp/qlbprog_bench')
    # HF-4 10-18: 1 = also run the landed cluster qfd_tt_ctlm_dv_lpf_lp in lockstep (needs --hard 1); --lmut = its mutant
    ap.add_argument('--landed', type=int, default=0)
    ap.add_argument('--lmut', type=int, default=0)
    a = ap.parse_args()
    ok, n, errs, info = run(a)
    v = 'PASS' if ok == n and not errs else 'FAIL'
    print(f'CTLM_PROG MUT={a.mut} BMUT={a.bmut} HARD_HR={a.hard} HRA={a.hra} DECODE={a.decode}: {v} {ok}/{n}  rom_go-issue {info.get("rom_go_minus_issue")} '
          f'nat_go-issue {info.get("nat_go_minus_issue")} csr@{info.get("csr")} stage1_xt1 {info.get("stage1_matches_xt1_ops")}')
    print('    ROM fields (slice layout):', json.dumps(info.get('rom_fields', [])[:4]))
    for e in errs[:12]:
        print('   ', e)
    if a.landed:
        print(info.get('landed', 'LANDED_LOCKSTEP NO_RESULT'))
        for m in info.get('landed_mismatch', [])[:5]:
            print('   ', m)
    sys.exit(0 if v == 'PASS' else 1)


if __name__ == '__main__':
    main()
