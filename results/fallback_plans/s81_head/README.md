# s81_head — landed bottom-up FALLBACK PLAN (paper only, UNEXECUTED)

Lane FALLBACK-PLAN-PREP-2, written 2026-10-27 ~10:40 PDT. OWNER 10-27 ~08:1x approved fallback PLANS (no builds).
Trigger (OWNER 10-27 ~03:1x): at **2026-10-29 12:00 PDT**, if KV and QC do not both pass related-pair die STA, this plan
starts for HEAD in parallel with KV and S81, and top-down continues. Until then: **no builds, no kits, no ot-run.**
`launch_fallback.sh` is not executed. It refuses to run before T0, without `FALLBACK_TRIGGER=FIRED`, or without a COORD ruling id.

Labels: CHECKED = I recomputed or ran it in this lane. UNCHECKED = copied from a packet or estimated.

## 0 Status / sources (SHAs)

| Item | Source |
|---|---|
| Landed topology (consolidated, not redone) | Codex `codex/head-plan-0815@c9bd770f5` `results/head_fallback_prep_0815/{regions,compose}` (on GitHub; NOT on main) |
| Composed fallback plan | `compose/landed_portable.json` sha256 `1815d5ab203037b4…` (R17 adopted geometry, current HEAD providers, BQ=2, Native32 profile) |
| Tools (all on main `60b5ddf523`, CHECKED with `git merge-base`/`git cat-file`) | `tools/s81_head/fallback_land.py` (plan/compose/variant, `--monitor dataflow`, `--observer-spec`), `tools/die_plan/clock_landings.py`, `clock_landing_plan.py`, `gen_phys` key `clock.reserved_sites_um` + `tools/s81_head/fallback_reserve.py` (FALLBACK-HEAD-2/3; merged in ROOT-MERGE-24 `8404ea2f05`), `die_trial.py kit --htree-full-depth --tree-site-legal --tree-site-slide`, `die_infra.py grt`, `die_sta_related.py`, `kit_preflight.py`, `gen.py latency/rtl/phys`, `bind.py --strict` |
| Base plan of record | main `physical/die_plan/s81_head/die_plan.json` sha256 `d84d7778ce5f9db9…` (last change `2b67cdc6c3`, 10-27 07:43) |
| Lane history | `~/coord/lanes/FALLBACK-HEAD.md` (fd300/fs300/sl300 trees, monitor=dataflow, reserve tool), `~/coord/lanes/S81-HEAD.md` (R15/R16), Codex `handoff/codex-head-20261027-1013.md`, `handoff/codex_s81_head_20261027_1004.md` |
| HEAD RTL of record | HEAD-RTL-5 bind (main `262d070384`); R15 infra delta: HEAD_DIE_PORTBIND PASS, providers missing 4→0 (UNCHECKED here) |
| G0/G0C (this lane, diagnostic probe on intel2, MemoryMax 8 G) | `g0/` (see section 9a) |

The topology has not been re-derived. The Codex packet is on R17 geometry. The R18 owner (codex/head-tree-0830 successors) is still correcting the hard-core outlines and the clock build, so step S0 below re-runs the same recipe on the final R18 plan before adoption.

## 1 Region partition

- **Granularity = partition** (`fallback_land.py plan --granularity part`). Every one of the **326 partitions is its own clock region** (UNCHECKED packet; partition count CHECKED by G0C = 326). Die 17,521.92 × 17,556.48 µm = **307.6 mm²** (CHECKED from the plan outline).
- Types (16, all kept shared: **0 type splits**, 16→16, CHECKED from `compose_report.json`):

| Type | Inst | Outline µm | Plan cells (UNCHECKED, plan `cells`) | Hard cores inside |
|---|---|---|---|---|
| hd_tile | 264 | 708.48 × 1036.8 | 1,071,597 total, of which ~50 k glue (ASSUMED in plan) | 4 × elemA_cv + 1 × elemB_cv |
| hd_turn_a / hd_turn_b | 12 / 12 | 172.8 × 1036.8 | 2,000 | – |
| hd_spn / hd_spn_end | 5 / 1 | 1382.4 × 2073.6 | 60,000 | – |
| hd_serdes | 12 | 2885.76 × 1226.88 | 0 + PHY macro (VDDPHY domain) | ot_pdie_serdes (MODEL area) |
| hd_st_turn / st_str / st_n3 / st_n4 / st_m / st_k5 | 4/4/1/1/3/1 | 1442.88 × 1226.88 | 6k / 6k / 12k / 12k / 2k / 8k | – |
| hd_mesh | 3 | 1442.88 × 1226.88 | 140,000 | – |
| hd_lep0N | 1 | 1442.88 × 1226.88 | 365,489 | – |
| hd_ctl | 1 | 1442.88 × 1226.88 | 300,000 | – |
| hd_host | 1 | 1442.88 × 1226.88 | 200,000 | – |

- **Rejected alternative (qualitative, UNCHECKED, not recomposed here): rowpair granularity.** It is also emitted by `fallback_land.py plan --granularity rowpair`. It gives fewer crossings, but each region is a 2-row × ~17-mm strip, which breaks the landed-regions standard (a single tree across mm). The partition granularity is the one that meets the standard. Each region is ≤ 2.9 mm on its long side (hd_serdes), and the dominant hd_tile region is 0.71 × 1.04 mm.

## 2 Landed crossings + forwarded half-cycle hops

- **427 crossed ports / 211,813 bits** on **327 lanes**, with 1,708 new scalar pins (UNCHECKED packet; the 327-lane count is CHECKED, because G0 on the un-regenerated plan gives exactly 327 latency errors = 327 lanes).
- Each crossing = `ot_dp_clk_landing` with the existing LANDING-CONTRACT ring (fixed latency, no backpressure, 4-slot ring), **+3 cycles per crossing**, sink-side ring, forwarded-clock pins `fclk_out_<bus>` → `fclk_in_<bus>` + `landing_ready_i/landing_fault_i`.
- Lane added-cycle histogram (UNCHECKED packet): +3: 293 lanes, +6: 6, +9: 20, +15: 2, +21: 2, +27: 2, +30: 2.
- Live ring data FF **1,061,200** (CHECKED: the sum over the `requirements.json` cohorts of instances × FF = 1,061,200). Ring control FF upper bound 45,055 (UNCHECKED).
- Monitor = **dataflow** (`compose --monitor dataflow`). Status rides 2 spare bits of each data ring, so there is no type split: 1,281 infra edges, landing_contract **0 errors**, max hop 18.3 µm, **0 storage-band placement failures**, boot_ready max **327 cycles** (CHECKED from `compose_report.json`).
- **Forwarded half-cycle hops.** The long die lanes already carry plan-placed registered FT stations inside the ft frames (hd_st_*, hd_turn_*, hd_spn ft_slots) at ≤ 405 µm reach (12.1e). A station-to-station hop inside one region is synchronous to that region's local tree. Where a lane crosses a region boundary, the hop is the landed crossing above. The packet adds no new free-standing half-cycle relay. Base G0C has 2 WARN geometry entries (hd_host slots au/ad: ~1,335 µm > 3 stations × 405), and the fallback plan has the same 2. **Action S0b:** check those two hd_host FT slots carry ≥ 4 stations in the R18 plan, or else add one forwarded half-cycle hop per slot (the hd_host kit carries the station).

## 3 Per-region clock trees

- **Die level (die H-tree to region roots).** The base is the FALLBACK-HEAD **sl300** recipe: `die_trial.py kit --htree-full-depth --tree-site-legal --tree-site-slide --leaf-um 300`. Buffers slide along their own legs, so root→entry lengths are equal by construction. It is site-legal (0 cells on hard cores / PHY / outside a partition). History on the old geometry: 2,393 cells, die GRT 50 it overflow 0 TT+FF, landed |Δ| 212.4 TT / 188.4 FF vs P/2 = 416.5 (margin 204), GEOM-REVIEW-7 PASS as fallback geometry (all UNCHECKED, historical, **not a gate on the new plan**). The fd300 and fs300 trees are rejected on record (spread 607, margin 105).
- **R18 shapes.** sl300 was built on pre-R17 outlines. The tree is rebuilt on the final R18 plan (S2). Its `sites` feed `fallback_reserve.py` → `clock.reserved_sites_um`: tree rects become hard blockages, ring banks are GPL-only blockages. GEOM re-checks them against the final hard-core shapes: 0 on core, 0 in VDDPHY, ≤ 2 cells per 20-µm box, ring bank clear.
- **Region-local tree.** Each partition runs its own CTS from its plan-defined entry. For hd_tile the entry is the channel cross (354.24, 354.24) from INFRA-FIRST-HEAD-4, which feeds the 5 core entries `ft_mstrap_i`. The landed rings are clocked by the forwarded clock on the write side and by the local tree on the read side.
- **Hard cores (12.3 v5.0).** Hard cores keep their own signed/real-view insertion delay, annotated on the core clock pin as macro insertion-delay balancing (early taps allowed). Examples: elemA_eco R15 RCX TT 228.56 / FF 184.80 (CHECKED in R15 lane, not re-checked here). The core-internal tree is unshared and is charged by the AOCV table.
- **Gate (12.4a).** The gate is die GRT0 incl. clock (≥ 50 iterations) AND main `die_sta_related.py` with the shared model:
  - TT setup ≥ 0 and FF hold ≥ 0 on every related pair (intra-region, landed seam, die link);
  - CPPR to the last common tree node only;
  - `--clock-aocv-table` = the approved 0.21 %/mm table;
  - `--droop-region mesh`: differential droop is 0 inside one region; the full one-sided +5.1 % applies across regions until PDNSim;
  - data-path hold buffers allowed (12.4a a1);
  - landed seams judged with `--landing-window-ps` (P/2 = 416.5).
  Residual trims/pads only sparse and ledgered (12.8 d2).

## 4 Reused signed / closed views

| View | Status (evidence) | Fallback use |
|---|---|---|
| elemA (`ot_s81hd_elemA_cv`) | R15 `elemA_eco` **SIGNED view published**: routed LEC EQ 30203/30203, DRC/antenna 0, setup +122.36 / hold +4.43 (claude/head-r15-1027@feab2cd94e; CHECKED by R15, not by me). But main `471dd392b5` turned on `--core-view-match-pins` + pin-file content sha, so a view signed on an old pin file no longer counts until the plan pins match it. The current successors (R19, HM0, residual2) are **NOT SIGNED** (R19 FF −7.35, HM0 FF −8.86/199 ep); residual2 is LIVE on intel1 (repair-RCX FF +2.00). | Reuse as a hard macro inside hd_tile (no core rebuild in the fallback). Pick whichever view is signed at T0 and point the plan `cores/elemA_pins.json` at that view's own pins (v5.0 early tap: its own insertion). |
| elemB (`ot_s81hd_elemB_cv`) | **NOT SIGNED.** HM10 routed LEC EQ 27594/27594 but FF −8.27/19; HM0 FF −3.92/53; residual2 LIVE on epyc2 (repair-RCX FF +2.00) (Codex 10:13, UNCHECKED). | Same as elemA. A blocker if still unsigned at T0. |
| hd_turn_a / hd_turn_b | PROTO m5 routes (10-25) on old ports. Not valid after ring insertion. | Rebuild (ring added); the old kits are a recipe reference only. |
| PHY `ot_pdie_serdes` | MODEL area, no hardened whole-PHY view (shared S81 issue; FLOW/sta_pg owns the actual split). | Blocker shared with S81. |
| All other 13 partition types | No signed view | Build. |

Summary: **0 of 16 partition types reusable. The 2 hard-core types (1,320 instances) are reusable once signed.** The fallback's saving is that the hard cores are never rebuilt for latency or centre re-pinning (v5.0), and no die-wide balanced clock is needed.

## 5 Build list

Hosts: epyc2 / intel1 / intel2 only, via `ssh -o ControlPath=none intel2 ~/.local/bin/ot-run`; never epyc1. Each build is 1 type (replicas share the build). Cells = plan cells + ring FF + ring control (UNCHECKED estimate). Hard cores are macros, so their cells are not counted in the parent run.

| # | Type | Std cells est. (≤400k/run) | --mem GB | Basis for --mem | Depends |
|---|---|---|---|---|---|
| B1 | hd_tile | ~53 k glue+ring + 5 macros | 32 | elem kits 16–32 GB at 150–214 k cells (measured requests); macro-heavy tile | S3, elemA+elemB signed |
| B2,B3 | hd_turn_a, hd_turn_b | ~5 k | 24 | PROTO-KITS route ot-run 24 GB (10-25) | S3 |
| B4 | hd_spn | ~77 k | 24 | scaled from hd_turn/elem | S3 |
| B5 | hd_spn_end | ~74 k | 24 | " | S3 |
| B6 | hd_serdes | ~3 k + PHY macro | 16 | small | S3, PHY view |
| B7–B12 | hd_st_turn, st_str, st_n3, st_n4, st_m, st_k5 | 3–23 k | 16 | small ft frames | S3 |
| B13 | hd_mesh | ~146 k | 32 | elemB 164 k at 16–32 | S3 |
| B14 | hd_lep0N | **~382 k (4.5 % under the cap, watch)** | 48 | METHODOLOGY 5.4 32–48 GB ≤ 400 k | S3 |
| B15 | hd_ctl | ~317 k | 48 | " | S3, observer binding |
| B16 | hd_host | ~208 k | 40 | " | S3 |

Each build runs synth + LEC → G2 proto (place + GRT + STA) → AUTO GEOM (1-in-5 visual) → route → HB4 data-hold ECO (per-mode MCMM, R16 fix) → RCX → `signoff.py` → routed LEC → publish (AUTOPILOT-SIGNOFF chain). Then come the die jobs: tree kit (8 GB), die GRT incl. clock TT+FF (`--priority die`, 64 GB each, UNCHECKED — sl300 combined GRT ran on epyc1, no RSS recorded) and die_sta_related TT/FF (32 GB each, UNCHECKED). The memory for hd_lep0N/hd_ctl/hd_host is the methodology budget, not a measurement (UNCHECKED). The sizes are corrected from the first proto's measured RSS.

## 6 Area / latency ledger

| Item | Value | Label |
|---|---|---|
| Ring live data FF | 1,061,200 | CHECKED (sum of cohorts) |
| Ring area, FF-only (~0.30 µm²/FF) | 0.323 mm² = **0.105 %** of 307.6 mm² | CHECKED arithmetic; per-FF basis UNCHECKED |
| Ring area, 4.66 basis (FF + mux/control, logical, unmapped) | 0.987 mm² = **0.321 %** of die | CHECKED arithmetic; basis UNCHECKED |
| Mapped estimate (to confirm at first synth of hd_tile/hd_spn) | 0.3–1.0 mm², **< 1 % of die** (meets the < 1 % estimate) | UNCHECKED |
| Die tree cells (sl300 analogue) | ~2.4 k buffers, negligible area | UNCHECKED, historical |
| Outline change | none: rings fit in the existing outlines, 0 storage-band failures | CHECKED (compose_report) |
| Latency per head pass | **+171 cycles = 142.4 ns** at 833 ps. Breakdown: 37 head-pass crossings +111, plus the gather round trip +60 (worst one-way 10 crossings) | +171 UNCHECKED packet; ns CHECKED arithmetic |
| Token price | NOT COMPOSED (compose_tok_ds not re-run on this plan). Rough bound: if one head pass sits once on the AR token critical path, 142.4 ns / (1/784.9 tok/s = 1.274 ms) ≈ **0.011 %** AR. | UNCHECKED |
| Boot | ready ≤ 327 cycles, one-time | UNCHECKED packet |

## 7 Critical path to die GRT0 incl. clock + related-pair die STA

T0 = 2026-10-29 12:00 PDT. Wall-time estimates are UNCHECKED and assume the fleet is not saturated.

| Step | Work | Est. h | Starts after | Done by (est.) |
|---|---|---|---|---|
| S0 | COORD ruling id. Snapshot the final R18 plan; run `fallback_land.py plan --granularity part` + `compose --monitor dataflow --observer-spec <ctl actual>`; regenerate `gen.py latency --inplace`; G0/G0C = base error set; S0b hd_host au/ad stations. | 2 | T0 | 10-29 14:00 |
| S1 | **Binder ring emission on the native HEAD top** (`clock_landings` dataflow monitor into the generated top + reset nodes). Exact observer binding (hd_ctl `start_i` / `lep_fault_i` → ready/fault). 8-FT-port physical adapter on each A/B core in the physical parent. Then `bind.py --strict` PASS. | 8–10 | S0 | 10-29 22:00 |
| S2 | sl300-recipe die tree on R18 (`die_trial.py kit`) + `fallback_reserve.py` → reserved sites. GEOM auto check. (parallel with S1) | 3 | S0 | 10-29 17:00 |
| S3 | 16 kits: `gen.py rtl/phys` with rings + `clock.reserved_sites_um`, `kit_preflight.py` PASS, AUTO GEOM | 2 | S1, S2 | 10-30 00:00 |
| S4 | 16 builds in parallel (section 5). Longest are hd_lep0N / hd_ctl / hd_tile: synth+LEC 3, proto 2, route+HB4 ECO 8, RCX+signoff+routed LEC 4 | 17 | S3 | 10-30 17:00 |
| S4' | elemA/elemB signed (live residual2 chains; not part of the fallback) | – | already running | must be done before S4 hd_tile |
| S5 | ring-window STA per landed type (`clock_landing_verify`) | 1 | S4 | 10-30 18:00 |
| S6 | die GRT incl. clock, ≥ 50 it, TT+FF (`die_infra.py grt` on the combined tree + real abstracts) | 4 | S5 (a plan-view GRT can run early after S2 as a probe) | 10-30 22:00 |
| S7 | `die_sta_related.py` TT setup / FF hold, real views, approved AOCV, mesh droop region, hold-buffer fit; independent NUMBER-CHECK | 3 + 2 | S6 | **~10-31 03:00 PDT** |

Critical path ≈ 39–41 h, gated by S1 (tool code on the native top) and S4 (the hd_lep0N/hd_ctl builds). The largest schedule risk is S1. It is code plus tests, not a build. OWNER question Q1 asks whether it may be prepared before T0.

## 8 Top-down artefacts that carry over

- R17/R18 master plan: partition outlines and lattice, PG C3 grid (M8 0.48@4.32 / M9 6.48@34.56) and the 75-µm core bump decision (INFRA-FIRST-HEAD-4 recommendation; verify the owner ruling), VDDPHY domains/bumps, seal/reserve frames.
- FT stations / ft_slots in ft frames (12.1d pushdown), 405-µm reach, repeater bays, entry pins on M7.
- hd_tile channel-cross tap (354.24, 354.24) and the 1,387 declared clock slots / 177 declared ties (master_plan `--declared-slots`).
- Hard-core views, the in-core island pushdown and `ft_mstrap_i` entries (native 40-FT adapter, `codex/head-1027@1d54678770`, merged per root note).
- Reset wavefront and the qualified bootstrap buses (`codex/head-plan-0815@a480f95d1`, pending root adoption).
- HEAD-RTL-5 bind and source closure, the Native32 transport profile, HB4 strap LEC (264/264 EQ).
- Shared die timing model (`die_sta_related.py`, AOCV 0.21 %/mm, mesh MC tooling) and the AUTOPILOT/PREFLIGHT chain.
- Not carried: the die-wide balanced MSCTS mesh (replaced by region trees), and the core centre re-pin/latency rebuilds (v5.0 early taps instead).

## 9 Open blockers + owner questions

1. **Binder ring emission** on the native HEAD top: not implemented. `clock_landings` dataflow emitter exists; there is no hook into the generated HEAD top or reset nodes. (S1)
2. **Observer OPEN** (fails closed): the hd_ctl ready/fault ports must be bound exactly (`start_i` / `lep_fault_i` candidates) and pass `clock_landings` on the native body.
3. **8 new physical FT ports per A/B core**: the physical parent adapter is not built. The logical `.clk` provider does not prove the physical interface.
4. **R18 outline / PG site reservation**: the tree sites and ring banks must be re-reserved against the final R18 hard-core shapes and the HEAD5 PG. The Codex FT halo review is PASS_FACE_PLANNING_ONLY. 57 local drop/stack FAILs (38 no_clock_track, 19 no_pin_stack) remain on the top-down tree builder; the fallback region trees must avoid the same stack windows.
5. **elemA/elemB signed views** with matching pin files (match-pins ON).
6. **PHY real view** (shared with S81).
7. Token price NOT COMPOSED (compose_tok_ds on the S0 plan).

OWNER? Q1: may S1 (binder ring-emission code + tests, no builds) be prepared before T0? It is the critical-path item and would bring the die STA ETA forward by ~8–10 h.

### 9a G0/G0C (diagnostic probe, intel2, systemd-run MemoryMax 8 G, main `60b5ddf523` tools; logs in `g0/`)
- Base plan of record: **G0C PASS 0 errors / 6 warnings**, 16 types / 326 partitions (CHECKED, `g0/g0_base.log`).
- Packet `landed_portable.json` as committed: **G0C FAIL 327 errors**, all `[latency]` (table vs plan). There are exactly 327 errors for the 327 landed lanes, so the latency table was simply not regenerated (CHECKED, `g0/g0_fb_raw.log`).
- After `gen.py latency --inplace` (327 lanes regenerated): **G0C PASS 0 errors / 6 warnings**, the same warning set as the base (CHECKED, `g0/g0_fblat.log`, `g0/g0_fblat_report.json`; plan sha256 `4de57e0bfb52ab09…` on intel2 `/srv/opentallas-scratch2/claude/fallback-plans-1027/head_g0/src/results/head_fallback_prep_0815/compose/landed_portable_lat.json`). The latency regeneration is step S0 of the launch script.
