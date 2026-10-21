#!/usr/bin/env python3
"""DRIVE-S81-SVCFIT 10-20: svc_rs slot fit on the mu7 die vs attw head-group count (option B), joined with the rate model.
MODEL (plan-level areas, no packing proof).  Inputs: summary.json (compose_svcfit.py), the mu7i4 plan facts (ep6
/srv/opentallas-scratch/claude/s81-die11/mu7i4/plan/plan.json: die 31968.5 x 25000 at reticle, 122 frames, svc region
x 10536.4..21432.2, y 1724..4452.1, 16 slots 1214.2 x 1344), mk_attw_lp.py geometry (claude/s81-svc4-attw-1019) with
the hgrp8 child 432 x 432, closed-view LEF sizes on main, the Codex pin packet ebcb8a9d5 (svc_rs pin minimum
1728 x 1555.2 nonentry / 1728 x 1641.6 entry).
  python3 results/token_pass/svcfit_s81_1020/fit_svcfit.py   # -> fit.json + table
"""
import json, math
from pathlib import Path
H = Path(__file__).resolve().parent
G_, CH, HG = 43.2, 86.4, 432.0
up = lambda v: round(math.ceil(v / G_ - 1e-9) * G_, 3)
A_STD = 190000.0                     # mk_attw_lp default: attw minus tiles + landing rings (census attwnotileg)
BIGH = 32 * 41.04                    # c column: 32 ot_sram_1r1w_256x256 stacked (land 12 + pmem 4 + stage 16)


def attw(ncol, gpc):
    """mk_attw_lp geometry generalised: ncol tile columns x gpc groups, one centre c column."""
    colh = gpc * HG + (gpc - 1) * CH
    h = max(up(2 * CH + colh), up(2 * CH + BIGH))
    cw = up(G_ + 172.8 + G_ + 51.408 + G_ + max(A_STD / 0.5 / (h - 2 * G_), 4 * G_) + G_)
    w = up(ncol * (HG + CH) + cw + 2 * CH)
    return w, h


REST_PIN = (1728.0 * 1555.2 * 14 + 1728.0 * 1641.6 * 2) / 16 / 1e6   # svc_rs w/o attw, pin-bound (Codex ebcb8a9d5)
REST_HARD = (8 * 216 * 216 + 4 * 527.04 * 432 + 345.6 * 216 + 151.2 ** 2 + 144 * 17.28 * 32.4) / 1e6
REGION_NOW = (21432.2 - 10536.4) * (4452.1 - 1724.0) / 1e6
FRAME_MM2 = 1436.832 * 2848 / 1e6 + 1017 * 2848 / 2 / 1e6 * 0.0   # frame body (rows 0/1 mean height); channels not counted
GAPF = 1.10                           # column gaps (rq/rd of upper slices) + row gaps
F, TAU = 1.2e9, 4.159
HOP = 1008                            # cycles a stage hop (CAL2 law: 1006 + 2)
T140 = dict(ar=F / 1065.9, mtp=F * TAU / 3286.0)


def main():
    s = json.loads((H / 'summary.json').read_text())
    rate = {r['groups']: r for r in s['rows']}
    shapes = {16: (4, 4), 8: (2, 4), 4: (1, 4), 2: (1, 2)}
    out = []
    for g, (nc, gpc) in shapes.items():
        w, h = attw(nc, gpc)
        a = w * h / 1e6
        slot = a + REST_PIN
        need = 16 * slot * GAPF
        extra = need - REGION_NOW
        frames_lost = math.ceil(extra / FRAME_MM2)
        f = 122 - frames_lost
        n = math.ceil(201 * 116 / f)          # MODEL: scaled from the qualified 116-frame / 201-stage map
        dT = rate[g]['dT']
        row = dict(groups=g, attw_um=[w, h], attw_mm2=round(a, 2), hgrp_mm2=round(16 * g * HG * HG / 1e6, 1),
                   slot_mm2=round(slot, 2), band_need_mm2=round(need, 1), extra_mm2=round(extra, 1), frames=f,
                   stages_model=n, dies_model=round(644 * n / 140))
        for k in ('ar', 'mtp'):
            tau = TAU if k == 'mtp' else 1.0
            T_unit = T140[k] + dT[k]['solved']
            T_all = T_unit + (n - 140) * HOP
            row[k] = dict(unit_only=round(F * tau / T_unit, 1), unit_pct=round(100 * (T140[k] / T_unit - 1), 2),
                          with_frames=round(F * tau / T_all, 1), total_pct=round(100 * (T140[k] / T_all - 1), 2))
        out.append(row)
        print(f"G{g:2d} attw {w}x{h} ({a:.2f}) slot {slot:.2f} band {need:.0f} (+{extra:.0f}) -> {f} frames, ~{n} stages, "
              f"~{row['dies_model']} dies | AR unit {row['ar']['unit_only']} ({row['ar']['unit_pct']}%) all "
              f"{row['ar']['with_frames']} ({row['ar']['total_pct']}%) | MTP unit {row['mtp']['unit_only']} all {row['mtp']['with_frames']} ({row['mtp']['total_pct']}%)")
    res = dict(schema='opentallas.s81_svcfit.fit.v1', grade='MODEL (plan areas, scaled stage count; no packing proof)',
               region_now_mm2=round(REGION_NOW, 1), slot_now_um=[1214.2, 1344.0], rest_pin_mm2=round(REST_PIN, 3),
               rest_hard_mm2=round(REST_HARD, 3), frame_mm2=round(FRAME_MM2, 2), gap_factor=GAPF, die_um=[31968.5, 25000.0],
               die_note='at reticle: W margin 515.7 um, frame top 24705.8 of 25000 -> growth = frames dropped',
               s116_anchor=dict(frames=116, stages=201, ar=1011.1, mtp=3159.2, dies=888,
                                note='qualified map (req201 201/201 PASS); drops f_2R01..f_5L01 above the band: '
                                     'region +~31 mm2 (comb: 39.4 contiguous y<5342 + 6 pockets 1437x2490 between slices)'),
               rows=out)
    (H / 'fit.json').write_text(json.dumps(res, indent=1) + '\n')


if __name__ == '__main__':
    main()
