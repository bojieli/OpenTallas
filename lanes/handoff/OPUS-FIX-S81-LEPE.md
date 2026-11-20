# OPUS-FIX-S81-LEPE handoff (Opus successor of FABLE-FIX-S81-LEPE, 2026-11-20 ~15:30 PST)

Only owner of lepe kits (COORD). Goal: lepe/lepw LP kits to sign-off. Rows file: lanes/handoff/FABLE-FIX-S81-LEPE-RIP1-rows.json
(items 1-5 final, item6 land.tag provisional, hold_structural note). Posts: lanes/posts/FABLE-FIX-S81-LEPE.md. J6 owner: S81-DIE-R4.

## Main commits (mine)
- 0f2e402edce RELAY-IDX: kit_istations.py rs_dff_succ, NAME[k] keys site the aliased last relay stage (test_kit_istations.py).
- 5802101050d KIT-RD-1 + f3a172a6cc1: tools/die_plan/kit_relay_depth.py; bind kit-rtl applies sink relay_depth rows on hard-core
  pins and refuses (BindError naming the row) any it cannot apply; check_branch refuses missing relay_branch copies. Tests
  test_kit_relay_depth.py. Scan: s81 1212/1212 relay_depth + 887/887 branch bound, KV 285/285, 0 silently dropped.
- 11f7c845850 kit_wave OOM_KILL_FREE=3.

## proof6/r2 (running, epyc9 /srv/opentallas-scratch2/claude/fable-lepe/proof6/r2/dsdv_slice_lepe_mu_LP__t2)
RIP1 + rows 1-3 (row 1 hand-written in bound RTL, orig *_bound.sv.orig_p6), crg sites, corrected LEF. ot-run epyc9 80 GB.
- GRT overflow 0; post-CTS TT -403.58 (roq 1462 ends); post-GRT TT start -167.83/385 -> -149.06/208 (worst u_u_land.tag[0][*]).
- Hold: pre-GRT -205.98 -> after repair port_in 3726 -116.07 only (32,839 cells); post-GRT -24.07/144 viol, hold repair at TNS 0 (iter 170).
- NEXT: when run ends read final 5_1_grt hold/setup; run STA path report on u_u_land.tag (item6) via ot-run (not epyc9 if full).
  Do NOT use proof6/dsdv_slice_lepe_mu_LP__t2 (Fable overwrote it).
## proof7 (queued for memory, epyc9 fable-lepe/opus-p7)
Reproducible: build.sh (mk7.py, apply_krd.py, p7_extra.py, inputs/ + inputs.sha256) = r2 + Fable proof7-spec (land rst_n relay D3,
122 non-core taps; tap_span_um not applied on d8e tools). `ot-run --mem 96 --threads 16 --hosts epyc9 --dir .../opus-p7 -- bash build.sh grt`, log run.log.

## Wave kits
lepw_mu_C__t1 attempt 21 on event b05c98f7919 (epyc2). All 4 lane-core types (lepe_mu_LP__t2, lepe_nh_mus_LP__t1, lepw_mu_LP__t2,
lepw_mus_LP__t2) carry the corrected lane LEF at b05c98f7919 (DRT-0073 crashes were old event 3fa87b84b18). Watch for DRT-0073 recurrence.

## Open
1. item6 land.tag path read; 2. lockup rows for lepe cross_tap (LOCKUP-STATION-1130 s81 rows not published; derive on a lepe CTS kit);
3. setup -149 > -42 gate: rows 4 (a)+(b) + item6 needed for J6; 4. Waiters biou3b6k9 (proof6) / bsipkaewt (proof7) die with this session.
