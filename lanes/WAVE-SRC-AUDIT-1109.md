# WAVE-SRC-AUDIT 2026-11-09 (lane WAVE-SRC-AUDIT -> COORD, KW-FIX-43)

Method. Read every commit in WAVE-SRC-GAP-1109.tsv (179 distinct shas) from the real diffs (GitHub). For each die I read the
added lines of each changed kit-path file against the die's PINNED source (epyc7, snapshot ~21:00 PST 11-09): "absent" = under 25 %
of those lines present (usually 0); markers named below were grepped per die. Also read the die plans, wave item_env/gen_env, and
kit_wave_stages.tsv (2026-11-09 20:50, 112 FAIL rows plan_current). Failure-row matches are stated as measured or inferred.
Sources: s81 kw43t51/src_t51f; kv dkv97/src_zb; qc kw41/src_qcsw2; hbm kw41/src_hbmf4; head kw42/src_head_hp1.

Two scope corrections to the table the audit was given:
- TSV omits commits for files whose source blob is "local_unseen": gen_phys.py and landing_placement.tcl changed under the other dies
  often show for one die only. Fixes absent under this but missing from the TSV for that die are included below (e.g. 1940add62dc6 on
  QC, 82af67af on QC/KV/S81, TAPWIN gen_phys on all dies).
- 4aa8c234091c (the trigger): landing_collector.py now carries the fix in src_zb and src_t51f (file mtime 11-09 20:54 PST; KW-FIX-43
  overlay, 67/67 added lines present). The 69 built types still carry the defect; the source gap is closed.

Runtime overlays (not source-dependent, excluded): tools/autopilot (runtime); lec.py and kit_resume (future_lec hub overlay); eco_loop.py,
post_grt_chain.py, prd_mk.sh, prd_hook.tcl, eco_grt_pre.tcl (admission bundle bcc8881f..., which carries CLOCK_EDIT_HOOKS and eco_grt_pre:
measured), so 539f02, 53e79 eco_loop half, 29a806, 4b0987, b65a84, 8b22a8, 28e008 and a0490c are NOT source gaps.

## S81 (TSV 144 rows; matter 3 items / 4 commits; unsure 3; rest irrelevant)
| sha | effect | stage | re-bind / regen | plan event | failure class |
|---|---|---|---|---|---|
| 90b5279e4254 RESET-KEY | __cl clone kits get no reset_contract.json (kit_reset_contract has no reset_contract_member: marker 0), so LEC runs at the 4-edge default; commit counts 58 S81 clone types | gen (contract stage), LEC at place | regen, or kit_reset_contract `restage KIT --die s81` (LEC re-run, no rebuild) | no | serdes__t15__cla2127225 and serdes__t1__clb45db5be FAIL_PREFLOOR LEC NOT EQUIVALENT (inferred: both are clones) |
| 958a7d6d7fe3 legacy_gate | deep G2 setup miss at GRT stops the kit (FAIL_POSTCTS) instead of logging; S81 is the only die without it (measured) | route (GRT gate) | regen (legacy_gate.py copied into kit) | no | serdes__t14, serdes__t2 route TIMING 'G2 setup_tt failed before pair census' (exact symptom) |
| 1389515fc989 + c69786b37699 TAPWIN | kit SDC charges cross-tap pairs the full die band (window_ps 180); gen_phys has neither commit (marker 0). c69786b replaces the 40 ps default with S81 per_type_ps | gen (SDC), sign-off | regen after event | YES: TAPWIN-TYPE-1109 per_type_ps (event tool in repo at c69786b, not applied in the S81 plan: measured iqf__t1 has no per_type or per_port entry) | iqf__t1 signoff TT -123 FF -160 cross-tap (commit: 1390/2319 viol, ~10/~100 with window credited) |

Unsure (S81): 7c0931570526 signoff TT vclk rebind over early-core-tap clocks (setup_tt NOT RUN on station t51 vE; no current 'unavailable' row, but S81 stations will hit it at next sign-off) -- re-sign only; aa1420b04041/0b305f23952b/aa8acb1988ee/882f260cd295 landing_place gen moves (S81 already has the runtime macro-exit 1e34e1, t10 row predates it); 120eba390b45 core-kit max-wire (core kits only).

## KV (TSV 152 rows; matter 2; unsure 3; rest irrelevant)
| sha | effect | stage | re-bind / regen | plan event | failure class |
|---|---|---|---|---|---|
| 1940add62dc6 | cland_ffkey misses chunk-wire ring storage names dch[c].sd_c[k], so the START rekey moves all ring storage away from its read registers; marker absent in src_zb; kv3_hg_v1p3 netlist has 70368 sd_c names (measured) | place (landing_placement.tcl, kit copy) | regen / place-stage resume | no | kv3_hgi_v3 route GRT-0116 (commit's own case: 30448 gcells) |
| 90b5279e4254 RESET-KEY | as S81; KV has clone types | gen (contract) | regen or restage | no | defect class, no current KV LEC FAIL row |

Unsure (KV): 95df6810481e landing placement resize footprint (only KV lacks it; FIRM overlap class, no current row); 9db0ec8d71eb START-window grow + landing_place group (aa8acb/0b305f/882f/aa1420), no current KV place fail; 120eba390b45.

## QC (TSV 80 rows; matter 3; unsure 3; rest irrelevant)
| sha | effect | stage | re-bind / regen | plan event | failure class |
|---|---|---|---|---|---|
| 1940add62dc6 | as KV; absent in src_qcsw2 (not in TSV for QC: local_unseen). Measured sd_c/dch names in QC netlists: cbn_q11__cl5cc92dfe 16532, sle_sc_v3 70499 | place | regen / place resume | no | QC route GRT-0116 rows (8 current); sle_sc_v3 and cbn_q11 measured to carry the names; other rows inferred |
| 82af67af8f26 CONS-OVERMACRO-1 | conservative kits cut M7 to 10 % over SU lanes/SC core (signal ceiling below macro OBS + 2); commit names sle_su_l0/l1, slw_sc; absent in src_qcsw2 (marker 0) | gen (config), route | regen | no | CONS rows with GRT-0116 (item_env OT_CONS_KIT measured): sle_su_l1__cl5ea486db, slw_su_l0__cl1a1c1f8f, __cl1e5219ea, cbf_q11 |
| 90b5279e4254 RESET-KEY | as S81; most QC types are __cl clones | gen (contract) | regen or restage | no | defect class, no current QC LEC FAIL row |

Unsure (QC): 66c8ba930c16 off-window band relocation (plan-event tool, cbf_q00 class; needs a resize event); 1e34e1135a3d macro-exit runtime; 120eba390b45. QC 'no legal' place rows (cbn_q01 x2) are u_cland_fstart_rsf_o writer-face (measured message), not macro-exit: no absent commit explains them.

## HBM (TSV 90 rows; matter 4 items / 6 commits; unsure 2; rest irrelevant)
| sha | effect | stage | re-bind / regen | plan event | failure class |
|---|---|---|---|---|---|
| b2ae6c209fa8 + adbb61f05b68 + c2836b8f2596 hop latch | latches launched on a late tap move to the capture tap (OT_HOP_LATCH_CAPTURE_TAP, HBM default) with GRT hold padding; all three absent in src_hbmf4 (markers 0); ea77494498 FRAC present | CTS (clock_taps.tcl), GRT (grt_pre) | regen | no (plan relay_lockup latch types q_mca, q_spb1, q_spt1/2, vsN1..6 already there) | vsN1/vsN2/vsN4/vsN6/q_spb1 signoff TIMING: vsN2 TT -33.18 is the commit's own case (exact row match); others inferred |
| 4f7a78955d54 | PDN M6 macro-edge channels (PDN-0178/0179) closed; marker ot_ft_m7_ok 0 in src_hbmf4 | gen (PDN Tcl) | regen | no | q_b000, q_b000__physical_v1, q_b001__physical_v1, q_b101 place PDN-0179 (4 rows; origin q_b010/q_b000 class) |
| 090d37504b52 | no gap-column window on outline-edge columns, PDN memory 57 GB -> 13 GB on q_su20 (commit's measurement); marker 0 | gen (PDN Tcl) | regen | no | q_su20 place INFRA Error 247 do-2_4_floorplan_pdn (commit's own case); q_su11 |
| c15eb3676920 hold_margin_pick | 35 ps GRT FF hold target on hard cores >100k cells; not in gen_core_kit_hbm/run_kit_hbm of src_hbmf4 (measured) | GRT (core kits) | regen of core kits (core-kit gen) | no | big-core FF hold drift (commit: q3bc_SF1 33.6, q3bc_E2b 38.9 ps); current rows e.g. ot_hfd_coll_q2n2 post-CTS hold inferred |

Unsure (HBM): b3f0a3d9e1e4 relay_line pt_w conservative (needs gen_core_kit_hbm --relay-line, absent); 90b5279e4254 (HBM names mostly no __cl). HBM GRT-0116 (q_spu0 etc.): 1940add does not apply on sample q_spu0 (sd_c 0). q_su01 DRT-0073: plans have 0 clock_entry_access, so 6d92d957 does not explain it.

## HEAD (TSV 70 rows; matter 0; unsure 2; rest irrelevant)
HEAD has 2 FAIL rows (hd_ctl RSZ-0060, hd_host_e routed DRC 2); neither maps to an absent commit. Unsure: 82af67af8f26 applies only to hd_serdes (OT_CONS_KIT, measured); 1940add62dc6 (hd_ctl netlist has 41 sd_c names, small ring exposure).

## Counted irrelevant
All other rows: autopilot/kit_wave runtime, HBM-split/plan-event tools (ts_relay, qc_su, type_safe, hbm_split, bound_macro), other-die plan events and schema-only commits, kit_gen_lint/lazy-fetch, opt-in knobs no die sets (ft_polarity on KV/S81, OT_GUTTER, reset latch form), escaped-name fixes cb13e19342/422126acd1 (sampled QC/S81 core_taps/core_latency carry no bracketed names; HEAD/HBM generate-loop cases only).
