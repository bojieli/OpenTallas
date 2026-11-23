# KV D29 review package (KV-D29, 11-23 11:5x PST) -> FABLE-RC-KVHEAD, FABLE-RC-ALL, COORD, VIS-KV
## Compose of record
- K3 = Codex compose (ledger epyc8 kv-plan-r6/d29/kvd29/k3_ledger_pcslit/CUT-LEDGER-KV-D29.tsv, 38 rows) + post steps (d29/k3.chain): PC KREQ, reprice 126 lanes, PCV1BANK2 8a715f0b1bc9 (BANKWIN 0), FIX-SYNC reset graft, final remap, PC FO align, row B (14-type pv split, 71 types / 175 partitions), V3FT, PADRAM, SPINEFAM/BANKFAM, CLASS-FIX-RHI (RST+HSK+IO, 69 types), PV locality, T1SPLIT (hgi_v2 x2 + v5 hst2_t1), SOFTFLOP refinement, PCTAPEGRESS, TAPOFF last (1538 ports / 31 types, census 56/56 PASS).
- Tree plan f75a71af72eb (epyc8 kw45/src_kv_d29_work_r6/.../plan_of_record/plan_c.json), tools rt 174935ee5e9c.
- Gate candidate k3e = K3 + LANDCAP 96bd25042a92 (pv_v12 / pv_v5n band re-site, ADV-LAND-CAP 2->0, PRE 0) + bind_rowcheck.py @ main 43d121c8c0d4 (RELAYSINK as-built-map fix), NO skip, R8/PV fixed point then one strict gate. Unit intel2 kv-d29-k3e-1123, log d29/k3e.out. Plan sha is printed at LANDCAP_APPLIED.
## Gate results so far
- k3c (f75a71af72eb): PRECHECK 0, PRE 0 (125 advisories), G0 PASS 0 errors / 0 pending (71 types, 175 partitions), strict = 15 R8_STALE only (vport ES_0/WS_0 <- pvw_0 u_ctl pad extras). Ran with OT_PLAN_GATE_SKIP=RELAYSINK, so it is not strict.
- RELAYSINK: all 360 FAIL lines (38 types) are false (checker ignored inputs/asbuilt_map_binder2_kst2.json). With the map, 0 FAIL; k1b no-skip bind emitted the same rows with 0 errors. Fix main 43d121c8c0d4 + test (rows_in/H/README.md).
- k3d (Codex r7, skip still set): running. k3e: queued behind it. Result posted on arrival. R8 bar = D28 seal baseline (32 unequal groups, 7 types, 4 afk/kreq inversions ruled BENIGN; fork A verified vs rh12).
## Item table (DIE-FIX-LEDGER KV)
| item | status in D29 | evidence |
|---|---|---|
| rc113 hroot E strip | GATED-pending-k3e | BAND/RING/RES/EFS + HROOT-GEOM 4ca2bc6de1a3 + RINGFORM in K3; b4_place probe (intel1 fam-kv-hroot-r1/d29geom/b4_place) |
| rc114 / rc126 / rc117-hold, pc port_in (RING class) | REASONED (accepted cb9a415f619) | ringeye.tsv FF re-measures; KV-CTLPORT dbc5c772e0d wave key at apply (CTL class) |
| rc116 sys_c dcal | GATED-pending-k3e | rows C 08be3955c5c7 + D c296998f3e31 + RTL 23d08aceeda5 (byte-identical to the HUBC-SYSC-R2 frozen set) |
| rc117 sys_c taps | GATED-pending-k3e | SYSCTAP 7e1264a9eba0 (+50 taps, max 1199/1200, origin t31 protected) |
| sys_c TT -201 (probe C+D+E) | REASONED-OPEN | fork F rows_in/F/REASON.md: S1 u_txcal.ev_* -> att_tx_* 10 b 1.3 mm (no cover) -> named row SYSC-D2DOUT (pin window up to d2d_kv band, or +1 aligned beat-group station) as same-day amendment; S1b/S2 covered by Codex RANKS 46f088d331af (its place unit failed, not relaunched); RING -70 / IO -54 existing reasons; local -61 near-miss. Proposal: HOLD kv3_sys_c at apply until SYSC-D2DOUT. |
| rc118 / rc119 / rc121 pc | REASONED-OPEN (COORD 11:2x) | FABLE-OPEN-KV 10:54 REVIEW-GAPS (PCSLIT/PCGUT blockage released before DPL, GRT 16,161; seam ~3.2k; pc__po_d3 unstationed); G1-G3 + pc_v3 probe = same-day amendment; ALL pc types HELD at apply |
| rc120 AFFAULT | GATED-pending-k3e | AFFAULT in K3 (stand-alone 5b9a55ae26b8 PRE/G0/strict/LAT pass) |
| rc122 pc_v1 bank | GATED-pending-k3e | PCV1BANK2 8a715f0b1bc9 POSTROW, BANKWIN 0; pc_v1 cl7f/cl4ea relaunch after the pc amendment |
| rc123 hgi_v4 ft23 / FT20BAND band overlap | GATED-pending-k3e | FT23STREET c862d73fe64b + FT20BAND 45892e81daaf; HK6 1e709b0765db PRE/G0/strict/LAT/BPC 0, LAND-CAP 0 |
| rc124 hgi_v1 / hst2 | GATED-pending-k3e | HST2SITE cddc1dd754e2 + T1SPLIT (per-destination copies, COORD) |
| rc127 hg centre blob | REASONED-pending-probe | HGFORM 65ada8a83db4 + HGSTREET r2 bb8a5f3c1814 + KRSPCORE 399f5d95fb70 in K3; HGFORM place/GRT probe kv3_hg_v1p2 (intel1 KV-D28/private/KV-D29/kv3_hg_v1p2_1123105128, goal grt) running; result by 13:30 or stays REASONED |
| rc128 pv | GATED-pending-k3e | row B + V3FT + PADRAM aa6a12af054 + PV locality in K3; row-B standalone R7 fa4b3d07f9b8 strict/LAT/BPC 0 |
| rc129 pv_v3 banks | GATED | BANKCORE db83d9ceb6a8 |
| x4 hub_Wi spine | GATED-pending-k3e | HUBWISPINE |
| x8 / x15 hroot ring arcs | GATED-pending-k3e | HROOT-GEOM slg band re-centre; b4 CTS x15 +13.2 MET |
| x10 tap offsets | GATED-pending-k3e | TAPOFF last step, tap_offset_fill check PASS + all-mode cover 56/56 |
| hub_C row E | GATED-pending-k3e (row E 1656764949d7) / residual REASONED | fork F: H1 kvs_attn + delay chains -> HUBC-E2 c95f773d3e97 (2519 seats, PRE+G0 0, not strict-bound) = same-day amendment; H2 reset fanout 210 bits -> reset.leaf_clusters row; H3 seq->bout fork +1 E station; H4 u_d38 N/S split. Proposal: HOLD kv3_hub_C at apply until E2 + H2-H4 rows. |
| CLASS-FIX-RHI row 29 | RST+HSK GATED-pending-k3e; IO REASONED | probe config.mk OT_TAP_RESET_AFFINITY/SPLIT=1, OT_TAP_PAIR_MACRO=1; IO sender_min gives no io_hold.tcl on KV (0 proved sender ports) -> IO-BOUNDARY stays under cb9a415f619 + CTLPORT; CTS-log effect pending the probe |
| KV-CTLPORT rc114 CTL | GATED (tools) | main dbc5c772e0d; apply: kit_wave_edit --set /dies/qwen_kvsys/die_gen_env/OT_PREGRT_HOLD_PORTS_SCOPE=ctl |
| LAND-CAP pv_v5n / pv_v12 | GATED-pending-k3e | LANDCAP 96bd25042a92 |
## At apply (if k3e passes)
- HOLD: all pc types (amendment), kv3_sys_c (SYSC-D2DOUT), kv3_hub_C (E2 + H2-H4); hub_Wo/Eo if the kit_relay_depth __rst_n fix is not in the wave rt.
- Release the 16 WAIT-BIND rows (hgi_*, hg_v1p5/v1p6/v3, hub_Wo). Set the KV-CTLPORT wave key.
- Owed before the cut: whole-die render of the k3e plan (VIS-KV) + ADV-MERGE-RESET-DEPTH / ADV-RESET-NAME on the k3e plan (kv-d29-k3d-reset-1123 waiter does the k3d one).

## Cut outcome at 14:4x PST

- KV-D28 remains the live wave event. KV-D29 missed the 14:00 cut and has no release candidate. K3e `698bf5a0cf52` did not reach its final strict gate. Four native EMIT crashes left stale 11:11 PST reports that the fixed-point script mistakenly reused.
- The fresh exact head has 0 errors, 5,940 R8 members and current effective owner-pad coverage. Actual remaining bind blocker is the strict cl4ea PC cohort split plus an independent bound-only variant plan-cell lookup crash. See `KV-D29.md` 14:4x and E8 native scoped receipts.
- Standalone row-B R7 functional receipts remain valid in their scope. Exact v5n daughter placement remains held, as do the PC and sys_c corrections named above. Consult `results/geom_review/kv_d29_private_places_1436_1123.md` for six viewed results, the corrected render-refusal class, and the HGFORM row-grid first error.
