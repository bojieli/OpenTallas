# Uniform re-signoff of closed blocks (lane SIGNOFF, 2026-10-24)

This applies one sign-off recipe, `tools/die_plan/signoff.py`, to every block that the 4 current die plans + B2
reference as closed. The plans are s81, qwen_compute, qwen_kvsys, hbm P7 and HBM-ARCH B2r2 (on
`claude/hbm-arch-1024` @3277b5e78b), with s81_head as an extra.

**Corner rule** (owner, restated 2026-10-24, AGENTS.md c7ce2ed69a): timing closes at the typical corner.
- Setup is checked at TT and hold at FF, with 60 ps setup / 25 ps hold uncertainty and pin-flop spread <= 80 ps.
- SS is reported for information only and never gates.
- The first version of this page (main 0f5176689d) gated on SS. It is superseded. Its run verdicts are kept as
  `runs/*/signoff.ss_rule_superseded.json`.

## Result: 0 SIGNED, 0 NOT SIGNED, 138 NEEDS RE-RUN

The 138 unique closed modules were all routed on old-fleet hosts (ot-epyc4, ot-agidock128, ot-epyc7,
ot-epyc5, ot-epyc1tb, ...). Those disks were wiped at 07:03 PDT:
- no live host (localhost, epyc2, epyc3, intel1, intel2) has a `closure-loop` run dir;
- git holds no routed ODB/DEF + netlist + SPEF for any of them. The repo keeps their views (LEF + ETM libs) and
  records only.

A block can't be re-signed from an ETM, so every one of them is **NEEDS RE-RUN**. Most have their kit
(`physical/ref_tile/<kit>`) in the repo and can be re-run from what is committed (see `kit_in_repo`).

| die | closed modules | SIGNED | NOT SIGNED | NEEDS RE-RUN | last record FAILS on paper | paper PASS | no / incomplete record | not-closed plan cores (not counted) |
|---|---|---|---|---|---|---|---|---|
| s81 | 37 | 0 | 0 | 37 | 1 | 35 | 1 | 0 |
| qwen_compute | 21 | 0 | 0 | 21 | 2 | 17 | 2 | 7 |
| qwen_kvsys | 20 | 0 | 0 | 20 | 2 | 18 | 0 | 30 |
| hbm | 55 | 0 | 0 | 55 | 2 | 51 | 2 | 189 |
| s81_head (extra) | 4 | 0 | 0 | 4 | 0 | 2 | 2 | 1 |
| hbm_b2r2 | 51 | 0 | 0 | 51 | 2 | 47 | 2 | 192 |

### Paper screen of the last record (TT rule)

Each NEEDS RE-RUN block's last record is screened against:
- recorded TT setup >= 0;
- FF hold >= 0;
- pin-flop spread at TT and FF <= 80 ps;
- DRC 0.

The TT setup value is the closure_loop verdict's `metrics.ss_ps`. That key is historical: under option B
(2026-10-07) it holds the TT setup slack, and `ss_sensitivity_ps` holds the SS slack. The inventory now names them
`cl_tt_setup_ps` and `cl_ss_info_ps`.

Of the unique modules, 124 pass on paper, 7 fail and 7 have no record or an incomplete one. **All 7 failures are
pin-flop spread > 80 ps.** These blocks are not die-bindable and need a re-close (clock), not only a re-STA:
- s81: `dsdv_gunit_l5` 101.9/95.3 ps;
- qwen_compute: `qfd_dv_lane_h_safe2` 82.4 TT, `qfd_dv_s8_station_tail1` 84.0/80.2;
- qwen_kvsys: `qkd_kvs_ctl` 121.8/109.3, `qkd_kvs_emb` 149.9 TT;
- hbm and B2: `ot_hbm_svc_pc_ctrl_leaf_cfg_h9b` 117.5/117.7, `ot_hgi_qdq_transport_rslice` 84.7/80.8.

No record:
- `dsdv_idx_tx_n32`;
- the A0 romleaf_rpf pair (kits on `claude/a0-repack-1023`);
- s81_head `ot_s81hd_elemA_cv` / `elemB_cv`.

No recorded spread: `ot_hgi_qw_dec`, `ot_hgi_sm_xload_cl2_bfqg`.

A paper PASS is still not a sign-off. Those records predate the uniform boundary-hold standard and the sdc_lint /
face_guard gates. The ref_tile sign-off SDCs are Tcl programs (env-driven measured IO references), and sdc_lint's
fail-closed vocabulary rejects that form, so a re-close should use the die-plan kit SDC form.

Also note:
- the HBM P7 and B2r2 plans re-pin the closed hard cores onto new plan tracks, so those blocks need a re-harden anyway;
- `dsdv_idx_tx_n32` has no SS liberty (information only now).

Per-module tables: [per_die.md](per_die.md). The recorded SS slack is in the last column, information only.
Machine-readable: [summary.json](summary.json) and [inventory.json](inventory.json). The inventory comes from
`tools/die_plan/signoff_inventory.py` and includes all surviving run dirs on the live hosts.

## Routed runs that do exist: signed with the recipe (none is a plan-closed block)

The surviving runs:
- `dsdv_eng_rr_h0/h1`: the CORE-S81-ENG hard cores, recovered to intel1;
- kv3 io partitions: KV-P6/P7 kits9 runs, recovered to intel2;
- `col_h10_r1__t1`: a CP1-R10 r10a kit on epyc3.

All are pathfinding runs on kits generated before 4b7b2b3e64. The verdicts below were re-evaluated under the TT rule
from the same STA sessions.

| run | verdict | TT setup WNS (endpoints) | FF hold WNS std (raw SDC) | pin-flop spread TT/FF | slew viol TT/FF | sdc_lint | face_guard | DRC/antenna | SS setup (info) |
|---|---|---|---|---|---|---|---|---|---|
| col_h10_r1__t1_cp1r10 | NOT SIGNED | -212.39 (274) | -45.74 (SDC +0.60) | 55.14/47.31 | 1278/1124 | FAIL (2) | FAIL {'dropped': 120, 'feedthrough': 1, 'shared': 1} | 0/0 | -462.44 |
| dsdv_eng_rr_h0 | NOT SIGNED | +8.05 (0) | -20.76 (SDC -6.27) | 36.58/29.16 | 0/0 | FAIL (2) | FAIL {'shared': 68} | 0/0 | -396.55 |
| dsdv_eng_rr_h1 | NOT SIGNED | +13.90 (0) | -32.70 (SDC -6.41) | 54.9/47.91 | 0/0 | FAIL (2) | FAIL {'shared': 68} | 0/0 | -377.41 |
| kv3_io_cor_v1 | NOT SIGNED | -132.68 (2525) | -10.52 (SDC +5.83) | 40.54/33.65 | 4030/3364 | FAIL (51) | PASS  | 0/0 | -417.24 |
| kv3_io_ft_v1 | NOT SIGNED | -55.95 (36) | -3.08 (SDC +8.56) | 30.49/24.16 | 1547/1364 | FAIL (9) | PASS  | 0/0 | -346.22 |

Records: `runs/<name>/signoff.json` (+ per-corner `corner.json`, `session.tcl`, `sta.log.gz`).

Findings:
- **eng_rr_h0/h1 close TT setup** (+8.05 / +13.90 ps). These are identical to ORFS's own `finish__timing__setup__ws`
  8.04867 and hold 8.2728, which calibrates the engine against the flow. They are NOT SIGNED for two reasons:
  - FF hold under the uniform boundary-hold standard (min output delay 0, min input delay -40 ps) is -20.76 / -32.70.
    Their raw SDC hold is already -6.3 / -6.4 at FF, because the flow repaired hold at TT only;
  - sdc_lint (old min delays) and face_guard (68 unregistered half-cycle `in_w` bits) fail.
- The KV io partitions and the CP1 r10a column fail TT setup (-56 / -133 / -212 ps). They also carry thousands of
  max-transition violations (320 ps limit) at TT and FF. The standard hold overlay flips their raw-SDC FF hold passes
  into fails.

## The recipe (`tools/die_plan/signoff.py`)

`signoff.py run --run-dir <ORFS run> --out DIR [--insertion-target 250] [--corners tt,ff[,ss]]` reads the routed
`6_final.odb` and its SPEF. If there is no SPEF it re-extracts with OpenRCX. The golden SDC is the kit's
`constraint.sdc`. It runs OpenSTA (OpenROAD in the pinned ORFS image) as one process per corner, in parallel.

The verdict is SIGNED only if every blocking check PASSes. A check that could not run is NOT RUN, and that blocks:
- **TT setup** WNS >= 0, with the SDC's 60 ps uncertainty;
- **FF hold** WNS >= 0 under the standard boundary-hold overlay (the raw-SDC hold is reported beside it);
- max transition and max capacitance violations = 0 at TT and FF;
- no unconstrained endpoints, unclocked registers or loops;
- pin-flop clock spread <= 80 ps at TT and FF, plus insertion within +-40 ps of the target for die-plan partitions;
- `sdc_lint`, which also checks the 60/25 ps uncertainty and the 833 ps period;
- `face_guard`;
- DRC = 0 and antenna = 0.

Reported but not blocking:
- SS (only with `--corners tt,ff,ss`);
- fanout over 64 (WARN);
- OCV: no derate in the verdict, because 60/25 ps is the project margin. `ocv5_*` is a flat late 1.05 / early 0.95
  derate, information only.

Other entry points:
- `signoff.py verdict DIR/signoff.json` re-evaluates a record;
- kits generated by `gen.py phys` run `signoff.py` as the final step of `run_kit.sh` (verdict in `KIT/signoff/`);
- tests: `tools/die_plan/test_signoff.py`.

Reproduce:
1. `python3 tools/die_plan/signoff_inventory.py --out results/signoff_1024/inventory.json`
2. `python3 tools/die_plan/signoff_summary.py --inventory results/signoff_1024/inventory.json --runs results/signoff_1024/runs --out results/signoff_1024/summary.json --md results/signoff_1024/per_die.md`
