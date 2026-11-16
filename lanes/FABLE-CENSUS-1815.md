# FABLE-CENSUS-1815: every unsigned core and type on S81, HEAD, QC, KV (2026-11-15 18:16 PST snapshot)

Read-only census by FABLE-CENSUS-1815. HBM parked, not covered. Nothing launched, stopped, held or edited.
One row per open item: `lanes/CENSUS-1815.tsv` (538 rows = 5 cores + 533 types).
MEASURED = read by me (wave state 18:16, plan cache, kit files on build hosts, archive INDEX). REPORTED = lane post or Fable review.

## 0. Summary

Answer to "are the cores all closed, are all mismatches and missing files fixed": **no**. 5 cores and 533 types are open.
None of the 533 open types is blocked by a P&R result that nobody is working on; **477 of 533 (89 %) are held or failed
before placement**, on six causes. Three of the five open cores are already signed and archived and only the counter is missing.

| # | root-cause class | types | S81 | HEAD | QC | KV | the ONE fix | owner (alive?) | unblocks |
|---|---|---|---|---|---|---|---|---|---|
| 1 | waiting on plan event | 257 | 249 | 0 | 8 | 0 | S81 Event F part 2 for the col family (216); S81 G3/G3b for svc, leaf slot, t24, bk_sel (33); QC S4q7e / S4x (8) | DIE-S81-92 (yes), DIE-QC-103 (yes) | 257 |
| 2 | tool or source skew | 168 | 103 | 0 | 14 | 51 | S81: G3b drops the 59 remaining tap_offset tables, because the S81 tree's `gen_phys.py` writes a form its own `sdc_lint.py` cannot read (103). KV: tree rebuilt from one tools sha (51). QC: fixed 16:37, relaunched 18:17 (14) | DIE-S81-92 (yes), KV-102 (yes) | 168 |
| 3 | running, no result yet | 39 | 1 | 2 | 36 | 0 | none; 11 of the QC 36 are in families that stop with `DRT-0255` | KIT-OPS-5 | 0 |
| 4 | missing file / source | 34 | 1 | 0 | 33 | 0 | one QC source-closure pass (9 pruned HDL, 5 `ot_rst_relay`, 6 cland views, 4 `core_view_sha`, 4 kit not self-contained, 5 other) | **none alive** (WAVE-QCFIX-0715 silent since 08:11) | 33 |
| 5 | `DRT-0255` | 12 | 0 | 2 | 10 | 0 | proven PG form into the gen env (acts at floorplan) | DRT0255-PROOF-1115, GENBUG-IMPL (yes) | 12 now, 23 with the running QC families |
| 6 | hold (GRT hold repair stall) | 11 | 0 | 0 | 11 | 0 | hold-arm fix or station rows | **none alive** (QC-HOLDGRT-1 never posted) | 11 |
| 7 | setup < -150 | 6 | 0 | 2 | 4 | 0 | station / tap rows (HEAD NF12, QC S4x); not a repair class | HEAD-100, DIE-QC-103 (yes) | 6 |
| 8 | never launched / infra end | 5 | 0 | 0 | 5 | 0 | relaunch on S4Q3C | KIT-OPS-5 | 5 |
| 9 | setup -42..-150 | 1 | 0 | 1 | 0 | 0 | TT setup repair (hd_host_e -77.7 -> -31.7) | HEAD-100 | 1 |
| | sum | 533 | 354 | 7 | 121 | 51 | | | |

Classes with 0 open types as the present blocker: plan/prepare mismatch (HEAD, fixed 18:1x), overlay schema (S81 G1d, 0 types
directly, but it delayed class 2 by 3 h), DRC, congestion. The S81 col family is counted in class 1; its measured cause is
setup < -150 (22 col_h9 kits at -152 to -573, REPORTED FABLE-CLOSURE-1715).

State of the 533: HELD 464 (S81 348, QC 65, KV 51), RUNNING 44, relaunched after the snapshot 14, FAIL not held 10, other 1.

Top fixes by types unblocked:

| rank | fix | owner | types |
|---|---|---|---|
| 1 | S81 Event F part 2: per-port window + IFN 0 halves + ROM tap rows + col3_c pinwire view in one event, one col_h9_r0_p6 pilot to CTS first | DIE-S81-92 | 216 |
| 2 | S81 G3b: G3 + drop the 59 remaining non-col tap_offset tables, `sdc_lint` on the whole release list before ADOPT, wave src switched to B6gG3/src in the same release | DIE-S81-92 | 136 (103 + 33) |
| 3 | KV: `src_kv_kvgeom7u_c1` from one tools sha + pcc/pcf leaf sources; kit_rtl smoke on hg_v3 and pc_v1; lift the die `*` hold | KV-102 | 51 |
| 4 | QC source closure: one lane restages every missing input for S4Q3C, then lifts the three WAVE-QCFIX class holds | new lane QC-SRC-CLOSE (no live owner today) | 33 |
| 5 | `DRT-0255` PG form in the gen env of all four dies before the QC S4q7 and S81 G volume | DRT0255-PROOF-1115, GENBUG-IMPL | 12 failed + 11 running QC + every later route |
| 6 | QC hold stall: give the 15 FABLE-TRIAGE-QC hold keys a live owner | new lane or DIE-QC-103 | 11 |
| 7 | Counter: ingest the 3 archived QC n9 core records | FLOW-HEALTH-1 | 3 cores (QC 67/67), 0 build |

## 1. Open cores (5)

| die | core | why no row / no result | exact missing step | who |
|---|---|---|---|---|
| QC | sta_region_nb0_h17_n9_s10, h18_n9_s10, h18_n9_s11 | **Signed and archived, not counted.** MEASURED: `INDEX.tsv` rows 436-438 are ARCHIVED-BOTH (rtx-pro + AGIdock: 6_final.odb, signoff.json, LEC EQUIVALENT); CORE-ROWS-1115 built them as lane kits on epyc9 (`eco_q_h17_u5`, `q_h18a_u5`, `q_h18b_u5`), so no wave row is expected. The counter cache has 0 signed records naming these modules (only `kq_sta_region_nb0_synth0`), and the INDEX record column is empty, so the archive gate has nothing to credit. The three n6 masters had the same gap before S4q3c replaced them. | Ingest the three archived `signoff.json` into the signed store (`tools/signed_store_ingest.py`) or add epyc9 `core-rows-1115` to the scan roots; rerun `release_tree_plan.py`. INFERENCE: I did not trace the credit code path line by line. h17_n9_s10 has hold -1.42 ps on 2 input ports that the parent type must meet. | FLOW-HEALTH-1 (counter). CORE-ROWS-1115 is silent since 10:56. |
| S81 | dsdv_bksel_q | **Not running; two finished results unread.** MEASURED on epyc8 `core-bksel-1115`: b1o finished 15:05 PST, b1g 17:06 PST, each with 6_final.odb and signoff.json: DRC 0; setup TT -256.81 (215 endpoints) / -219.49 (243); hold FF -4.73 / -4.82; slew violations 1,905 / 1,763; `macro_libs: FAIL` because the FF corner reads `ot_s81ph_hq_pk2_tc.lib`; clock pair coverage NOT RUN (UNEXPANDED_CHILD_ETM); 814k-817k cells. The breakdown says "running, no result"; no container exists. Wave key `dsdv_bksel_q__v2467d3dbc120` has no row because every build was a lane kit. | Read and post the two results; bind the pk2 FF lib; Fable PD review of the 215 / 243 setup endpoints (6 CTS variants and 2 routed forms have failed; setup < -150 is not an ECO class; the cell count is twice the 400k guide). | New lane. CORE-BKSEL-1115 is silent since 12:0x. |
| S81 | dsdv_gunit_l1f_bf | **Near miss, no live job since 13:06.** g3f routed: DRC 0, TT -16.46, FF hold -42.0, drv 15. Late hold ECO failed three times (margin 5 at 09:44, margin 1 at 13:04, margin 2 at 13:06): `prd_result.json` route_rc 5, clk_check_rc 1 (detail route rewires frozen clock nets). The two 13:0x failures were never posted. No wave row: lane kit; wave key `dsdv_gunit_l1f_bf__v3a3277924b43` never launched. | Close the 42 ps FF hold before detail route (hold repair on the g3f 4_cts / 5_1_grt database, non-port scope) and route once, then sign-off, archive, counter. A fourth post-route ECO is the same failure. | New lane + Fable read. CORE-ROWS-1115 silent since 10:56. |

## 2. Open types per die (rows in the TSV)

### S81: 354 open of 394 (HELD 348, RUNNING 2, FAIL 3, advisory 1)

| family | types | state | last attempt | class | releases on |
|---|---|---|---|---|---|
| col_h9 (180), col_h10 (36) | 216 | held, 2 keys each | SUPERSEDED / DEDUP / CANCELLED rows on old events; the 22 newest col_h9 kits stopped at the post-CTS gate, TT setup -152 to -573 (REPORTED) | waiting on plan event (cause: setup < -150 on the element face, flat 208 ps window, ROM tap, reset removal, Lef58EolKeepOut on the col abstract) | Event F part 2 + col3_c pinwire view |
| ot_s81sl_leaf (61), serdes (10), dsdv_slice_* (19), kv_leaf (5), slice_station (4), gunit, eng, iqf, seqhost | 103 | held by list | 78 rows still show the 14:0x `--src-tree` kit_rtl error (fixed 16:37, never relaunched because the list hold came first); 10 show `sdc_lint` "clock window outside plan clock.tap_window" at gen | tool or source skew | G1d was the release; its gate failed at 15:36 (bind overlay without the BANDTAP schema keys, plus a cleaned `hard_params.json`) and was read at ~17:0x. Now G1db / G3 binding; FABLE-PD-S81-1750 measured that G3's release list still fails `sdc_lint` (slice_station__t8 53 errors, t45 16, serdes__t4 43) until G3b |
| svc_hi / svc_lo (16), leaf y-slot / x-slot (14), slice_station__t24, bk_sel__t2, lepe_mu_LP__t2 | 33 | held | old-event rows, RETRY-INFRA at place | waiting on plan event | G3 / G3b (BANDTAP v4, PHYT1 rows, t14 form R; svc needs the memory-macro synthesis option) |
| serdes__t12, ot_s81sl_leaf__t27 | 2 | running route | - | running | gate read |
| slice_station__t51 | 1 | advisory | waits on child core `s81p_slice_station__t51_ot_s81_station_t51_native_w` (no routed view; WAIT-CHILD posted every 20 min) | missing file / source | nobody owns the child core build |
| slice_station__t52 and 2 others | 3 | FAIL / restaged | waiter never started | tool or source skew | relaunch after G3b |

### HEAD: 7 open of 26 (6 running on NF12 since ~17:55, 1 failed)

| type | state | last result | class | fix |
|---|---|---|---|---|
| hd_ctl | FAIL route | `DRT-0255` net b_i[...] | DRT-0255 | PG form; proof p_hd_ctl in placement at 17:30 |
| hd_spn | running route, held after | previous kit `DRT-0255`, setup -145 | DRT-0255 | proof p_hd_spn in route |
| hd_serdes | running place | 17:42 gate setup_est -217, hold_est -120 on the NF6 kit | setup < -150 | RTL fan-out tree for pma_rck (HEAD-SERDES-1115); tap-group proxy reaches -69 on GRT RC, not -42 |
| hd_host_w | running place | -198 before NF11 / NF12 | setup < -150 | NF12 40-tap per-port window; first read at its gate |
| hd_host_e | running place | -77.7 -> -31.7 with the TT repair | setup -42..-150 | NF11 early tap + repair |
| hd_mesh, hd_lep0N | running route | - | running | gate read |

### QC: 121 open of 127 (HELD 65, RUNNING 36, relaunched 18:17 14, FAIL 6)

| group | types | class | evidence | owner |
|---|---|---|---|---|
| running (cb 15 incl. relaunches, sc, stm, su_l0/l1, glue, native59, others) | 36 | running | 30 in route, 3 in place, 3 in gen / kit_rtl; 11 are in the DRT-0255 hold families | KIT-OPS-5 |
| pruned HDL: slw_fw_v3, coll_ucie, sle_st_b_v1 x1, others | 9 | missing source | `bind: ERROR preferred HDL source missing: .../die-qc-103/treeA/physical/qwen_missi...` on events S4K to S4P | none alive |
| hc0 / hc1 / hc2 GEN_LINT | 5 | missing source | `Module \ot_rst_relay referenced in \qfd_dv_s5_xhead3 is not part of the design` | none alive |
| sle_ctl x6 | 6 | missing file | 4: INFRA-VIEW-MISSING `sle_cland_w517_n_s10_1` under epyc10 `die-qc-103/rk2`; 2: KIT_NOT_SELF_CONTAINED `rk2/sle_cland_w2104_s_s34/.../signoff.json` | none alive |
| slw_fe_v1 / v2 x4 | 4 | missing source | gen `ModuleNotFoundError: No module named 'core_view_sha'` (S3R rows) | none alive |
| st_a_v1 x6, sle_su_c, sle_stm_v3, st_a_v2 x1 | 9 | missing file / source | prov_view input not staged (FileNotFoundError), leaf modules without a source (`qfd_dv_s8_vm8q_rp1_*`, `qfd_dv_s5_stm_se*`), param_wrap port table (fixed 16:56) | none alive |
| cb / sc / fe `--src-tree` rows | 14 | tool skew, fixed | failed 11:33-13:13, fix merged 16:37, relaunched 18:17-18:20 on S4Q3C | KIT-OPS-5 |
| hc0, st_b, su_l1, fe_v1, coll_n, sc_v1 | 10 | DRT-0255 | Maze Route error in the 1st iteration | DRT0255-PROOF-1115 |
| hold-stall keys (hc3 x2, stm_v1 x4, stm_v2 x2, st_b_v1, fe_v1, fw_v1) | 11 | hold | GRT hold repair > 3 h, same numbers per attempt; key waits on QC-HOLDGRT-1 | none alive |
| sle_sc_v3, tt_ctlm, sle_st_b_v2, sle_fw_v2 | 4 | setup < -150 | SETUP_TRIAGE at the gate | DIE-QC-103 (S4x stations) |
| su_c x2, hc1, hc2, sc_v1, su_l1, st_b_v1, coll_ft__cl78c7b300 | 8 | waiting on plan event | S4q6b and S4q7c rebinds failed with 2 errors (sc reset rows withdrawn 18:00); coll_ft is held "until the counter lists it" | DIE-QC-103 |
| infra end (disk floor on intel1, restaged waiter, exit 137, place RC 0 without odb) | 5 | never launched / over-hold | not a design result | KIT-OPS-5 |

### KV: 51 open of 56 (all HELD by the die `*` hold since 17:35)

All 51: tool or source skew. `src_kv_kvgeom7u` is a per-file overlay stack: `gen_phys.py` calls `core_tap_early_ps` with 4
arguments, the tree's `schema.py` takes 3; `reset_tree.py` has no `pin_root_copies`; `qkd_kvs_pcc` / `pcf` leaf sources are
missing; 73 of 227 gen/bind modules differ from main (FLOW-HEALTH 18:07). 24 launches, 24 kit_rtl failures, 0 placements on
7u. KV-102 started the one-sha rebuild at 18:10. Behind that hold, per type (TSV fix column): hg / hgi / pv 34 types were
at -150 to -400 placed on kvgeom6 and have never built on a stationed plan; io_cor x2 and hroot stop with `DRT-0255`;
kv3_hub_C has a provisional qkd_ahub view whose lib sha differs from the signed view; kv3_pc_v3 fails a bound R8 strap
declaration; kv3_hub_Wi waits on child cores qkd_hr_core_order / peer. kv3_io_ft_v1 shows SIGNED in the wave (10:53) and is
not in the count: archive step missing.

## 3. Mismatches and missing files across the fleet

| # | what | where | state 18:30 |
|---|---|---|---|
| 1 | Wave plan is not the plan on origin/main, on all four dies | S81 1510a6a72050 (B6gE), HEAD 129319e1cb0b (NF12), QC 4675caa7e8e2 (S4q3c), KV b7156937f334 (7u); the counter counts the wave plan, main holds older events | open; no plan event of today is merged to main |
| 2 | Die src trees differ from main in the gen/bind closure (227 modules) | S81 B6gE/src 63, KV src_kv_kvgeom7u 73, HEAD src_head_rp21z_pgcaplec_c327 42, QC wt/qc-s29-tree2 36; cross-host copies identical (0 differ) | open; this is the source of every "tool skew" class today |
| 3 | S81 tree inconsistent in itself | `gen_phys.py` with the per-port offsets form, `sdc_lint.py` without it: 56 gen failures 15:45-17:45 | open until G3b |
| 4 | KV tree inconsistent in itself | see KV above | rebuild started 18:10 |
| 5 | Bind overlay without new schema keys | S81 `ovl_b6E` lacked `band_fixed_um` / `band_tap_windows_um`: G1d G0 17 errors at 15:36, read ~17:0x | fixed in ovl_b6G / ovl_b6G3 (8 keys); G1db and G3 still binding |
| 6 | Plan inputs removed by cleanup or sync | `col_h9_l4_lp_kit_vg_romq_split.hard_params.json` (ELAB_RC 1); 4 `ev/B6gG1d*` files on epyc10 by `rsync --delete` | restored |
| 7 | Prepared plan vs plan | HEAD `wave_prepare.json` 0c1bce11e10f vs plan 129319e1cb0b after NF10-NF12 | fixed 18:1x (KIT-OPS-5 `wave_prepare_refresh.py`); 3 NF12 rows passed kit_rtl |
| 8 | QC kit inputs missing | 33 types, section 2 QC; the holds are "until class proven past its step" with no lane to prove it | open, unowned |
| 9 | FF corner bound to a TT lib | dsdv_bksel_q b1o / b1g: `ot_s81ph_hq_pk2_tc.lib (ff)` | open, unread |
| 10 | Signed but not counted | 3 QC n9 cores (archived both); kv3_io_ft_v1 (wave SIGNED 10:53) | open |
| 11 | Child core views missing | S81 `s81p_slice_station__t51_..._native_w`; KV `qkd_hr_core_order`, `qkd_hr_core_peer`, `qkd_kvs_pcc`, `qkd_kvs_pcf`; QC `qfd_dv_s8x_btab`, `qfd_dv_s8x_prog` (su_c) | open; WAIT-CHILD posts go to dead lanes (item 13) |
| 12 | Holds past or without a release path | QC: 16 types on WAVE-QCFIX-0715 class holds (lane silent since 08:11); 15 keys wait on QC-HOLDGRT-1 (never posted); coll_ft__cl78c7b300 "until the counter lists it" (it does not). KV: kv3_hgi_v5 "release on the current event" (7u is current; masked by `*`). S81: each of 216 col types carries 2 keys | open; WAVE-HOLDS-1115 lifted 11 KV keys at 18:21 |
| 13 | Wave owner labels name dead lanes | kit_wave.json owner_lane: S81 "DIE-S81-90", QC "DIE-QC-101", KV "KV-101", HEAD "HEAD-98"; every KIT-WAVE failure line is addressed to them. Live owners are DIE-S81-92, DIE-QC-103, KV-102, HEAD-100 | open; this is why STALE reads 189 unowned on S81 |
| 14 | Fixed tool error not relaunched | QC 14 rows sat FAILED 4.5-6.5 h; fix merged 16:37, relaunch 18:17. S81 78 rows keep the `--src-tree` text as their last row | QC closed; S81 behind G3b |
| 15 | ot-run installed vs main | REPORTED merged 16:52 (r188) and rolled; I did not find a SAME line in FLOW-HEALTH.tsv | not verified |

## 4. Lanes that own open items and are not alive

CORE-BKSEL-1115 (last post 12:0x; 2 unread results), CORE-ROWS-1115 (10:56; 2 unreported ECO failures, 3 uncounted cores),
WAVE-QCFIX-0715 (08:11; 16 held QC types), QC-HOLDGRT-1 (never posted; 15 hold keys), FAIL-S81-1 (11-14), DIE-S81-90,
DIE-QC-101, DIE-QC-97, KV-101, DIE-KV-97, HEAD-98 (named in wave config and STALE.tsv, no posts today).

## 5. Method and limits

- Open list = plan_types of the wave plan in the release-tree cache minus signed_types; row = latest kit_wave_stages row
  with plan_current != no; hold = fnmatch of the item against dies.<die>.hold_items; all at 18:16 PST.
- Class = what blocks the item now (hold reason first, then last error). A held type's P&R result on the next event is
  unknown; rows 1-3 of the fix table unblock launches, they do not sign types. FABLE-CLOSURE-1715 measured the P&R classes
  on the 86 types that have kits: `DRT-0255` 24, setup < -150 31, TT repair alone 2.
- Not checked: per-host presence of each staged file for S81 / HEAD; ot-run drift; the counter's credit path for the n9
  cores (stated as inference). I did not open any database or run STA.
