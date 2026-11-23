# KV D29 review package (KV-D29, rev 2 11-23 16:0x PST: K3g/k3h; rev 1 11:5x) -> FABLE-RC-KVHEAD, FABLE-RC-ALL, COORD, VIS-KV
## Compose of record (rev 2)
- Plan of record candidate = Codex K3g 324af451f9be (epyc8 kw45/src_kv_d29_work_r6/physical/die_plan/qwen_kvsys/plan_of_record/plan_k3g_pc_hg_reseat_1123.json).
  K3g = K3 f75a71af72eb (Codex compose, ledger d29/kvd29/k3_ledger_pcslit/CUT-LEDGER-KV-D29.tsv, 38 rows + post steps, see rev 1 below)
  + LANDCAP 96bd25042a92 + VPORT-EXTRA-REBIND (vport_w_pads_b5 852251383e71, semantic r2 asbuilt 93d84f11ab7c / r8 dca549d208b9)
  + K3e EMIT KeyError fix (main 22fc636471d) + K3f cl4ea one-bit receiver bank + pc origin re-seat (t108/t103 at [88.736,1466.144], 8.64 um)
  + hg bank re-seat on kv3_hg_v1p5 / v1p6 / v3 (6 banks, lower-left moves <= 24 nm x 110 nm, max hop 97.198 um) = the rc127 site-grid fix.
- Gate of record = k3h (intel2 unit kv-d29-k3h-1123, epyc8 d29/k3h.out): Codex's k3g_integrated gate unchanged, tools = full rt bd54869e80c5
  (tools + common_flow, no per-module overlay, so no TOOLSTALE; bind_rowcheck 65556659d65c carries the RELAYSINK fix 43d121c8c0d4).
  Steps: PRECHECK, PRE, G0, TAPOFF check, strict bind --all-gaps with NO skip, LATCHECK, BPC, R8 check + baseline v2. Then (d29/k3h_after.out):
  whole-die render d29/k3h_gate_rt_bd54869/after/kv_d29_k3g_die.png + ADV-MERGE-RESET-DEPTH / ADV-RESET-NAME (both must be 0).
- Codex run kv-d29-k3g-full-isolated-r2-1536 on the same plan with the old per-module tools is the early signal; not the record (TOOLSTALE).
- COORD RULING 11-23 16:3x (for FABLE-RC-ALL): the R8 baseline check v2 is ACCEPTED for k3h. Type conflicts match on type, site count and
  example site; the printed pad values are not compared (kv3_pc_v1__cl7f648944 example pads [3,7] -> [3,8] moved only because of the vport
  rebind); any site-count or site change still fails. kv3_pc_v1__cl7f648944 stays HELD at apply. Checker + test on main 501a435935e8
  (tools/die_plan/r8_baseline_check.py, test_r8_baseline_check.py, 6 pass); gate copy d29/kvd29/check_r8_baseline_v2.py.
- R8 bar = D28 seal baseline (32 unequal groups, 7 conflicting types, 4 afk/kreq inversions BENIGN).
- FABLE-RC pre-verdict (hub 89a2ca96): pc, sys_c, hub_C accepted held-at-apply; D29 is a partial fix of the die.
## Rev 1 compose detail (K3)
- K3 post steps: PC KREQ, reprice 126 lanes, PCV1BANK2 8a715f0b1bc9 (BANKWIN 0), FIX-SYNC reset graft, final remap, PC FO align, row B (14-type pv split, 71 types / 175 partitions), V3FT, PADRAM, SPINEFAM/BANKFAM, CLASS-FIX-RHI (RST+HSK+IO, 69 types), PV locality, T1SPLIT, SOFTFLOP, PCTAPEGRESS, TAPOFF last (census 56/56 PASS).
- History: k3c strict = 15 R8_STALE (root cause: stale owner extra vport_w_pads_b5 after row-B split, fixed by the rebind); k3e v1-v3 failed on script bugs, then a real EMIT KeyError on synthesized kv3_pc_v1__cl4ea58a5c__v1 (fixed 22fc636471d).
## Item table (DIE-FIX-LEDGER KV)
| item | status in D29 | evidence |
|---|---|---|
| rc113 hroot E strip | GATED-pending-k3h | BAND/RING/RES/EFS + HROOT-GEOM 4ca2bc6de1a3 + RINGFORM in K3; b4_place probe (intel1 fam-kv-hroot-r1/d29geom/b4_place) |
| rc114 / rc126 / rc117-hold, pc port_in (RING class) | REASONED (accepted cb9a415f619) | ringeye.tsv FF re-measures; KV-CTLPORT dbc5c772e0d wave key at apply (CTL class) |
| rc116 sys_c dcal | GATED-pending-k3h | rows C 08be3955c5c7 + D c296998f3e31 + RTL 23d08aceeda5 (byte-identical to the HUBC-SYSC-R2 frozen set) |
| rc117 sys_c taps | GATED-pending-k3h | SYSCTAP 7e1264a9eba0 (+50 taps, max 1199/1200, origin t31 protected) |
| sys_c TT -201 (probe C+D+E) | REASONED-OPEN | fork F rows_in/F/REASON.md: S1 u_txcal.ev_* -> att_tx_* 10 b 1.3 mm (no cover) -> named row SYSC-D2DOUT (pin window up to d2d_kv band, or +1 aligned beat-group station) as same-day amendment; S1b/S2 covered by Codex RANKS 46f088d331af (its place unit failed, not relaunched); RING -70 / IO -54 existing reasons; local -61 near-miss. Proposal: HOLD kv3_sys_c at apply until SYSC-D2DOUT. |
| rc118 / rc119 / rc121 pc | REASONED-OPEN (COORD 11:2x) | FABLE-OPEN-KV 10:54 REVIEW-GAPS (PCSLIT/PCGUT blockage released before DPL, GRT 16,161; seam ~3.2k; pc__po_d3 unstationed); G1-G3 + pc_v3 probe = same-day amendment; ALL pc types HELD at apply |
| rc120 AFFAULT | GATED-pending-k3h | AFFAULT in K3 (stand-alone 5b9a55ae26b8 PRE/G0/strict/LAT pass) |
| rc122 pc_v1 bank | GATED-pending-k3h | PCV1BANK2 8a715f0b1bc9 POSTROW, BANKWIN 0; pc_v1 cl7f/cl4ea relaunch after the pc amendment |
| rc123 hgi_v4 ft23 / FT20BAND band overlap | GATED-pending-k3h | FT23STREET c862d73fe64b + FT20BAND 45892e81daaf; HK6 1e709b0765db PRE/G0/strict/LAT/BPC 0, LAND-CAP 0 |
| rc124 hgi_v1 / hst2 | GATED-pending-k3h | HST2SITE cddc1dd754e2 + T1SPLIT (per-destination copies, COORD) |
| rc127 hg centre blob | REASONED-pending-probe | HGFORM 65ada8a83db4 + HGSTREET r2 bb8a5f3c1814 + KRSPCORE 399f5d95fb70 in K3; first probe kv3_hg_v1p2_1123105128 failed early placement (bank origin off native site grid); K3g re-seats the banks on hg_v1p5/v1p6/v3; place probe on the K3g banks launches once k3h strict = 0 (COORD 16:3x), placed render posted to FABLE-RC-ALL |
| rc128 pv | GATED-pending-k3h | row B + V3FT + PADRAM aa6a12af054 + PV locality in K3; row-B standalone R7 fa4b3d07f9b8 strict/LAT/BPC 0 |
| rc129 pv_v3 banks | GATED | BANKCORE db83d9ceb6a8 |
| x4 hub_Wi spine | GATED-pending-k3h | HUBWISPINE |
| x8 / x15 hroot ring arcs | GATED-pending-k3h | HROOT-GEOM slg band re-centre; b4 CTS x15 +13.2 MET |
| x10 tap offsets | GATED-pending-k3h | TAPOFF last step, tap_offset_fill check PASS + all-mode cover 56/56 |
| hub_C row E | GATED-pending-k3h (row E 1656764949d7) / residual REASONED | fork F: H1 kvs_attn + delay chains -> HUBC-E2 c95f773d3e97 (2519 seats, PRE+G0 0, not strict-bound) = same-day amendment; H2 reset fanout 210 bits -> reset.leaf_clusters row; H3 seq->bout fork +1 E station; H4 u_d38 N/S split. Proposal: HOLD kv3_hub_C at apply until E2 + H2-H4 rows. |
| CLASS-FIX-RHI row 29 | RST+HSK GATED-pending-k3h; IO REASONED | probe config.mk OT_TAP_RESET_AFFINITY/SPLIT=1, OT_TAP_PAIR_MACRO=1; IO sender_min gives no io_hold.tcl on KV (0 proved sender ports) -> IO-BOUNDARY stays under cb9a415f619 + CTLPORT; CTS-log effect pending the probe |
| KV-CTLPORT rc114 CTL | GATED (tools) | main dbc5c772e0d; apply: kit_wave_edit --set /dies/qwen_kvsys/die_gen_env/OT_PREGRT_HOLD_PORTS_SCOPE=ctl |
| LAND-CAP pv_v5n / pv_v12 | GATED-pending-k3h | LANDCAP 96bd25042a92 |
## At apply (if k3h passes)
- HOLD: all pc types (amendment; incl. kv3_pc_v1__cl7f648944 per COORD R8 ruling), kv3_sys_c (SYSC-D2DOUT), kv3_hub_C (E2 + H2-H4); hub_Wo/Eo if the kit_relay_depth __rst_n fix is not in the wave rt.
- Release the 16 WAIT-BIND rows (hgi_*, hg_v1p5/v1p6/v3, hub_Wo). Set the KV-CTLPORT wave key.
- Owed before the cut: k3h strict 0 + LAT/BPC/R8-v2 PASS; whole-die render + both reset advisories 0 (k3h_after); rc127 placed render (probe after k3h).
