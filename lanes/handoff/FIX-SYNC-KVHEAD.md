# FIX-SYNC-KVHEAD handoff (Opus; started 11-22 01:1x PST). Fix-propagation lane for KV (qwen_kvsys) + HEAD (s81_head).
Brief: claude scratchpad sync_brief.txt (COORD 11-22 01:3x). Tables: lanes/FIX-SYNC-KV.tsv, lanes/FIX-SYNC-HEAD.tsv.
Lane dir: epyc8 /srv/opentallas-scratch2/claude/fix-sync-kvhead (repo/ = ot-lane-clone cone tools+physical/common_flow; tmp/; kvc02/);
epyc10 same path tmp/ (lbc/ runner, sb_r17b.tsv). Deadlines: KV D28 rows to KV-PLAN-R6 by 11:30 PST (seal 12:00), else D29; HEAD rows to
OPUS-FIX-HEAD-LEP0N-R8 (r18). Report to COORD every 4 h (<250 words).

## Inputs of record
- KV D28 dry compose: epyc8 kv-plan-r6/d28/dry5_post/plan_post.json (fcfa38bdb65b), base d28/base_d27d3.json (48b92c30c8f6).
- HEAD live r17b plan: epyc10 kw45/snap_s81_head/s81_head_r17b_s0/physical/die_plan/s81_head/prep/NF15f/prep/source_plan.json (+published/);
  base r16 same path under s81_head_r16_s0. r18b split tree (LEP0N-R8) s81_head_r18b_split_s0 (building at 01:3x).
- failure_breakdown 01:26: HEAD types 25/26 signed (only hd_lep0N open) -> HEAD propagation is advisory except hd_lep0N. KV types 6/56.

## Round 1 (01:15-01:50)
- KV-C01: landing_band_core false [new] errors on hard-ring bands (17 on hub_Ei/Eo/Wo, would fail D28 publish gate --band-base).
  FIXED main 0c33826deb (hard_ring_buses). Posted to KV-PLAN-R6: put that file in the D28 tree tools. CHECK they did (rerun lbc on final).
- KV-C02: hub hard rings lack band.hard_core. Row ROWS_FIX-SYNC-KVHEAD-hardcore.py (epyc8 lane dir), dry compose da781647edaa, PRE PASS.
  Sent to HUB-R6 (veto by 02:45) default D29.
- KV-C07: pv_v5/v5n station regs inside pvg0_p0/p3 -> PV-R7 advisory D29.
- KV-C03 packed-face: pc_v1 only (in D28). HEAD 0.
- HEAD: LBC r17b 14 new all hd_lep0N stage bands (LEP0N-R8 bandfix in r18); inherited hd_ctl a_rx_i/h_rx_i, hd_host_e coll_i1 (signed types,
  advisory). Sideband audit >405 non-lep0N: hd_serdes 618 est, hd_tile 448, hd_turn_a 443, hd_ctl 437, hd_spn 435 (signed, advisory).
- Not mine: CLASS-SWEEP-R1 (HB4 over-insert, band capacity/overlap, reset tap), TAP-GRID-R5 (taps), NEARMISS-ECO-R1.

## NEXT
- Every 30-60 min: harvest posts (KV-PLAN-R6, HUB-R6, PV-R7, HGI-R6, IOPC-R4, HROOT-R1, HUBC-SYSC-R2, RINGMAC, AHUB, WAITBIND, LEP0N-R8,
  HEAD-CTL-R1, CLASS-SWEEP-R1) for new RULING/ROWS-READY/root causes; add classes; detect; hand rows.
- Before 11:30: rerun landing_band_core (0c33826deb) + p5/p7 scans on the final D28 compose (after PV-R7/HGI-R6 rows land).
- Open: KV-C14 strip density (hroot DRT-0255) needs a placed-DB proxy; pc_v3 cells 998k in plan (check placed count with IOPC-R4).

## 02:2x (after weekly limit)
- RESUMED posted. KV-PLAN-R6 rehearsal 2 on rt 6d2e187f0d65 (dry5 fcfa38bdb65b): PRE PASS, G0 --band-base D27d3 PASS 0 (17 false hard-ring errors gone), strict bind 0, LATCHECK 0, BPC PASS. KV-C01 CLOSED.
- KV-C15 (pc pin stations, IOPC-R4 pcreg) added to table; IOPC-R4 owns siblings pc__cl5a95b461/cl254f2e73; pc_v1 x3 check after D28 bind.
- Pending D28 rows: PV-R7 (v3 split, bind running), HGI-R6. When both land in kv-plan-r6/d28/rows.json: rerun lbc (rt 6d2e187f0d65) + p5/p7 scans on the final compose.
- HEAD: LEP0N-R8 r18c split tree s81_head_r18c_split_s0 (45c1f2f8e091), kits on epyc9; nothing to hand.

- 11-22 thin-band scan (COORD ask): S81 J7 a6771d121e95 == J8 draft 53cab071c82f, 96 rects / 22 types (lanes/handoff/FIX-SYNC-KVHEAD-thinband-S81-J7J8.tsv); QC V3 e69de4a70060 6 hits (…-QC-V3.tsv). Advisories posted to SLICE-R6, SVC-R9, FAIL-S81-1, CB-R4, SLWSLE-R1, J6-ASSEMBLY-R5, QC-PLAN-R13. No rows from me; same form on 5 signed leaf types, so this is an advisory, not a gate.
| H-C08 | FABLE-FIX-HEAD-LEP0N LEP-RINGFF-1 | split re-compose dropped bands[coll_i*].ring_place=ff -> whole ring packed FIRM in netlist order (W -496) | band ring_place ff in base/split parent, not ff in new plan | restore ring_place ff + rect on pin window | fable 04:14 | HEAD hd_lep0N_w FIXED-by-owner; KV/S81/QC 0 hits |
