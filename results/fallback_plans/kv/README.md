# KV (qwen_kvsys) landed bottom-up FALLBACK PLAN — plan only, UNEXECUTED

Lane FALLBACK-PLAN-PREP-2 (OWNER 10-27 ~08:1x item 6: fallback PLANS, no builds). Trigger: 2026-10-29 12:00 PDT. If KV and QC
do not both pass related-pair die STA (TT setup and FF hold >= 0, real views, shared model, NUMBER-CHECKED), the fallback starts
for KV, S81 and HEAD in parallel, and top-down continues. Nothing in this directory has been run except the read-only probes
named in section 0. `launch_fallback.sh` is DRY-RUN by default and refuses to run before the trigger.

Labels: CHECKED = I reproduced the number from the cited file during this lane. UNCHECKED = taken from a packet or estimated.

## 0 Status / sources

| Item | Source |
|---|---|
| Region / crossing topology (consolidated, not redone) | Codex `codex/kv-clock-1027` @ d06cccbc4, `results/kv_fallback_prep_1027/` (row_groups_*.json, viewed PNG) |
| Plan of record used by that packet | R26 `38c1ed8519:results/clock_kv_r26/plan/hm_r26.json.gz` (sha256 568fc66e…), pins snapshot 517b37f88 |
| Older 8-region fallback (price + gate reference only) | `claude/fallback-kv-1026` `results/fallback_kv_1026/README.md` |
| Native reference | strict bind4 at 5c7c40d860: 160 partitions / 51 types / 0 strict errors (UNCHECKED, Codex) |
| Tools (all present on origin/main 60b5ddf523, CHECKED by `git cat-file`) | `fallback_regions.py`, `clock_landings.py`, `clock_landing_plan.py` (compose, monitor reset/dataflow), `die_trial.py kit --region-trees --htree-full-depth --tree-site-legal --tree-site-slide`, `check.py --completeness`, `gen.py rtl/phys/latency`, `bind.py`, `clock_landing_verify.py`, `die_sta_related.py` |

The top-down plan will move before T0: Codex event 3cb5395c6 / 68203aa54 (Q1 package, PV wide slice, KVSCTL) is pending adoption.
Step S1 of the launch script therefore regenerates every artefact here on the plan of record at T0. The numbers below are from R26.

Probe run in this lane (read-only, intel2, MemoryMax 24 G, main 60b5ddf523 tools, R26 plan + 517b37f88 pins):
`clock_landing_plan.compose` on the 128-group crossings. Codex had not composed this candidate.
Result **OK in 1,064 s** (CHECKED, `compose_probe.json`):
- types 51 -> 60 (9 landing-mask cohort splits);
- reset-mode collector root hub_C, 159 edges, max die hop 377.3 um;
- raw reset release 95 cycles, ring train 21, ready-at-glue max 388 cycles, 0 data cycles added at boot;
- **30 storage-band placement FAILs, all in kv3_pv_v7 / kv3_pv_v12.** These are the ft42..ft56 inputs: 15 per type, each
  needing a 47.52-um macro-free band. The fix is a PV FT band (plan delta) or the S81 thin-bank search; it belongs in S2/S3.

G0/G0C (`g0_probe.txt`, CHECKED by error-set diff):
- base R26: 11 errors, all missing cell estimates;
- landed: 20 errors = the same 11 + 9 of the same class for the 9 new cohort types;
- 0 new latency, landing, cut or reach errors after `gen.py latency --inplace`.

## 1 Region partition

- Die 11,076.48 x 27,043.2 um = 299.5 mm2, 160 partitions, 51 types (CHECKED from hm_r26.json).
- **128 local clock groups (CHECKED from row_groups_roots.json):**
  - 96 single-partition groups;
  - 32 two-partition groups, each = one hard PHY (`kv3_phy*`) plus its same-row PC (`kv3_pc*`).
  - Largest group: 2,160 x 1,676.16 um (hub_C). PHY+PC group: 1,900.8 x 1,520.64 um.
- Rule: the four wide mission buses between each hard PHY and its same-row PC stay synchronous, inside one group. Every other
  partition face lands. PHY reset/boot/fault (width 1) is not a mission bus; it lands too.
- Rejected, failures retained in the Codex packet (UNCHECKED, Codex):
  - all-160 partition-local: needs 5 landings per hard PHY, but the hard-wrapper collector supports 1;
  - stock merge-hard (96 groups): 17-partition / 13-mm vertical strips through the PHY reset chain, plus 30 unplaced bands.
- Figure viewed: `row_groups_regions.png` (copied here). It shows a regular 8-column grid, with PHY+PC pairs on both die edges and
  no long merged strips.
  - GEOM note: the existing soft clock entries (black dots) of `sys_*`, `io_*` and `hroot_*` sit on the region edge, not at the
    centre. The local-tree root is therefore re-sited to the region centroid (S4), or the root offset is accepted and shown in
    the tree report.

## 2 Landed crossings + forwarded half-cycle hops

- **3,595 landed ports / 519,111 bits** on 2,084 lanes (CHECKED, `row_groups_crossings.json` + `row_groups_requirements.json`).
- Each crossing = `ot_dp_clk_landing`: 4-slot ring, DEPTH4 / OFFSET2 / RDREG1, +3 cycles, fixed latency, no backpressure
  (lanes/LANDING-CONTRACT.md; static schedule rule 10-14).
- Added cycles per lane (CHECKED): +3 x 1,650 lanes, +6 x 115, +9 x 102, +12 x 75, +15 x 32, +18 x 16, +21 x 16, +24 x 30,
  +27 x 3, +30 x 23, +33 x 21, +39 x 1. Sum 10,785 lane-cycles. A lane crossing k faces pays 3k.
- The long multi-face lanes are FT chains through several partitions. Each partition FT station already registers the data
  (12.1d pushdown), so landing each face only adds the ring. Option to price at S1 (not chosen here): forwarded-clock FT
  (the source clock travels with the data, one landing at the far end) cuts +3k to +3. That needs FT-slot tooling that main
  does not have yet (same gap as S81 "fwd-FT").
- Forwarded half-cycle hops: inside a group, die-top FT hops keep the 405-um registered reach (12.1e) and repeaters <= 450 um.
  Group bounds (<= 2.16 x 1.68 mm) need no half-cycle hop. Half-cycle forwarding is used only where a lane crosses a group in
  one hop, as on S81; the R26 plan has none (all die lanes are partition-stationed).
- 32 PHY boot/reset landings (one per hard PHY, `row_groups_phy_reset.json`, CHECKED count) are hosted in the neighbouring PC
  digital wrapper, with registered <= 405-um delivery. The hard PHY is not reopened. The wavefront/START offsets grow by +3 per
  PHY hop in the boot chain (L668: hroot -> phy_*_7 -> ... -> phy_*_0, so up to 8 x 3 = +24 boot cycles; boot-only, not a token cost).
- Status/fault collector: reset-mode collector (main default), observer = hub_C sequencer `qkd_seq_core_static_s` (fault `hf`,
  ready `lp_run`), as in the Codex probe. It must be re-rooted for the 128 groups (S2).

## 3 Per-region clock trees

- Die clock in the fallback = **one short global distribution to 128 region roots + one local tree per group**. The regional mesh
  and full H-tree of R26 (32 x 71 mesh, 12,563 cells) are not needed for timing closure, because no synchronous pair crosses a group boundary.
  - The global distribution only has to deliver a clean edge to each root. Phase between groups is absorbed by the landing ring.
  - Landed phase budget: |d| <= P/2 = 416.5 ps, the FALLBACK-HEAD fd300/sl300 gate.
- Tool: `die_trial.py kit <landed_plan> --region-trees regions.json --htree-full-depth --tree-site-legal --tree-site-slide`.
  - This is the S81-2 / HEAD sl300 recipe: equal-length legs by sliding along their own legs, 0 cells on hard cores / PHY.
  - Fixes carried from the S81 GRT lesson (S81-2 landed |d| failed 135 TT / 85 FF: PHY region +2 ns late, root spread 640, lk slew 980):
    1. no region holds a whole PHY column. Here PHY+PC = 1.9 x 1.5 mm, so this is already met;
    2. equal root-leg lengths from the die root;
    3. 405-um repeaters on every global leg.
- Inside a group: single-root CTS per partition kit (the partition's own tree), from the plan entry. For the 32 PHY+PC groups,
  the PC kit tree also feeds the PHY digital interface pin.
  - Intra-group skew target <= 80 ps (design target, 12.4a). The 10-26 8-region probe found intra-partition FF spread
    > 80 ps in 11 partitions (sys_c 157, hub_C 136, pv_S_4..7 102-109; UNCHECKED). Single-root kit CTS replaces that stitched die tree.
- Hard cores: v5.0 early taps (12.3). Each core's insertion delay comes from its own signed/real view, and the partition tree taps it earlier
  by exactly that delay. Unshared core-internal delay is charged by the 12.4a b1 AOCV table (0.21 %/mm). No core is rebuilt for
  latency. In-core islands (12.2a1) stay in the cores; in the fallback their die-owned FT ports are tied to the partition tree,
  not to the die mesh.
- Gate model: unchanged and shared (OWNER 10-27, one model). `die_sta_related.py` on main runs with `--clock-aocv-table`,
  `--cppr-lca` (CPPR only to the last common tree node = region root for intra-group pairs), `--droop-regions` per group, and
  differential droop. Pairs in different groups never form a synchronous path, so the +5.1 % one-sided droop between regions
  does not enter a pair.
  - Landed crossings get the ring-window check (`--landing-window-ps`).
  - Data-path hold buffers are allowed (12.4a a1, `--hold-buffers`).

## 4 Reused signed / closed views

- **Hard cores (31 modules, 1,410 instances; CHECKED from plan):** shared with top-down. A view signed off for top-down carries over
  unchanged, because the fallback does not change core pins, outline, islands or latency contract.
  - Current state (UNCHECKED, from KV-CORES-R2/R3 and the Codex reset handoff 10:15): **0 of 24 in-scope core types has a usable signed view.**
  - e1/e5 were signed off, but their routed netlists are gone, so they need re-sign.
  - The cores remain on the critical path in BOTH plans. The fallback does not shorten it.
  - Live core work continues under KV-CORES / Codex children (E2/E6 final kits, Q2 LEC, PV R0 trial, KVSCTL preflight FAIL).
    The fallback adds no core job.
- **Hard PHY (`kv3_phy*`, 32 instances):** reused as-is (no ring inside; its boot landing moves to the PC).
- **Partitions (soft parents):** all 19 non-PHY families get rings at their landed faces, so every non-PHY partition type
  (47 types / 128 instances) needs a new kit.
  - No partition kit is signed off today (UNCHECKED). The fallback therefore replaces top-down partition kits; it does not throw
    signed ones away.
- Carry-over from top-down kits: outlines, core placement, pin files (r25/r26), PG (R4 dense), FT slots / bays, islands, entry
  pins, preflight/autopilot recipe.

## 5 Build list (after the trigger only; honest --mem; <= 400k cells per OpenROAD run; hosts epyc2 / intel1 / intel2, never epyc1)

| # | Build | Count | Cells per run (est.) | --mem GB | Depends |
|---|---|---|---|---|---|
| B0 | S1-S3 plan regen + compose + G0/G0C (python) | 1 | n/a | 24 | T0 plan of record |
| B1 | region trees `die_trial kit --region-trees` + render | 1 | ~10-20k tree cells | 32 | B0 |
| B2 | `gen.py rtl` + `gen.py phys` (landing RTL + kits, 47 types) + port-bind/strict bind | 1 | n/a | 48 | B0 |
| B3 | synth + LEC per partition type (yosys, cores as blackbox views) | 47 | glue + rings; rings <= 125k FF per type (hub_C padded upper; CHECKED from requirements) | 24 | B2 |
| B4 | partition P&R + sign-off (run_kit.sh / autopilot) | 47 | <= 400k each (G0C gate; see risk) | 48 | B3 + core views of that type |
| B5 | die GRT incl. clock (>= 50 it, TT + FF): die_trial `run_clock.sh` + `run_grt.sh` | 1 die | top only | clock 32 / GRT 256 (die_trial.py generator values, CHECKED in source) | B1 + B4 abstracts (stand-ins allowed for GRT) |
| B6 | die STA related pairs + ring windows (`die_sta_related.py`, real views) | 2 corners | n/a | 96 (UNCHECKED) | B4 SIGNED + B5 |
| B7 | token/latency compile (R8 + calendars, native bind) | 1 | n/a | 32 | B0 (in parallel) |

- Cell-cap risk (UNCHECKED L1 plan estimates, flattened minus replicated leaves): `kv3_sys_SD` 1.81 M (no hard core), `kv3_hub_C`
  0.81 M incl. ahub 397k, `kv3_pc*` ~0.8 M, `kv3_hub_Wi` 0.59 M, `kv3_hg*` 0.39 M glue + up to 30k ring FF.
  - These already need hard cores / G0C in top-down; the fallback inherits whatever top-down does.
  - Where glue + rings exceeds 400k, the ring banks of that type become one hardened landing-bank core per face (<= 125k FF, own kit). They are not added to the glue.
- Fleet capacity at 10:3x (CHECKED `ot-run --status`): epyc2 admits 782 GB, intel1 617 GB, intel2 606 GB. 47 x 48 GB = 2.26 TB, so
  B4 runs in about 2 waves.

## 6 Area / latency ledger

| Item | Value | Label |
|---|---|---|
| Live ring data FF | 2,613,530 | CHECKED (requirements) |
| Control FF (upper) | 306,071 | CHECKED |
| Padded data FF (upper) | 3,490,880 | CHECKED |
| DFFHQNx1 area | 0.2916 um2 | CHECKED (asap7sc7p5t_SEQ_RVT_TT lib) |
| Mapped ring area, x1.6 for mux/rd-reg/buffers | 1.36 mm2 (live) .. 1.77 mm2 (padded upper) | UNCHECKED factor |
| % of die (299.5 mm2) | **0.45-0.59 %** (earlier estimate "< 1 %" holds) | UNCHECKED |
| Clock: R26 mesh (12,563 cells) replaced by 128 local trees | roughly neutral | UNCHECKED |
| New scalar clock/status pins | 14,380 | CHECKED |
| Added latency | 2,084 lanes, +3 .. +39 cycles, 10,785 lane-cycles | CHECKED |
| Token price | **NOT COMPOSED** for 128 groups. Reference only: the 8-region fallback (10-26) priced Qwen ROM -0.36 % (K=3) / -0.66 % upper. 128 groups land about 3.6x more ports, so expect more; the price is per critical-chain lane, not the lane-cycle sum. B7 composes it. | UNCHECKED |

Qwen ledger context (10-26): 1.47 accepted + 7.12 proposed. The 15 % figure is a design target, not a limit (OWNER 10-26).

## 7 Critical path to die GRT0 incl. clock + related-pair die STA (from T0 = 2026-10-29 12:00 PDT)

| Step | What | Est. wall | Cumulative | Depends |
|---|---|---|---|---|
| S1 | regenerate groups + crossings on the T0 plan of record (`fallback_row_groups.py` recipe) | 0.5 h | T0+0.5 h | — |
| S2 | PHY boot landings hosted in PC wrappers (32), collector re-root, wavefront/START offsets | 4-6 h | T0+6 h | S1 |
| S3 | compose + G0/G0C 0 new errors + GEOM G1 of region/tree render | 2 h | T0+8 h | S2 |
| S4 | region trees (die_trial --region-trees ...) + tree_predict landed |d| <= 416.5 + GEOM | 2-3 h | T0+11 h | S3 |
| S5 | gen rtl/phys 47 kits + strict bind + preflight | 3-4 h | T0+15 h | S3 |
| S6 | synth + LEC (47, parallel) | 4-6 h | T0+21 h | S5 |
| S7 | partition P&R + RCX + sign-off (47, 2 waves), autopilot | 12-24 h | T0+33..45 h | S6 + core views |
| S8 | die GRT incl. clock >= 50 it TT+FF (stand-ins allowed from S5; rerun on S7 abstracts) | 4-6 h | T0+15 h (probe) / T0+51 h (final) | S4, S5/S7 |
| S9 | die STA related pairs + ring windows on real views, NUMBER-CHECK | 3-4 h | **T0+40..55 h ≈ 10-31 04:00-19:00 PDT** | S7, S8 |

- **The real critical path is the hard cores**, the same as top-down. S9 needs every core of every partition signed off. If KV
  cores are not all signed off by T0+30 h, S9 slips with them.
- What the fallback buys: no die-wide mesh/H-tree sign-off, no 8-mm unshared seam pairs, and no die-level hold fight across regions.
- Earliest useful signal: a die GRT incl. region trees plus a stand-in landed-window STA at about T0+16 h.

## 8 Top-down artefacts that carry over

PG grid (R4 dense, 150/75-um bump decision), partition outlines and lattice, hard-core placements, pin files r25/r26, entry pins,
in-core islands (tied to local trees), FT slots / repeater bays (405 um), reset wavefront tool, master-plan slices (kits still need
one; the fallback slice = master slice + ring storage bands), kit generator + PREFLIGHT + autopilot, die_sta_related shared
model + AOCV table, all core kits/views in flight.
Dropped: die mesh/H-tree build and its MC sign-off. They are kept as top-down artefacts; nothing is deleted.

## 9 Open blockers / owner questions

1. PHY boot hosting: 32 boot/reset landings move into the PC wrappers. Each needs exact pins, windows and netlist (S2).
2. Collector re-root + reset-mode collector for 128 groups. The `exactly one landing per hard wrapper` constraint is met by
   hosting in the PC (verify in S3).
3. Cell cap on sys_SD / hub_C / pc / hub_Wi: inherited from top-down (see section 5).
4. Token price for 128 groups not composed (B7). If it is materially above the 8-region reference, the owner chooses between the
   128-group plan and fewer, larger groups (e.g. 2 x 2 blocks).
5. compose probe on R26: OK, but 30 band FAILs on pv_v7/pv_v12 FT inputs, and types 51 -> 60. Both are fixed in S2/S3 (see section 0).

No owner policy change is requested. Section 12 is unchanged.
