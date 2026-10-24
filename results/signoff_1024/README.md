# Uniform re-signoff of closed blocks (lane SIGNOFF, 2026-10-24)

One sign-off recipe, `tools/die_plan/signoff.py`, applied to every block the 4 current die plans + B2 reference as
closed (s81, qwen_compute, qwen_kvsys, hbm P7, HBM-ARCH B2r2 on `claude/hbm-arch-1024` @3277b5e78b; s81_head as an
extra). Main at inventory time: 4b7b2b3e64.

## Result: 0 SIGNED, 0 NOT SIGNED, 137 NEEDS RE-RUN

The 137 unique closed modules (17,256 instances across the plans) were all routed on old-fleet hosts (ot-epyc4 51,
ot-agidock128 32, ot-epyc7 13, ot-epyc5 10, ot-epyc1tb 7, others). Those disks were wiped at 07:03 PDT. No live host
(localhost, epyc2, epyc3, intel1, intel2) has a `closure-loop` run dir, and git holds no routed ODB/DEF + netlist +
SPEF for any of them. The repo keeps their views (LEF + ETM libs) and records, not the routed databases. A block
can't be re-signed from an ETM, so every one of them is **NEEDS RE-RUN**. 117 of the 137 have their kit
(`physical/ref_tile/<kit>`) in the repo and can be re-run from what is committed. The other 20 have no kit in the repo
(views were copied into s81_die_views / closed_import, or the kits live on unmerged branches such as
`claude/a0-repack-1023`).

| die | closed modules | SIGNED | NOT SIGNED | NEEDS RE-RUN | of which the last record fails on paper | paper PASS | not-closed plan cores (not counted) |
|---|---|---|---|---|---|---|---|
| s81 | 37 | 0 | 0 | 37 | 29 (SS 29, spread 1) | 7 | 0 |
| qwen_compute | 21 | 0 | 0 | 21 | 16 (SS 16, spread 2) | 3 | 7 |
| qwen_kvsys | 20 | 0 | 0 | 20 | 9 (SS 9, spread 2) | 11 | 30 |
| hbm | 55 | 0 | 0 | 55 | 32 (SS 31, spread 2) | 23 | 189 |
| s81_head (extra) | 3 | 0 | 0 | 3 | 1 (SS 1) | 1 | 1 |
| hbm_b2r2 | 51 | 0 | 0 | 51 | 31 (SS 30, spread 2) | 20 | 192 |

### Paper screen of the last record

Each NEEDS RE-RUN block's last record is screened against the standard:
- recorded SS setup >= 0;
- recorded FF hold >= 0;
- recorded pin-flop spread at TT and FF <= 80 ps;
- DRC 0.

Of the 137 unique modules, **88 fail on paper**, 45 pass, 3 have no record and 1 is incomplete. A paper FAIL can't
be signed by re-running STA on the same layout; the block needs a re-close.

**SS setup is the main failure, and the records hide it.** 133 of the 134 closure_loop verdicts were accepted at
**TT setup** (`acceptance.setup_corner: TT`, OWNER 2026-10-08 rule "TT setup >= 0 / FF hold >= 0; SS sensitivity").
Their `metrics.ss_ps` field holds the TT slack, and the SS-library slack sits in `metrics.ss_sensitivity_ps`.
AGENTS.md (2026-09-30) requires SS setup for a headline clock, so these are TT closures. The inventory reports the
real SS value (`cl_ss_ps`) next to the closure corner value (`cl_setup_corner` / `cl_setup_ps`). Recorded SS runs from
-2,935 ps to +392 ps; 47 modules are SS-clean on record.

Seven modules also fail on recorded pin-flop spread:
- s81: `dsdv_gunit_l5` 101.9/95.3 ps;
- qwen_compute: `qfd_dv_lane_h_safe2` 82.4 TT, `qfd_dv_s8_station_tail1` 84.0/80.2;
- qwen_kvsys: `qkd_kvs_ctl` 121.8/109.3, `qkd_kvs_emb` 149.9 TT;
- hbm and B2: `ot_hbm_svc_pc_ctrl_leaf_cfg_h9b` 117.5/117.7, `ot_hgi_qdq_transport_rslice` 84.7/80.8.

A paper PASS is not a sign-off either. Those records predate the uniform boundary-hold standard and the sdc_lint /
face_guard gates. The ref_tile sign-off SDCs are Tcl programs (env-driven measured IO references), and sdc_lint's
fail-closed vocabulary rejects that form, so a re-close should use the die-plan kit SDC form.

Also note:
- the HBM P7 and B2r2 plans re-pin the closed hard cores onto new plan tracks. Even a recovered DB would not match the
  plan pins, so those blocks need a re-harden anyway;
- `dsdv_idx_tx_n32` has no SS liberty (only TT/FF).

Per-module tables: [per_die.md](per_die.md). Machine-readable: [summary.json](summary.json) (per die / module:
status, recorded numbers, recorded DB host:path, kit, paper screen) and [inventory.json](inventory.json) (from
`tools/die_plan/signoff_inventory.py`, including all 102 surviving run dirs on the live hosts).

## Routed runs that do exist: signed with the recipe (none is a plan-closed block)

The surviving routed runs with 6_final odb/spef are listed below. `dsdv_eng_rr_h0/h1` are the CORE-S81-ENG hard
cores, recovered from the old disk to intel1. The kv3 io partitions are KV-P6/P7 kits9 runs, recovered to intel2.
`col_h10_r1__t1` is a CP1-R10 r10a kit on epyc3, from before the fail-closed gates. All of them are pathfinding runs
on kits generated before 4b7b2b3e64.

| run | verdict | SS setup WNS (endpoints) | FF hold WNS std (raw SDC) | TT setup | pin-flop spread TT/FF | slew viol SS/FF/TT | sdc_lint | face_guard | DRC/antenna |
|---|---|---|---|---|---|---|---|---|---|
| col_h10_r1__t1_cp1r10 | NOT SIGNED | -462.44 (1153) | -45.74 (SDC +0.60) | -212.39 | 55.14/47.31 | 1791/1124/1278 | FAIL (2) | FAIL {'dropped': 120, 'feedthrough': 1, 'shared': 1} | 0/0 |
| dsdv_eng_rr_h0 | NOT SIGNED | -396.55 (5108) | -20.76 (SDC -6.27) | +8.05 | 36.58/29.16 | 34/0/0 | FAIL (2) | FAIL {'shared': 68} | 0/0 |
| dsdv_eng_rr_h1 | NOT SIGNED | -377.41 (4968) | -32.70 (SDC -6.41) | +13.90 | 54.9/47.91 | 16/0/0 | FAIL (2) | FAIL {'shared': 68} | 0/0 |
| kv3_io_cor_v1 | NOT SIGNED | -417.24 (4248) | -10.52 (SDC +5.83) | -132.68 | 40.54/33.65 | 6661/3364/4030 | FAIL (51) | PASS  | 0/0 |
| kv3_io_ft_v1 | NOT SIGNED | -346.22 (851) | -3.08 (SDC +8.56) | -55.95 | 30.49/24.16 | 1736/1364/1547 | FAIL (9) | PASS  | 0/0 |

Records: `runs/<name>/signoff.json` (+ per-corner `corner.json`, `session.tcl`, `sta.log.gz`).

Findings:
- **The TT-flow cores are not SS-signable.** eng_rr_h0/h1 close at TT (+8.05 / +13.90 ps, identical to ORFS's own
  `finish__timing__setup__ws` 8.04867 and hold 8.2728). This also calibrates the engine against the flow: 0.00 ps
  difference. At SS the same cores are -397 / -377 ps on ~5,000 endpoints. Every kit routed with `CORNER = TC` is
  pathfinding until it is re-closed at SS.
- **The uniform boundary-hold standard turns raw-SDC hold passes into FF hold fails.** The standard is min output
  delay 0 and min input delay -40 ps. Under it: kv3_io_ft +8.56 -> -3.08, kv3_io_cor +5.83 -> -10.52, CP1 col
  +0.60 -> -45.74. The raw SDC waived the sender seam hold, as COORD stated at 07:31.
- **The KV io partitions and the CP1 r10a column fail TT setup and carry thousands of max-transition violations**
  (320 ps limit, up to ~700 ps on placement buffers).
- face_guard on the CP1 r10a column: dropped 120, feedthrough 1, shared 1. This matches the CP1-R10 finding of
  136 dropped / merged. The eng_rr cores fail `shared` (68 input bits fan out to 16 loads: unregistered half-cycle
  `in_w` inputs).

## The recipe (`tools/die_plan/signoff.py`)

`signoff.py run --run-dir <ORFS run> --out DIR [--insertion-target 250]` reads the routed `6_final.odb` and its SPEF.
If there is no SPEF it re-extracts with OpenRCX (`rcx_patterns.rules`). The golden SDC is the kit's `constraint.sdc`.
It runs OpenSTA (OpenROAD in the pinned ORFS image) as one process per corner, in parallel: SS, FF, TT, with the
ASAP7 RVT/LVT/SLVT NLDM libraries of that corner plus the kit's macro libs per corner.

The verdict is SIGNED only if every blocking check PASSes. A check that could not run is NOT RUN, and that blocks:
- SS setup WNS >= 0;
- FF hold WNS >= 0 under the standard boundary-hold overlay (the raw-SDC hold is reported beside it);
- max transition and max capacitance violations = 0 at all corners;
- no unconstrained endpoints, unclocked registers or loops (`check_setup`);
- pin-flop clock spread <= 80 ps at TT and FF, plus insertion within +-40 ps of the target for die-plan partitions.
  Insertion and spread are measured on the active edge at every register, and on the pin flops (registers in the
  fan-out of data inputs or the fan-in of data outputs);
- `sdc_lint` on the SDC: kit `sdc_lint.json` when present, else a context derived from the SDC and the netlist ports
  (period 833, 60/25 ps uncertainty, insertion and tolerance);
- `face_guard` on the synthesized netlist with the kit pins;
- DRC = 0 and antenna violating nets = 0 from the route record.

Reported but not blocking:
- TT setup and hold (pathfinding);
- fanout over 64 (WARN; ASAP7 has no max_fanout);
- OCV: no derate in the verdict. The AGENTS.md 60/25 ps uncertainty is the project's OCV + jitter margin, and
  changing that needs an owner decision. A flat late 1.05 / early 0.95 derate is reported as `ocv5_*`, information
  only.

`signoff.py verdict DIR/signoff.json` re-evaluates a record. Tests: `tools/die_plan/test_signoff.py`.

Reproduce the summary:
`python3 tools/die_plan/signoff_inventory.py --out results/signoff_1024/inventory.json` (ssh scan of the 5 hosts), then
`python3 tools/die_plan/signoff_summary.py --inventory results/signoff_1024/inventory.json --runs results/signoff_1024/runs --out results/signoff_1024/summary.json --md results/signoff_1024/per_die.md`.
