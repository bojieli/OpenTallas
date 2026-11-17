# FABLE-FIX-QC-DIECLK handoff (QC die clock closure + cb family, end to end). Started 2026-11-16 20:4x PST.

Work dir epyc2 /srv/opentallas-scratch3/claude/fable-fix-qc-dieclk (repo/ = my clone, wiA/, wiB/, helper scripts).
Client logs intel2 ~/fable-fix-qc-dieclk/. Lanes directed by posts: QC-CLK-R2 (rows), QC-TYPES-R (kits), QC-PLAN-R (plan, wave).

## Measured so far
- Residual 707 pairs (projection, tol 11, latch on launch tap): all flop -> flop, 31 tap pairs, 634 fail only by the 2 x tol = 22 ps
  window, 65 fail on an ideal clock (zero-logic pipe stages vs 25 ps hold uncertainty), 606 within -20 ps. Tighter tol: tol 5 -> 267,
  tol 3 -> 168, tol 0 -> 73. No per-pair budget or tap move is needed: it is ordinary padding. (resid.py on fable-pd-qc-mclk/rows.tsv)
- What-if A (wiA: failed kit cee3540cfd65 4_cts.odb unchanged + kit SDC rewritten with S4q9m cb rows 5eb16cc73797 + lever-3 repair):
  before 1,736 endpoints, cross-tap 1,699 worst -81.55; after ONE pass 0 endpoints, wns +5.00, 2,369 hold cells (0.55 %),
  TT setup estimate unchanged -294.44, 0 overlaps, 861 s. Old rows: 36,093 cells and -211.66 kept.
- What-if B (wiB: same placement, CTS re-run with lever 2 + cb rows): hop-latch pass 5,892 latches on their launch tap, 1,058
  re-hung, 256 without a tapped launch flop. Post-CTS FF gate: 785 endpoints = cross_tap 712 worst -44.17, same_tap 71 worst -47.80,
  port_in 2 at -91.84 (IO shift not regenerated). After one pass: 0 endpoints, +5.01, 1,311 hold cells, setup unchanged -285.78, 475 s.
- Setup read (setupA, TT, placement RC, repaired wiA DB): wns -294.44, 417 endpoints, all internal; 409 are one class
  u_fab_u_x_*.u_st.b_d -> tap_d / cap / u_d*_a_d.r[0] (worst = zero logic, 20 buffers, 955 ps of wire); 8 are u_lk_nk latch -> core.
  Old source has 0 ot_qfd_xcst_rep cells; the L2 source has it (rtl/physical/qcluster/qfd_c_stn.sv). Setup on cb is UNPROVEN until
  the pilot on the L2 source; pilot gate: no b_d -> tap_d/cap/a_d endpoint below -42 at post-CTS TT.
- Limits of both: old S4Q6D source (no r301 xcst_rep), IO window shift kept at the old W 644.2, placement RC.

## Source
- claude/fable-fix-qc-dieclk-1116 @dd226b837fa: clock_taps.tcl hop-latch pass also takes u_lk_nk_*; pregrt_ff_hold pg_verdict accepts
  on endpoint + TNS gain, pass loop continues while endpoints fall >= 5 %; GRT-form anchors follow; +5 tests.
  GATE main=d1fa289b1cb pass=25/25, READY posted 21:1x; waits for the COORD ruling / merge.
- The S4q9m published tree must carry these two files, else every cb kit repeats the FALLBACK (told QC-PLAN-R).

## Open / next
1. s4q9m_l2d chain (E2 fable-die-qc-r/chain/qc/s4q9m_l2d, kit started 19:45, about 3 h): QC-CLK-R2 posts l2d rows; QC-PLAN-R
   composes S4q9m = l2d a915f1136c27 + rows + G rows + tool files, bind / LATCHECK / G0, publish E7/E8, atomic apply.
2. cb pilot before adoption (directive 21:1x): private plan = L2 19be3f0a3bb4 + cb rows, private src = L2 tree + 2 tool files,
   canary for cbn_q01__clab6e67f2 to route + sign-off. Gate at post-CTS: cross_tap <= 2,000, ws >= -90, 0 u_lk_nk_* endpoints
   open; after repair 0 endpoints. If not launched by 22:15 run it by hand (kit_wave.py step --config, private AP_DIR).
3. After the pilot signs off: release cb18 on s29q103S4Q9M, 18 types / 192 partitions; export signed types to AGIdock + rtx-pro.
4. Die clock gate: die STA with real cb views (routed pair setup >= 0, hold >= +10) once cb views exist; first proof = DRT + RCX
   of one cb region vs the SPEF offsets (QC-CLK-R2 self-review note).
5. Advisory: 6 taps over the 1,200-sink cap in cbn_q01 (clk_t115 5,425, clk_t104 2,471, clk_t42 2,488, clk_t103 2,249,
   clk_t39 1,354, clk_t97 1,281); trees still matched to 2 ps on the worst pair; finer tap pitch is a later event.

## Method shared (COORD request): post METHOD to KV-CLK-R2 / HEAD-DIE-R 21:1x (diagnose per tap pair, SPEF row cut, same-DB what-if).

## Not checked
- Routed (RCX) hold of the padded pairs; other cb types' own DBs; whether the l2d cb rows equal the s4q9m_r cb rows to 1 ps.

## CODEX takeover 2026-11-16 22:2x PST
- Actual live pilot is pilot2, not pilot1. Pilot1 FAIL kit_rtl21:56: symlink farm resolved6 HDL paths outside the source tree. Failed evidence kept. Claude corrected to full cp-a src_l2cb3 and restarted as pilot2; first mkcopy read-only cp refusal retained, then corrected successfully.
- pilot2 GEN live E8 PID2011528, unit2011243-1794895727;99.9%CPU/RSS585MB at22:26. Intel2 run-item50864, watcher172958 (chain_route.sh50864) will route after placement; no duplicate started. Work: E8 fable-fix-qc-dieclk/pilot2/items/cbn_q01__clab6e67f2/attempt_1. Intel2 logs ~/fable-fix-qc-dieclk/pilot2. Localized actual kit filelist DOES contain r301 ot_qfd_xcst_rep source, unlike old failed source.
- dd226 normal25/25 GREEN record recovered byte-identically from intel2-local mq-gate slot0 into ~/merge-queue/gates (original scp-to-self failed). Source now APPROVED r454, no rerun. Exact authored delta onto frozen L2 is E8 fable-fix-qc-dieclk/dd226_on_eb1e_L2_exact.patch SHA04db50aa87b25a0de236f4bf45a35d5610fd915141f2e27e02386800c627fe3f (68lines/2files), sibling JSON before/after hashes. Parent QC-PLAN-R has path for M source composition.
- Personally viewed plan render exact511500f23114: four regular cores,147um central/78um horizontal channels, continuous edge FT streets, broadbus pins beside sourcecolumn, centre/per-core taps. PASS-COND plan scope; record+PNG E8 fable-fix-qc-dieclk/results/geom_review/cb_pilot2_plan_511500f23114.*. Actual placement/PDN still to inspect when ready; no physical signoff inferred.

## 23:0x PST engineering updates
- Pilot2 L2+cbrows progressed GEN exit0/lint0/preflightPASS; source closure includes r301. PLACE admitted E8 unit2322334-1794897419; sealed physical work /srv/opentallas-scratch2/claude/ot-jobs/cbn_q01__clab6e67f2-place-outgoing-giraffe-2322635-1794897419/work. Synth complete; global-place hooks ongoing (face/FT/istations:0missing, max FT hop370.2um). Existing auto-route watcher kept. Actual2_3floorplan image personally inspected: pilot2/layout_20261117_065258/floorplan.png, review record in results/geom_review. Clock135taps likewise inspected, no hardcore-interior placement.
- Final M is NOT the same physical pilot: cbn_q01 count_straps widths7->6 and10 soft rings D8->D4. M cbrows equal5eb16 but cannot borrow full L2pilot causal-ready. Parent preparing immutable finalMtree/bind; launch M-specific cbn and special cbf_q01_s2 pilots once tuple exists (no sourcecopy needed). Root criterion: actualCTS+reloadedGRT TT>=-42/internalFF>=0/overflow0, matching relevantMcontracts; no fullDRTwait. Post cb-ready only on measured PASS.
- Distinct old failures diagnosed with actual reports, no reruns. cbncldd6ea846 oldCTS b_d[511]->tap_d[466] -279.04 (r301 fanout); oldGRT residual NK latch->u_t03 -57.28 with0.19psdatawire (clock phase cause). cbf_q00_s2 oldCTS cnt[0]->tap_d[503] -2084.70; r301 per16bitsegment cnt/run copies address it; hold had already reached0eps, later199k GRT repair scans hit retired12h cap. cbf_q01_s2 oldCTS reset u_cland_rst_a00_i->u_cland_fstart_y_o12 -3027.20, GRT reset->u_cland_origin -517.98, plus serdes fallingring->dsel -210.55CTS/-114.32GRT. CurrentL2 ACTUAL boundRTL fixes reset with local fstart_2 fromrst_rl222 and fstart_3 fromrst_rl206; specialserdes class needs its own M measurement. cbf_q01_s2 remains ACTIVE c_W5_bf_01 (onecopy); do not call it retired.
- Read-only diagnostic helpers staged E8 pilot2/setup_classes.sh + setup_classify.py (source-class TT, only if failure) and grt_census.{sh,tcl} (canonical signoff internalFF census, uses exact postCTS-GRT RC/clock frontend, fails placement fallback, readonlykit). Not launched without needed checkpoints. If globalFF>=0 already, extra census unnecessary. Otherwise require STD_MIN_START trunc0/err0 and STD_MIN_NONPORT core_n0/core_wns0, no hidden reg path behind port.

## Codex takeover: MBR causal diagnosis, 2026-11-17 00:10 PST

Failed MBR bind remains FAIL162; no release or qualified proof. Fresh R8 bootstrap diagnostic from exact MBR bus_groups + mandatory pinned pretable completed: E2 `/srv/opentallas-scratch3/claude/fable-fix-qc-knee-hc/gates/r8_s29q103S4Q9MBR_BOOTSTRAP_DIAGNOSTIC_1116.json`, SHA027d6945bc91b9b56608dc91d18932ac757cce3cdb8f69df914bb77edcf470be. Sibling diagnostic.json qualified=false.

PARAM_REGEN cause: native clock landing gives core->face21 all ports, returns north20/south19. Existing plan has no collective bidirectional latency groups; coll_regen requires one R per port and aborts before all head/sc/fabric parameter regen. Proposed real native bus-group padding (not calendar relabel): north group TXs0/RXs0/fltk/fltv; south TXs1/TXs2/RXs1/RXs2/fltk/fltv. schema.bus_pads places north+1 and south+2 physical stages at coll_core return input buses; no new collective pad-site conflicts. Exact diagnostic plan/receipt E2 knee-hc/gates/coll_calendar_MBR_diagnostic_1116/. Parent composer owns final adoption and latency/CA regen.

Actual minimum callback diagnostic (Binder through regen_params only, fresh R8 plus proposed groups, no emit/typecheck/credit) intel2 client1786674, E2 unit oth-ubuntu-3371137-1794902896, log ~/fable-fix-qc-dieclk/m_bootstrap/callback.client.log; output callback_receipt.json in directory above. Preserve progressing job.

TYPE_SPLIT5 exact groups are failedBR bind_report.type_splits. Four existing SU bus_pad site conflicts persist independent of collective fix: W5su_l0 pad29 vs28; E0pad2 vs E1/E2pad1. Five reported type splits also contain true conns/OR-leaf differences; parent informed to materialize exact clones, preserving all clock selectors and CM/KP contracts. No shared source type edits made by this lane yet.

Healthy pilot2 PLACE completed23:42, advisory NEED-STATION14groups/25over405/464bitsover580 preserved. Existing watcher ROUTE started23:53 E8 unit oth-ubuntu-3164095-1794902020; log pilot2/chain_route.log. Actual planned/placedPDN images personally reviewed before route. Pilot L2+cbrows differs finalM and cannot release finalM. Optional sameDB NK bypass what-if is PARKED by parent; no implementation/job started.

### Correction / active next step, 00:15 PST
Parent directed NOT to materialize the five failed-BR type splits before a coherent diagnostic. Old stale-skip and capacity failures omit r8_sites and regen abort omits417 overrides; their raw body/signature differences may disappear. Scratch-only materialize helper/output exists but is PARKED/UNUSED; no shared source/plan clones were applied. Parent approved exact type-local ctlcl503337ff25 / slw_sc_v2 28 capacity fields for minimum diagnostic ONLY. Staged callback_sites.py will follow first actual regen callback, collect actual sites/CW/updated bus_groups + typecheck, and emit only five reported families. Final adoption still needs actual cost/source review; no old counts assumed after RS groups.
