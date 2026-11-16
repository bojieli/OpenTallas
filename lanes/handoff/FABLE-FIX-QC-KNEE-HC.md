# FABLE-FIX-QC-KNEE-HC handoff (owner: QC plan event S4q9b -> S4q9c, hc family, DRT-0255 rows)

Started 2026-11-16 05:46 PST. Lanes under my direction: QC-HCFE-O (hc proofs P0/P2), QC-PINACCESS-O (DRT-0255 proof watch).

## Root cause (MEASURED 06:00-07:00)
- S4q9b was NEVER bound. epyc2 chain on kw45/src_qc_pin_e594a73db756_q9 (02:30-02:47): S4Q9BR / S4Q9BBR refused by
  plan_gate_pre TOOLS-SKEW (v1 tree: ca_region_table.py needs fallback_land.part_boxes / CYC, absent); rebinds BIND_RC=17;
  G0 crashed on a missing plan_of_record/sink_bins/hf1c/slw_su_c__cl19bb38ef.json (only in epyc9 die-qc-103/treeA).
- DIE-QC-103 silent since 04:35. S4q9 (no knee fix) did bind on epyc9 treeA; its G0 has 3 new errors: PHY content rows
  with lef + origin_um but no outline_um (phy_serdes, phy_serdes_b, phy_ucie_kv).

## Fix
- S4q9c = S4q9b (sha dcf35395a229) + outline_um = LEF SIZE on the 3 PHY rows. Plan sha256 dd47490db3901da0.
- Work dir: epyc9 /srv/opentallas-scratch2/claude/fable-fix-qc-knee-hc
  - treeE = real cp -a of kw45/src_qc_pin_eb1e73448bd0 (v2, nlink 1) + plan_of_record/zz_s29_qc103_s4q9c.{json,clock_merge,
    kit_pricing,cland_bin_sites} + sink_bins/hf1c/slw_su_c__cl19bb38ef.json + 16 qcviews insertion.json from treeA.
  - bin/chain.sh s4q9c (BR -> qc_r8_pinned derive -> rekey/pinpad2 -> BQ -> hcparam; LATCHECK per bind),
    bin/run_bind_isolated_pin.sh (epyc2 runner, git check dropped, BIND_OUT_ROOT), bin/g0.sh, bin/mk_s4q9c.py.
  - outputs: bind/bind_s29q103S4Q9C{BR,BQ}{,.log}, gates/{knee,plan_gate_pre,g0,latcheck,hcparam}_*, log/chain_s4q9c.log.
  - clients: intel2 ~/fable-fix-qc-knee-hc/{chain,g0}_s4q9c.client.log (ot-run --priority plan --hosts epyc9), started 06:55.
- Pre-checks on v2 tools: knee chains 988 FAIL 0 margin 0; plan_gate_pre PASS findings 0.
- BR is EXPECTED to end BIND_RC=1 with R8_STALE rows (stale seed); the verdict is the BQ bind.

## Adopt criteria (S4q9c)
BQ bind_report errors 0, r8rc 0, LATCHECK 1921/1921 (lane count may differ: read the log), hcparam mismatches 0,
G0 errors = the 2 inherited faces rows (sl_W5_fw.W, coll_f4.E 72 pins / 10 um) and no others.
Then: post READY+ADOPT to KIT-OPS-5 / TOOLS-CONVERGE with plan, asbuilt (runtime/zz_manifest_iso_s29q103S4Q9CBQ.json),
sidecar (runtime/zz_sidecar_s29q103S4Q9CBQ.json), bind dir; TOOLS-CONVERGE copies the bind to kw45/qcbind_pin_<v2/v3> and
the plan data into the published tree on every gen host. Release: the 34 knee types + su_l0 cl7a55c676 + 3 PHY + cbn_q00 x2.

## hc family
- 18 hc type rows are equal in S4q6d and S4q9c; HCSEL (LPC 40) is in the v2 tree. hc does not wait for the adopt.
- Requested 07:0x from KIT-OPS-5: item_env OT_TT_SETUP_DESIGN=1 OT_TT_SETUP_MARGIN=30 on the 18 hc keys, fresh launch on v2.
  CHECK each visit: ~/coord/autopilot/kit_wave.json dies.qwen_compute.item_env + only_items; if not done in 30 min, repeat.
- Proof so far (QC-HCFE-O P0, old hold guard): hc2 route DRC 0, TT setup -32.10 / 7 (was -178.75 / 494). Hold needs the
  QC-SRC-CLOSE pre-GRT non-port hold guard (r271(b), check it is in the tree).
- sle_hc2__cl9c4c4509__cl3edce1b8 SIGNED 05:14 (wave). Export check to AGIdock + rtx-pro still to do.

## DRT-0255
4 proof kits (sle_sc_v1__cl115da35f/__cl7479a5ec, slw_su_l1__cla2a78701/__clcc9d0155) + coll_n in only_items on v2.
First clean route -> QC-PINACCESS-O posts RESULT PASS proof:DRT0255 -> HOLDGEN releases the held rows.

## Open
- KIT-WAVE TOOL-SKEW 06:51 on the v2 tree ("17138 missing"): likely checked on a host without the tree; verify launches.
- QC-CBGLUE raw-branch delta (06:43) goes on top of S4q9c as the next event, not into this one.

## 2026-11-16 08:45 PST STATE (supersedes "Fix"/"Adopt criteria" details above)
- COORD r303: I own the QC plan event. Candidate = S4q9d (S4q9c + FABLE-FIX-QC-CBGLUE start-reset rows on cbf_q01, cbf_q01_s2, glue),
  plan sha 9c0f8e750f07, in treeE plan_of_record. COMPOSED posted 07:50, correction 08:4x.
- S4Q9CBQ and S4Q9DBQ: BIND_RC=1, ONE real error: PARAM_REGEN W5 nb_od of region 0 not the latest (qc_fabric_transport.py:183).
  All HARD_CORE_PARAM_ALL / _WRAP rows are a consequence (regen dropped). r8rc 0, LATCHECK 1921/1921, knee 0, G0 S4q9c = 2 inherited.
- Fix in flight: bin/chain_e.sh BUMP_FE SUFFIX = rebind S4q9d with pinpad2 fe bump 2 / 3 (tags S4Q9DBQ2, S4Q9DBQ3), elab seeded
  from bind_s29q103S4Q9CBQ; logs log/chain_s4q9d_fe{2,3}.log. If both still fail on nb_od: try fe 4/5, or ctl 4 if the error flips to r_d.
- ot-run on epyc9 needs OT_RUN_SCRATCH_DISK_FLOOR_GB=10 (scratch2 32 GB free); binds write 0.5 GB.
- Adopt (first bind with errors 0 + r8rc 0 + LATCHECK PASS + hcparam 0 + G0 = 2 inherited): post READY+ADOPT with plan, bind dir,
  asbuilt runtime/zz_manifest_iso_<TAG>.json, sidecar runtime/zz_sidecar_<TAG>.json; TOOLS-CONVERGE data-packs into the QC tree version.
- Wave (kit_wave.json 4789478d31c): hc TT env on 18 keys; file-01 hold deleted; coll_n attempt 22 placed, in route queue 08:26;
  sle_hc1 cl7d360508 + slw_hc1 cle683a076 in place on v2. hc2 proof kits clf60c5152 / clcc5e3e61 = proof_items DRT0255.
- sle_hc2__cl9c4c4509__cl3edce1b8 exported to rtx-pro + AGIdock (sha adcc5123d68a), INDEX rows on both.

## CODEX takeover 2026-11-16 10:20 PST — supersedes older adopt/source statements
- Active authoritative event: S4q9h, epyc2 `/srv/opentallas-scratch3/claude/fable-fix-qc-knee-hc/treeH`, plan `physical/die_plan/qwen_compute/plan_of_record/zz_s29_qc103_s4q9h.json`, sha `79bca8d5b9bb970900ff04922c97a0ff0d245aaf956ad7e4fae82253b042ae96`.
- H = F seam-station plan + corrected su_l1 geom2 equal-depth chains. Both su_l1 x_su_c_i shorter chains are now four stages along the east corridor and below lane6; max depth remains four, zero extra cycle price. Actual per-bit geometry and image reviewed; prior straight-line G failed macro overlap and is preserved.
- Crucial source correction: old treeE and published v2 lack r301 `ot_qfd_xcst_rep` and `cal_fault_go`. D/E/F binds cannot qualify those fixes and are not blanket-adopt candidates. Root directs coherent H for the next full release.
- H real cp-a source overlays: exact r301 `5e8855d43fe` qfd_c_stn.sv + qfd_sys_face_lctx3_core.sv; exact `0551428f55bee5deb5d916fb0a9fbd7782421ab6` kit_istations.py + test. Receipt `gates/treeH_overlay_receipt.json`; inventory `gates/treeH_manifest_inventory.json`, source hash `6a171b64af2fb819a188e77ddb0ac3a6d19558114d0a013831a6e6b8ea47f819`. No unexpected RTL/tool change.
- Fresh H ELAB/BIND started 10:17 via ot-run, no seed. Tag `s29q103S4Q9HBQI`; hub client PID 467756, log `~/fable-fix-qc-knee-hc/chain_s4q9h_I.client.log`; epyc2 unit `oth-ubuntu-2512480-1794853037`. Script `bin/chain_i.sh s4q9h I 0`; outputs `bind/bind_s29q103S4Q9HBQI`, `gates/`, `log/chain_s4q9h_I.log`. Then R8, LATCHECK, hcparam, G0. Actual start record captured fresh source hash and plan, seed=none.
- Old D/E/F jobs retained as pinned evidence. G stopped by exact owned unit after `gates/g_geometry_rejected.json` FAIL; no failed record overwritten.
- Still required: final KV-HG1 bind -> shared pair calendar compile CST 7,7,7,8,7,7 -> same image on QC/KV -> final QC calendar rebind + component/token gate. Current H calendar explicitly NOT programme-qualified. KV/token agents own the dependency; no source edits in running H.
- Class fixes: missing leaf_um failures on old S4Q6D are fixed in candidate plan (988 per-bit entries audited, none missing). Actual su_c failed RTL topology replay RC0; su_l1 additionally needs merged reader-driver fix 0551428 and corrected geom2 rows. New class 7ef21feb8e needs no extra H rows.

## CODEX 2026-11-16 10:34 PST — J replaces H as the active coherent candidate
- E finished: 37 strict errors = 1 expected fault R8_STALE + 24 false unsigned st_a registry mismatches + 12 REAL su_c MIF mismatches. LATCHECK 1921/1921 PASS; no adoption of this failed source.
- Root cause MIF: manifest omits existing OT_QC_SRAM_MIF. It selects MIF0 despite signed crh/prog/btab built at MIF1. Existing macro couples SUVM.MIF, parent wf_st start and all head MEMORY_READ_EXTRA; leaf-only override would be incorrect. Source H has same missing flag; immutable FAIL `gates/h_mif_profile_rejected.json`, only own H unit stopped exactly. No H source changed.
- J is a real cp-a treeH -> treeJ plus exact unsigned checker3db14d42 and one manifest define OT_QC_SRAM_MIF. Plan zz_s29_qc103_s4q9j.json has same corrected H geometry sha79bca8d5b9bb. Fresh J tag s29q103S4Q9JBQJ, script bin/chain_j.sh s4q9j J 0; client intel2 PID629124, log ~/fable-fix-qc-knee-hc/chain_s4q9j_J.client.log. Outputs bind/bind_s29q103S4Q9JBQJ and log/chain_s4q9j_J.log on epyc2 scratch3 KNEE.
- J source hash909a3b5fcf477b2650f099e9333a9554494f0a864d142af52e6fc3d6f544be8c. Inventory323916 files; exact6 source changes versusv2 = r3012RTL +055reader code/test +3dbunsigned code/test. Receipts gates/treeJ_overlay_receipt.json and treeJ_manifest_inventory.json.
- Unsigned3db fix passed24 tests and real E report replay: removes24 bogus unsigned st_a errors and retains12 genuine MIF errors (crh6/prog3/btab3), unresolved0. Normal source gate GREEN; root approval/merge lane owns integration.
- MIF profile has nonzero local latency: SU word-fetch start3->4, head memory read+1. gates/j_memory_profile_price.json records analytical effect with actual token cost PENDING. TOK-VERIFY-3 owns current one-SUVM/eight-head MIF1+CROM3 native age calibration and compiler repricing; historic +866-cycle sensitivity is not a current price. No P&R or rate claim from J yet.
- KV HG1A strict bind started10:28 on epyc10; final shared calendar remains a later source/image rebind. Current J programme is NOT qualified. Same final QC include/KV ROM64 via-map/boot targets/TXDP record must come from one final compiler output.
- Incoming shared TT PG replay fix: old tt_setup_repair reload loses PG capacity. HEAD nf15_gate owns focused fix; no running kit patched. Any DRT0255 after TT repair must distinguish that class before claiming pin/RTL failure. coll_n a22 currently live detail route; classB v2 runs do not contain r301xrep.
