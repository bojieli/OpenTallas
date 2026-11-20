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

## Update 11-20 ~15:45 PST: proof6/r2 ENDED
- Post-GRT hold: -24.07/144 viol -> +4.59 / 0 viol (+200 buffers, 1 chunk). HOLD >= 0 MET after GRT on this form.
- Setup cost: hold buffers pushed worst setup -149.06 -> -217.71 (guard stop), recovery pass ended -153.94 / 692 ends / EnTNS -32,227.
- TT setup repair at GRT crashed: RSZ-0074 (route tree for net155182, rebuffer161029 guide not restored), tt_setup_repair.tcl:136,
  after 1350 iters flat at -367/-380 (3456 ends); 5_1_grt.odb is the UNREPAIRED DB. Gate line: TT setup_est -377 (SETUP_TRIAGE), FF PASS.
- Worst class at every stage after GRT: u_u_land.tag[0][23] -> item6 is the J6 gating class; path read on 5_1_grt.odb next.

## Update 11-20 ~16:30 PST: item6 path read (epyc7 /srv/opentallas-scratch2/claude/opus-sta6, sta.sh/sta.tcl, k/ = kit copy + 5_1_grt.odb)
- All 31 u_u_land.tag ends start at u_u_land.u_rstr.rst_n placed at (1430.9,8.1) (E face), ~1,300 um to land logic at (~157,297): -348.5 TT placement RC.
- Row 6 = proof7-spec item B (land rst_n sink relay D3 + u_rstr at (349.8,355.8)); proof7 tests it. Posted to S81-DIE-R4.
- Next class: lnl3 k_li_d -> lep g_rx dq, 514 ends -396 placement RC on the unrepaired DB (-211.8 after GRT repair).
- RSZ-0074 bug posted to FLEET-WATCH-1400 (hub bc7eb64eafd).
