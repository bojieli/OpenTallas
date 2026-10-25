#!/usr/bin/env python3
"""HBM-HC (2026-10-24): B2 HC native bind as 128-lane HALF hubs -- an --rtl-items fragment for tools/hbm_b2/make_wiring.py.

    python3 tools/hbm_b2/hc_half_items.py --die physical/die_plan/hbm/bind/inputs/die_r18h5.v.gz \
        --asbuilt physical/die_plan/hbm/bind/asbuilt.json --out results/arch/hbm_arch_1024/b2_hc_half_items.json
    python3 tools/hbm_b2/make_wiring.py ... --rtl-items results/arch/hbm_arch_1024/b2_hc_half_items.json --out ...

What it binds (every source is derived from the r18h5 netlist through the transport collapse of tools/hbm_b2/b2_top.py):
  hc_eng            ot_hbm_hc_root_static #(QDRLY 2, QCHX 11, NQ 2): slot 0 = NW, slot 1 = NE (TPRE 7).  Its slot inputs
                    (qps_v / qps / qps_f / q_fault / gathered_mix_*) are rebuilt from hc_NW / hc_NE (as built: the hubs'
                    own outputs through relays, 4 slots SW, SE, NW, NE); its slot outputs shrink to 2 slots (out_width).
  hc_NW, hc_NE      ot_hbm_hc_qhub_static #(as built, W 128): root -> hub inputs rebuilt from hc_eng slot h (descriptor
                    qd_nv 8 b, ingest i_w 6 b, result 768 b); s_i 4,097 b from hcb_<h>0.s_o; bd_nv 8 b, wc_* 14 b.
  hcb_<h>0..7       bank tiles #(as built, W 128): every chain / write-control input that the as-built die feeds from a
                    widened output (o_nv, sum_out, s_o, wc_*, fa_j_o / fb_j_o, bd_nv) is rebuilt from the SAME source port
                    at the new width (a widened port keeps its as-built source; bit order LSB-first unchanged).
Ports whose as-built source is not exactly one widened output port at bits 0.. (concatenations: wf_n / wf_s, ...) keep their
as-built wiring (same width).  The fragment never edits a non-HC instance.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_top as T  # noqa: E402

HALVES = ('NW', 'NE')                   # root slot 0, 1
QSLOT_ASBUILT = {'SW': 0, 'SE': 1, 'NW': 2, 'NE': 3}
W = 128
# widened OUTPUT ports (master-level) -> new width
OUT_W = {
    'ot_hbm_hc_qhub_static': {'bd_nv': 8, 'wc_w': 14, 'wc_n': 14, 'wc_e': 14, 'wc_s': 14},
    'ot_hbm_hc_bankq_static': {'o_nv': 8, 'sum_out': 32 * W},
    'ot_hbm_hc_bankq_ft_static': {'o_nv': 8, 'sum_out': 32 * W, 'fa_j_o': 2, 'fb_j_o': 2},
    'ot_hbm_hc_bankq0_static': {'o_nv': 8, 'sum_out': 32 * W, 's_o': 32 * W + 1},
    'ot_hbm_hc_bankq_term_static': {'sum_out': 32 * W},
}
# widened INPUT ports -> new width
IN_W = {
    'ot_hbm_hc_qhub_static': {'d_nv': 8, 'i_w': 6, 's_i': 32 * W + 1},
    'ot_hbm_hc_bankq_static': {'d_nv': 8, 'sum_in': 32 * W, 'j': 2},
    'ot_hbm_hc_bankq_ft_static': {'d_nv': 8, 'sum_in': 32 * W, 'j': 2, 'fa_j': 2, 'fb_j': 2},
    'ot_hbm_hc_bankq0_static': {'d_nv': 8, 'j': 2, 's_i': 32 * W + 1},
    'ot_hbm_hc_bankq_term_static': {'d_nv': 8, 'sum_in': 32 * W, 'j': 2},
}
# root (NQ 2) slot outputs: per-slot width; hub input <- root output slot h
ROOT_OUT = dict(qd_v=1, qd_ss=1, qd_nv=8, qd_wa=10, qd_xa=10, qi_v=1, qi_kind=1, qi_slot=2, qi_lo=5, qi_w=6, qi_cnt=12,
                qi_word=10, result_v=1, result_position=3, result=768)
ROOT_OUT_W4 = dict(qd_nv=7, qi_w=5)     # as-built NQ 4 per-slot widths that differ
HUB_FROM_ROOT = dict(d_v='qd_v', d_ss='qd_ss', d_nv='qd_nv', d_wa='qd_wa', d_xa='qd_xa', i_v='qi_v', i_kind='qi_kind',
                     i_slot='qi_slot', i_lo='qi_lo', i_w='qi_w', i_cnt='qi_cnt', i_word='qi_word', result_v='result_v',
                     result_position='result_position', result='result')
# root slot inputs <- hub output (per-slot width)
ROOT_IN = dict(qps_v=('ps_v', 1), qps=('ps', 32), qps_f=('ps_f', 1), q_fault=('eng_fault', 1),
               gathered_mix_v=('gathered_mix_v', 1), gathered_mix_row=('gathered_mix_row', 5),
               gathered_mix_pos=('gathered_mix_pos', 3), gathered_mix_data=('gathered_mix_data', 32))


def src_list(die, inst, port):
    segs = T.parse_expr(die.insts[inst]['conns'][port], die.widths)
    out = []
    for s, _ in die.resolve(segs):
        if s[0] == 'c':
            out.append(['const', s[1], s[2]])
        else:
            si, sp = s[1].rsplit('__', 1) if '__' in s[1] else (None, s[1])
            out.append([si, sp, s[2], s[3]])
    return out


def add_params(params, extra):
    p = params.strip()
    return (p + ', ' + extra) if p else extra


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--die', required=True)
    ap.add_argument('--asbuilt', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ab = json.loads(Path(a.asbuilt).read_text())
    die = T.Die(a.die, ab['transport'])
    remaster, rebuild, out_width = {}, {}, {}
    checks = []

    # ---- root NQ 2
    r = die.insts['hc_eng']
    assert r['master'] == 'ot_hbm_hc_root_static', r['master']
    remaster['hc_eng'] = dict(master=r['master'], params=add_params(r['params'], '.NQ(2)'))
    out_width['hc_eng'] = {p: 2 * w for p, w in ROOT_OUT.items()}
    for p, (hp, w) in ROOT_IN.items():
        # as-built check: slot QSLOT_ASBUILT[h] of the root input is hub h's output (through relays)
        sl = src_list(die, 'hc_eng', p)
        flat = []
        for e in sl:
            flat += [(e[0], e[1], b) for b in range(e[2], e[3] + 1)] if e[0] != 'const' else [('const', 0, 0)] * e[1]
        for h in HALVES:
            q = QSLOT_ASBUILT[h]
            got = flat[q * w:(q + 1) * w]
            exp = [(f'hc_{h}', hp, b) for b in range(w)]
            checks.append(dict(what=f'hc_eng.{p} as-built slot {q} <- hc_{h}.{hp}', ok=got == exp))
        rebuild.setdefault('hc_eng', {})[p] = [[f'hc_{h}', hp, 0, w - 1] for h in HALVES]   # LSB-first: slot 0 = NW
    # ---- half hubs + banks
    for s, h in enumerate(HALVES):
        q = QSLOT_ASBUILT[h]
        ring = [f'hc_{h}'] + [f'hcb_{h}{k}' for k in range(8)]
        for n in ring:
            i = die.insts[n]
            remaster[n] = dict(master=i['master'], params=add_params(i['params'], f'.W({W})'))
            ow = {p: v for p, v in OUT_W[i['master']].items() if p in i['conns']}
            if ow:
                out_width[n] = ow
        hub = f'hc_{h}'
        # root -> hub
        for hp, rp in HUB_FROM_ROOT.items():
            w = ROOT_OUT[rp]
            w4 = ROOT_OUT_W4.get(rp, w)
            sl = src_list(die, hub, hp)
            checks.append(dict(what=f'{hub}.{hp} as-built <- hc_eng.{rp} slot {q}',
                               ok=sl == [['hc_eng', rp, q * w4, q * w4 + w4 - 1]]))
            rebuild.setdefault(hub, {})[hp] = [['hc_eng', rp, s * w, s * w + w - 1]]
        # widened inputs keep their as-built source port at the new width
        widened_srcs = {(n, p) for n in ring for p in OUT_W[die.insts[n]['master']]}
        for n in ring:
            m = die.insts[n]['master']
            for p, nw in IN_W[m].items():
                if p not in die.insts[n]['conns'] or (n == hub and p in HUB_FROM_ROOT):
                    continue
                sl = src_list(die, n, p)
                srcs = {(e[0], e[1]) for e in sl if e[0] != 'const'}
                ok = len(sl) == 1 and len(srcs) == 1 and next(iter(srcs)) in widened_srcs and sl[0][2] == 0
                if not ok and p == 's_i' and len(sl) == 2 and sl[0][1] == 'sum_out' and sl[1][1] == 'f_out' \
                        and sl[0][0] == sl[1][0] and sl[0][0] in ring and sl[0][2] == 0:
                    # bank 0 chain-exit relay input {f_out, sum_out} of the terminal bank 7
                    rebuild.setdefault(n, {})[p] = [[sl[0][0], 'sum_out', 0, 32 * W - 1], [sl[0][0], 'f_out', 0, 0]]
                    checks.append(dict(what=f'{n}.s_i <- {{{sl[0][0]}.f_out, {sl[0][0]}.sum_out[{32 * W - 1}:0]}}', ok=True))
                    continue
                if not ok:
                    # j of a bank fed by a 13-b write-control copy: wc_*[10] (as built) -> wc_*[11:10]
                    if p in ('j', 'fa_j', 'fb_j') and len(sl) == 1 and sl[0][0] in ring and sl[0][1].startswith('wc_') and sl[0][2] == 10:
                        rebuild.setdefault(n, {})[p] = [[sl[0][0], sl[0][1], 10, 11]]
                        checks.append(dict(what=f'{n}.{p} <- {sl[0][0]}.{sl[0][1]}[11:10] (as built [10])', ok=True))
                        continue
                    checks.append(dict(what=f'{n}.{p} as-built source {sl}', ok=False))
                    continue
                si, sp = next(iter(srcs))
                rebuild.setdefault(n, {})[p] = [[si, sp, 0, nw - 1]]
                checks.append(dict(what=f'{n}.{p} <- {si}.{sp}[{nw - 1}:0] (as built [{sl[0][3]}:0])', ok=True))
            # write-control ports {wv, xv, j, wa} that read a wc_* copy by bit: wv / xv move up by one bit
            for p in ('wv', 'xv', 'wa', 'fa_wv', 'fa_xv', 'fa_wa', 'fb_wv', 'fb_xv', 'fb_wa'):
                if p not in die.insts[n]['conns']:
                    continue
                sl = src_list(die, n, p)
                if len(sl) == 1 and sl[0][0] == hub and sl[0][1].startswith('wc_'):
                    lo, hi = sl[0][2], sl[0][3]
                    if lo >= 11:   # wv (12) / xv (11) -> 13 / 12
                        rebuild.setdefault(n, {})[p] = [[hub, sl[0][1], lo + 1, hi + 1]]
                        checks.append(dict(what=f'{n}.{p} <- {hub}.{sl[0][1]}[{hi + 1}:{lo + 1}] (as built [{hi}:{lo}])', ok=True))
    bad = [c for c in checks if not c['ok']]
    item = dict(id='R-HC', kind='rtl+wiring', status='done' if not bad else 'FAIL',
                what='hc_eng NQ 2 (slot 0 NW, slot 1 NE, TPRE 7) + hc_NW / hc_NE ot_hbm_hc_qhub_static W 128 (128-lane half '
                     'hubs) + hcb_{NW,NE}0..7 W 128 bank tiles (bankq0 / ft / plain / terminal); same pairwise tree, no '
                     'numerics change. Benches: run_hc_w_default_eq.sh (W 64 = originals), run_hc_half128.sh (W 128 vs 2 x '
                     'W 64 + 7th add, mutants). Die file list: canonical ot_hbm_hc_bankq_term_static.sv replaces the '
                     'scoped hcbt.sv.', checks=len(checks), check_fail=[c['what'] for c in bad])
    out = dict(schema='opentallas.hbm_b2.rtl_items.v1', by='HBM-HC', remaster=remaster, rebuild=rebuild,
               out_width=out_width, items=[item])
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(dict(checks=len(checks), fail=len(bad), bad=[c['what'] for c in bad][:20])))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
