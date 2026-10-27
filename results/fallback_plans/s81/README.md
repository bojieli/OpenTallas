# S81 landed bottom-up FALLBACK PLAN (FALLBACK-PLAN-PREP-2, 2026-10-27)

PLAN ONLY. Nothing here was built, and no ot-run job, kit or P&R was started for it. The plan runs only if the
OWNER trigger fires at 2026-10-29 12:00 PDT: KV + QC related-pair die STA not passing means KV, S81 and HEAD fallbacks
start in parallel, and top-down continues. `launch_fallback.sh` is UNEXECUTED and refuses to run before then.

Labels: **CHECKED** = reproduced by this lane from the named file. **UNCHECKED** = taken from a lane/Codex report, or an
estimate.

## 0 Status / sources

| item | value |
|---|---|
| Base topology (not redone) | Codex `codex/s81-planprep-0908@79bebcc855` (hub intel2; parent 76047a897b). It holds results/fallback_s81_0908/{PREPARED.json, README.md, die_plan.json.gz, landed_sidecar.json.gz, svc13_candidate/} |
| Prepared plan (PD7f + fi2 + PHY metadata) | sha256 `9fdf967b6db88c90f1cb0ea0b8ad43c35bf6644f0fad03a33eff12d83953b936`; its sidecar is `6a0463922f33...6e4ede` (PREPARED.json) |
| svc13 candidate (last storage band fixed), the input to this plan | intel1:/srv/opentallas-scratch2/claude/codex-s81-pd14-0818/fallback_g2_svc13/die_plan.json sha256 `b80fac422de54cb4da53f66e3d4be54a69ad2f62b4d0d71e97735daa145b7d5d`; landed_sidecar.json sha256 `ee064670aef29c18a732b717dc88d74d2461191daaf2e422646a3a111ab2f50a` (CHECKED, sha256sum) |
| Older fallback lanes (history, failures kept) | claude/fallback-s81-1026@0773aa1237; claude/fallback-s81-2-1026@feca9a0d94 (v5.0 price, region trees, die GRT); claude/path-s81-pd-1026@10640a9b6a (thin-bank tool, GRT collect, landed-d FAIL); codex/s81-pd2-2000@875f1c86a (direct-partition PHY merge dde2c5466) |
| main at writing | 60b5ddf52 |
| State | PREPARED_NOT_FROZEN, physical_qualified=false. COORD adoption of svc13 as one S81 plan event is still pending |

## 1 Region partition

- The plan has 397 partitions and 245 types, on a 31.95 x 24.74 mm die (790.6 mm²). The partition outlines cover
  775.9 mm². CHECKED from die_plan.json.
- Regions are built with `fallback_regions.py --block 2 --mode class --core tap` (v5.0). That gives **169 regions**
  (CHECKED: distinct `tag` in sidecar.regions).
- Partitions per region: 36 x 1, 83 x 2, 9 x 3, 40 x 4, and 1 x 9 (CHECKED).
  - The 9-partition region is `hard_phy_hbm`, the hard PHY plus its port neighbours (merge_hard). Its bbox is
    11.3 x 3.68 mm (CHECKED). It is the one structural outlier; see section 3a.
  - The next largest regions are std_bg_0_0 / std_bg_3_0, 3 partitions at 2.89 x 4.91 mm each, and std_b3_9_0 at
    4.65 x 2.45 mm (CHECKED).
- Region figure: results/geom_review/codex_s81_0908 on the Codex branch. Status: BLOCKED for route, not a GEOM PASS.
  GEOM-REVIEW-9 gave a PASS-COND for the 10-26 region trees, with conditions (1)-(3) in lanes/FALLBACK-LAND.md.
- Rejected alternatives, kept as history:
  - partition mode: 391 regions, 1.08 M landed bits.
  - G=4: one PHY+svc region too large.
  - 2x2 svc groups: merge_hard pulls all 16 svc into an 11.5 x 6.1 mm PHY region (PATH-S81-PD).

## 2 Landed crossings + forwarded half-cycle hops

- **1,211 landed ports / 559,181 bits on 570 lanes** (CHECKED: sidecar.ports count, width sum, distinct lanes).
  - 1,155 data + 56 ctl ports (CHECKED).
  - Every crossing is std->std.
  - Max port width is 4,015 bits; 226 ports are wider than 1,000 bits (CHECKED).
- **Crossing hardware: `ot_dp_clk_landing`**, the existing main LANDING-CONTRACT.
  - It runs on a forwarded clock beside the bus: DEPTH4 / OFFSET2 / RDREG1 = **+3 cycles**, fixed static latency, no
    credits or backpressure.
  - The ring sits at the sink partition, inside a macro-free storage band.
  - Placement failures: **0** in the svc13 sidecar (CHECKED: collector.placement_failures = []). History of the count:
    126 -> 60 (grid scan) -> 22 (thin bank) -> 1 (PD7f) -> 0 (svc13).
- **Forwarded half-cycle hops.** The 288 fi lanes split into 144 direct 2-cycle lanes and 144 landed 5-cycle lanes,
  after fixing a prior double count (PREPARED.json fi_latency_census, UNCHECKED).
- **Long die lanes.** Existing ft stations / repeater bays are kept: <=405 um per registered hop (12.1e), repeaters
  <=450 um.
  - svc13 actual max hop is 404.383 um (UNCHECKED, Codex REPORT.json).
  - The `fwd` reading (ft stations on the lane's forwarded clock, so a lane lands once) needs new ft-slot tooling. It
    is NOT the plan of record; the plan prices the `face` reading.
- **Status / boot collector.** Root is seqhost, observer dsdv_hostb_dstat (vid_ri / alive_i).
  - 357 edges (CHECKED).
  - Reset release max 103 cycles, ring train max 21, ready-at-glue max 587 cycles; max die hop 377.98 um (CHECKED
    from sidecar.collector).
  - data_cycles_added = 0.
  - START is gated by real registered ready, never by the budget alone.

## 3 Per-region clock trees

**Structure (fallback, 12.8e1 says it is used only because the continuous mesh path failed its gate):**
1. Die reference H-tree on M8/M9 (NDR, shielded), from the die root at (15975.36, 12372.48) to one ROOT per region.
   - It need not be zero-skew: cross-region pairs are landed, and the landed window is |d| <= P/2 = 416.5 ps.
2. Inside each region, an equal-depth local tree from the region root to every partition clock entry. Built with
   `die_trial.py kit --region-trees regions.json --htree-full-depth --tree-site-slide --leaf-um 300 --rep-um 405`.
   - Every cell site is legal: 0 on cores, 0 in VDDPHY, 0 outside partitions (FALLBACK-HEAD sl300 recipe).
3. Below the partition entry: the partition's own CTS.
   - Hard cores are tapped EARLY by their signed/real-view insertion delay (12.3 v5.0, macro insertion-delay
     balancing). The unshared core-internal delay is charged by the AOCV table.
   - Modelled delta vs a 250-ps core: bf_col +7.7 TT / +5.8 FF, rom_elem +6.4 / +4.6, gunit +5.8 / +4.2, bk_sel
     +3.9 / +2.7 ps (MODEL, UNCHECKED).

**Measured failure to fix first.** FALLBACK-S81-2 die GRT incl. clock: overflow 0 on TT and FF, 539,404 nets, 50 it,
4.4 min per corner, max RSS 17.0 GB (RSS CHECKED from out_{TT,FF}/combo_*.log). But landed |d| FAILS: 135 TT / 85 FF of
1,199 crossings exceed 416.5 ps, max 1,868 ps (UNCHECKED, PATH-S81-PD). Root causes and the planned structural fixes
(principle first, 12.8 d2):

- **3a. The PHY region tree (depth 10) arrives ~2 ns late, 66 crossings.**
  - Fix part 1: the direct-partition PHY merge (dde2c5466, opt-in). Only partitions that drive INTO the PHY join it:
    8 members, 10.10 x 3.68 mm (PD2, UNCHECKED). The current sidecar still has 9 members at 11.3 x 3.68 mm (CHECKED),
    so the merge must be re-applied at T0.
  - Fix part 2: a plan-computed region trunk, so that every region-root -> entry path has the same stage count and
    the same predicted delay (12.8 d1 plan sizing, before build).
  - TOOL GAP: an equal-latency region trunk is not on main's die_trial.
- **3b. Region-root arrival spread is 640 TT / 567 FF ps.** Fix: an equal-length reference tree (`--tree-site-slide`,
  the sl300 construction). For HEAD, sl300 cut the landed |d| from 607 to 212 ps (UNCHECKED, FALLBACK-HEAD).
- **3c. Serdes lk_* legs are unrepeated (slew 980 ps).** Fix: repeaters <=405 um on every lk leg (`--rep-um 405`).
  Also carry Codex's actual-pin hop guard (codex/clock-leaf-slack-1027@bf342caf92), which reports the real repeater
  reach instead of the average-leg metric.
- **3d. Residual iqf<->svc_0 (699 ps).** Re-check it after 3a-3c. If it still fails, use a residual tool (sparse,
  logged in lanes/CLOCK-RESIDUAL.md).

**Gate (12.4a, shared model, no fork):**
- Die GRT0 incl. clock at >=50 it, TT + FF.
- Landed |d| <= 416.5 ps on every crossing (diagnostic before STA).
- main `die_sta_related.py` on related pairs: TT setup >= 0, FF hold >= 0.
  - CPPR to the last common tree node (region root for same-region pairs).
  - AOCV table (`--clock-aocv-table`, g = 0.21 %/mm) outside meshes; there is no mesh in this fallback.
  - Droop (`--droop-regions`): 0 differential inside one region/PDN region. Across regions the full one-sided +5.1 %
    applies until PDNSim gives the differential. This charge falls on landed crossings only, which have the P/2 window.
  - Data-path hold buffers are allowed (12.4a a1), with the count reported.

## 4 Reused signed/closed views

| class | count | fallback effect |
|---|---|---|
| Partition types | 245 | **233 change** (CHECKED). They are a sink ring and/or a source forwarded-clock export of a landed port: 231 types have landed inputs; the union with source types is 233. **12 are untouched** (CHECKED): 7 col_h9/h10 r2/r0_p6 clones, 3 ot_s81sl_leaf (t30_s_2N_L4, t54, t54_s_5N_L4), serdes t12 lk_WS3, and phy_hbm |
| Partition types SIGNED on current PD7f interfaces | 0 | Nothing is lost. S81-KITS-1 03:03: 4 kits, 94 blocked by landed SDC vs sdc_lint, 126 open-input (UNCHECKED). Codex 10:12: no new SIGNED view |
| Hard-core modules / instances | 52 / 18,993 (CHECKED) | **All reused unchanged.** v5.0 early taps mean no core rebuild for latency; rings live in partitions, never in cores. 7,644 are generated ROM macros (ot_rom_4096x72_m8) |
| Hard cores with SIGNED views today | few | qbank_N old routed SIGNED 137.99 / 11.84. H1 SIGNED TT 34.75 / FF 0.87 but not current-plan qualified (old W-face clock pin). hcpost was in the signed set 10-25 (15 of 100 then). All UNCHECKED, from lanes/S81-CORE-LAT.md and PATH-S81.md |
| PHY | 1 hard | The phy_hbm reservation is not a hardened whole-PHY macro. The real native parent is ot_pdie_serdes_col with 6 digital + 2 analog children (FLOW/sta_pg). It is a shared dependency with top-down |

Conclusion: the fallback **saves** the die-wide 12.8 clock structure (mesh plus all-core common latency). It does
**not** save the hard-core real views or the partition re-kits. Those are on the critical path of both methods.

## 5 Build list

Cell estimates:
- Glue cells come from cells_est.json (path-s81-taps-1026 src: Yosys-measured or band-share). Hard cores are excluded,
  since they are hardened separately.
- Ring cells = 6 per landed input bit (5 FF + 1 mux) on the worst instance of each type.
- Per-type rows: s81_type_build_est.json. All UNCHECKED estimates.

| family | types | inst | max est cells (glue+ring) | --mem GB | note |
|---|---|---|---|---|---|
| dsdv_slice_*_LP (4 types) | 4 | 4 | 381,846 / 376,829 / 368,963 / 199,850 | 64 | **near the 400k cap**. If synth exceeds 400k, the existing hard-core split is the plan (G0C), never one >400k run |
| svc_hi/lo_dsdv_svc_rs(_w), pvso_entry | 16 | 16 | 74-107k | 48 | the 15 svc are rebuilt once with ROWX=1 (same event) |
| dsdv_slice_*_C | 16 | 16 | 77-85k | 40 | |
| col_h9/h10 | ~64 | ~240 | 36-69k | 40 | 7 clone types untouched |
| ot_s81sl_leaf / kv_leaf | 80 | 80 | 38-44k | 40 | 3 untouched |
| slice_station | 45 | 45 | 38k | 32 | |
| serdes / gunit / iqf / eng / bk_sel / seqhost | 19 | 19 | 6-86k | 32-40 | eng / bk_sel cores already reach-fixed |
| die-level | | | | | |
| region-tree kit (die_trial kit) | 1 | | 31,550 tree cells (UNCHECKED, 10-26) | 32 | |
| combined die GRT incl. clock, TT+FF | 2 | | 539k nets | **24** (measured max RSS 17.0 GB CHECKED) | ~5 min/corner |
| strict bind | 1 | | 397 parts | **160** (v10 OOM'd at 40, measured) | |
| die STA related-pair TT/FF | 2 | | | 64 (UNCHECKED) | |

- Hosts: ot-run picks among **epyc2 / intel1 / intel2** (never epyc1).
- Fleet at writing: epyc2 admits 811 GB, intel1 562 GB, plus intel2 (CHECKED, `ot-run --status` 10-27 ~10:4x).
- That is room for ~30 kit routes in parallel at 40-64 GB.
- All kits go through kit_preflight.py, then autopilot (route -> RCX -> signoff.py -> routed LEC -> publish).

## 6 Area / latency ledger

| item | value |
|---|---|
| Ring storage | 2,795,905 ring FF = 5 x 559,181 bits (CHECKED arithmetic). At the svc13 band density (17,752.6 um² / 20,160 FF = 0.88 um²/FF) that reserves **~2.46 mm² = 0.31 % of the 790.6 mm² die** (UNCHECKED estimate; 10-26 G=2 unmapped 2.68 mm² / 0.34 %). Fits existing outlines: 0 outline growth, 0 storage FAIL (UNCHECKED) |
| Region trees | ~31.5k cells, wire 5.66 m (10-26 v5.0 kit, UNCHECKED). It replaces the die mesh |
| Added cycles | +3 per landed crossing (CHECKED). 570 lanes affected (CHECKED). Plan-regen lane table +4,083 lane cycles (UNCHECKED, 10-26 168-region plan) |
| Token price | **AR 766.4 (-2.36 %) / MTP 2,689.5 (-2.18 %) vs 784.9 / 2,749.3 per user: CHECKED** (PATH-S81-PD NUMBER-CHECK). It was on the 168-region / 1,199-port plan; the current 169 / 1,211 plan is NOT re-priced (UNCHECKED, expected within ~0.1 %). Recompose with compose_tok_ds at T0 |
| Ledger context | the TOK-DS ledger is at ~17.0 % (owner OK'd 17 %, 10-26). The fallback moves it to ~19.0-19.4 %, over the 15 %/design TARGET. The owner treats targets as non-limits (10-26), but this needs an explicit OWNER OK if the fallback wins |

## 7 Critical path to die GRT0 incl. clock + related-pair die STA (T0 = 2026-10-29 12:00 PDT)

| # | step | est. wall | depends |
|---|---|---|---|
| 1 | COORD ruling: adopt svc13 + the PHY direct merge + ROWX=1 as ONE S81 plan event; merge branch tools (thin bank 10640a9b6a, dde2c5466 merge, bf342caf92 hop guard) | 2 h | trigger |
| 2 | Region trunk equalisation code + tests (die_trial opt-in; tool gap 3a), predicted landed \|d\| before build | 4 h | 1 |
| 3 | Recompose landings (clock_landing_plan.compose), gen.py latency --inplace, G0/G0C, render + GEOM | 2 h | 1 |
| 4 | die_trial kit --region-trees + combined die GRT TT+FF (>=50 it) + landed \|d\| report; iterate <=3x | 6 h | 2, 3 |
| 5 | **Die GRT0 incl. clock** + landed \|d\| PASS (plan-level, budget views) | **T0 + ~14 h** | 4 |
| 6 | Strict bind (--mem 160) on the event plan | 3 h | 3 |
| 7 | gen.py rtl/phys for 233 types -> kit_preflight -> synth + LEC -> G2 -> autopilot route/signoff, ~30 in parallel, ~8 waves of the largest; LP types first | 36-48 h | 3, 6 |
| 8 | Hard-core real views (52 modules), shared with top-down | **gating; not shortened by the fallback** | |
| 9 | die_sta_related.py TT/FF on real views (shared model) + hold-buffer fit + NUMBER-CHECK | 4 h | 5, 7, 8 |
| | **Related-pair die STA on real views** | **T0 + ~60-72 h if step 8 is done by then** (UNCHECKED estimate) | |

## 8 Top-down artefacts that carry over

- **PG**: the die PG grid / bump plan and PG lots (PHY metadata 08a453f51c3, 14 inverse-orientation lot checks). Per
  region, PDNSim droop then replaces the one-sided +5.1 %.
- **Master-plan pieces kept**: partition lattice, outlines, ft stations / repeater bays at <=405 um, entry pins (M7),
  core lots, the reset wavefront (root s_4S_L3 / seqhost collector), and the latency table formulae.
- **Clock pieces kept**:
  - the die H-tree root and upper levels, re-used as the reference tree;
  - the in-core islands / centre entries already built into rebuilt cores (harmless, used as the core clock pin);
  - the AOCV table and die_sta_related shared model.
  - The continuous mesh is NOT used (fallback by definition).
- **Hard cores**: all 52 modules, including Codex's c18 / l0r / l1c / qx work, whatever is signed off by then.
- **Flow**: kit_preflight, autopilot sign-off chain, GEOM auto-pass, routed LEC, sdc_lint landed-SDC fix (blocker A
  of S81-KITS-1), and the strict-bind recipe.

## 9 Open blockers + owner questions

1. One S81 event adoption, covering svc13 band + PHY merge + ROWX=1 + QXPQ GB binding (COORD).
2. Tool gap: a plan-sized equal region trunk (3a). Without it the PHY region fails the landed |d| again (measured
   10-26).
3. The PHY real views (ot_pdie_serdes_col split) and hard-core real views gate the real-view STA in both methods.
4. sdc_lint vs landed SDC (94 kits blocked 10-27 03:03) must be fixed before any re-kit.
5. The 4 LP slice types are near the 400k cap.
6. Tool gap: die_sta_related.py reads a die_clock_mesh proof (tap_arrivals_<C>.json). The die_trial region-tree
   GRT arrivals (arr_<C>.txt) need an exporter to that format before stage E. It is a small adapter; there is no
   new timing model.
6b. Launcher TODO(T0) markers: the compose entry point, bind.py args, the corner combo tcl, and land_report_regions.py
   being on main. Fill them in from SRC_SHA before DRY_RUN=0.
6c. OWNER? The fallback adds ~2.2-2.4 % to the S81 ledger (~19 %); this needs an OK if the fallback wins.
7. G0 on the svc13 candidate: **G0C FAIL, 5 errors, 244 of 245 types clean** (CHECKED, `g0_result.txt` and
   `g0_report.json.gz`; main 60b5ddf52 tools).
   - 1 REAL error: the bk_sel u_tx origin y = 64.8 is off the 8.64 lattice (PD2 bk_tx64 move). Fix it in the event.
   - 1 known base cut: svc_1 h5000 1.02, PATH-S81-PD5 ASK 1, still unruled.
   - 3 probe artefacts: the s_2N_L1 track-supply fallback, plus 2 stale-census s_4N_x06 errors from the borrowed
     plan dir.
   - No landing, pin or schema errors.
