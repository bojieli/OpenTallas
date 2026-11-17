# CODEX S81 strip takeover handoff, 2026-11-17 00:31 PST

Latest source: E8 `/srv/opentallas-scratch2/claude/fable-fix-s81-cong/wt_xr`, branch `claude/s81-strip-raw-proof-1117`.

- RAW mechanism proof commit `25a8e43f8d3c2e4c30144ea4e1b307bbc0600cc5`: normal GREEN65/65 on main17e5c950f49. `results/rtl/s81_vpw_raw_1117/run.py` reproduces 10,001 actual generated VPW writer comparisons and 9,995 read-after-write scheduler comparisons on two full-capacity 512x128 masked synchronous old-read SRAM models. Omitting dependent-read +1 fails cycle36. Arithmetic and canonical scheduler integration are not claimed.
- Latest evidence-only successor `7dbd8c613bb102da91d3a25d6a6df8d5318434f4`: also normal GREEN65/65 on main17e5c950f49. `results/rtl/s81_strip_B_elab_1117` records matched fresh-source full-shape leaf elaboration. t34 XR0 13,546 -> XR1 18,564 RTL FF; t62 13,277 ->18,295. Delta +5,018 each =4,096 HI +902 writer +16 DSR +4 reset. Exactly27 hard macros unchanged. This is RTL state before mapped optimization, not mapped area/timing. Both qualified refs sent root directly.
- Both commits stack on optional tools already proposed in this lane. Optional reset copies and CFR remain OFF in BASE B. No D5c body mutation or B PNR.

## B source/producer experiment

Frozen C3 actual source closure: E10 `/srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s5f`. C3 plan c20ec9e4c3c4. Experimental results E10 `/srv/opentallas-scratch2/claude/fable-fix-s81-strip/fullB_1117`.

- Fresh raw full-shape leaf source is generated from actual frozen C3 VP and leaf RTL with the approved XR mechanism. `s81_B34_fullshape_v3.{ys,json,log}`, `s81_B62_fullshape_v3.*`, matching `_base_v3.*`, and `B34_area_census_v3.json`/`B62_area_census_v3.json` are the final raw-leaf results. Version3 explicitly includes actual `ot_rst_relay`, `ot_hdc_delay`, and `ot_reset_sync` bodies. Earlier C3 frontend interface stubs were unsuitable for state/timeline measurement; earlier counts superseded.
- Price write availability +1, hc_post +1, boot reset +1, VP read0. Source CS_HI_D remains2; XR supplies the effective third HI stage. Do not additionally increment source HI_D.
- Actual native-parent partial ELAB retains the original `dv_die` source, the exact selected 3S/6N parent path and real HOSTB observer, blackboxing nonselected structural parents. `parent_t34_v3` and `parent_t62_v3` contain the final selected-parent source JSON/scripts. About4.4GB peak, 44-55sec, fresh JSON210/212MB. These are explicitly experimental partial source contexts, not complete die contexts.
- Partial bind CANNOT produce a qualified native B kit with current tooling. Both final consistent-C3-tool attempts abort in `native_istations.annotate` on omitted column `fW0_p1_b0.frame_int_o0: expected one outgoing lane`. Logs in each final `bind.log`. Earlier attempts diagnosed duplicate cohost wrapper definitions (fixed), stale E10 relay/wt TOOLS-SKEW (use frozen C3 producer tools), and inapplicable global ROM instance_path obligations in a no-ROM partial context (explicitly scoped out only for this experiment).
- Existing `bind_component.inspect` permits only other-type wavefront core-reset EMIT errors. It rejects omitted-parent source errors. No gate bypass, old bound VP stamping, PASS receipt, or B physical run was made. Next qualified native physical vehicle needs fresh C4 full-context bind+LAT, or supported minimum-context production preserving the entire selected C3 clock/reset/FT contract. No further partial-bind retries are useful without that support.
- All our component jobs completed. No active component job remains as of this handoff. Preparation scripts are E10 s81-b3-clk `prep_b_leaf_strip_1117.py`, `prep_strip_parent_v2_1117.py`; final actual commands are the immutable `.ys`/`run_parent_elab_v3.sh`/`run_parent_bind_v3.sh` in fullB_1117. Preserve source/results; no old published tree was edited.

## Corrected GPL and remaining classes

Corrected GPL source `claude/s81-strip-gpl-td30-1117@056783ac187`: exit overflow .25 and persistent second TD pass .30 (64/30). Earlier39ef remains HELD. Prior corrected t47/t75 full-shape CTS pilots and images collected/reviewed. No need to repeat.

- Actual kitRC corrected t47 (not artificial cap1.45): WNS-1096.5ps; 796 negative /655 below-42. Die reset106/-1096.5, START63/-463.17, VP other202/-264.24 (200 coefficient controls), VPW281/-249.32, VP reset1/-92.77, HI2/-75.74. Zero negative lap_ok / displaced-ring paths. Thus old broad displaced-ring class is cured; reset/START remain die-owner priorities. Extra blanket data stations are not indicated by the corrected placement result.
- Corrected t75 cap1.45: WNS-531.09; 867 negative /472 below-42. HI417->0 and displaced-ring class gone. Remaining die START24/-531, die reset101/-400.74, VP reset40/-378.55, VPW217/-301.34, VP other85/-170.25.
- Cap1.45 is census information; clocks/SDC/uncertainties were never relaxed. Actual kitRC read merely removed the artificial RC multiplier.
- Bank-end hook `e1b62d6096a` already has real old-shape t34/t62 DPL PASS:317 FF per cohort, nearest-bank maxima11.328/13.488um, placement checks pass. Actual B adds902 writer FF, so preoptimization cohort estimate1219. This hook does NOT place the additional4096 HI FF. Fresh B physical placement/clock proof is still required.
- Optional reset copy tool `d5946a58004`: +32 FF versus baseB, no extra cycles, minimum reset mechanism proof PASS. Optional CFR tool `46684a7f11b`: existing registered coefficient decode selected with XR, nominal5 state bits/0cycles, minimum coefficient miter PASS. Both physical/context proof pending and off in BASE B.

## t75 FT geometry

E8 `/srv/opentallas-scratch2/claude/fable-fix-s81-cong/t75_ft0_repack_v2` is the reviewed geometry source. Only ft0 station4 per-bit sites/regs change. Old worst hop442.8um -> max380.7um; zero macro/other-FT overlaps; 0 FF/0 cycles. Full-height band x399.6..418.284,y4.32..54.0. Do not use first south-only v1 or shift-only macro-overlap proposal. Die geometry owner already incorporated v2 into private C4 row candidates. No timing relaxation.

## Inherited GRTs, preserve

Original tapfix1 GRTs remain progressing; no completed5_1_grt.odb when last checked around00:20. t28/t34 intel1 and t62/t72 epyc7 under `/srv/opentallas-scratch2/claude/fable-fix-s81-cong/countable_F2s4tapfix1_eight/gen/ot_s81sl_leaf__tN`.

Last observed extra iterations: t28 13/30, t34 24/30, t62 11/30 (after its NDR restart), t72 11/30. Preserve. Existing Fable strategy permits stopping after GRT read via exact job PID/ot-heavy-stop only; no pattern kills. Fresh GRT timing must use global-route RC1.0. E7 `fable-fix-s81-coltap/an/stage_sta.sh KIT OUT grt` is the inherited helper; rank helper `fable-fix-s81-strip/rank_strip.py` on E7/intel1. Wait for FX DONE before ranking. CTS helper uses cap1.45, GRT helper uses actual route RC.

## Source/coord state

Only untracked `results/geom_review/s81_vpw_bank_1117/t75_report.json` in wt_xr is an obsolete v1 report; do not adopt. No source WIP was left. Canonical posts are `lanes/posts/CODEX-S81-STRIP.md` via post.sh. Gate logs intel2 `~/fable-fix-s81-strip/gate_raw_proof_1117.log` and `gate_B_census_1117.log`. No owner question is pending.

## 00:39 integration and live-job update

Before the next B full-context ELAB, account for this source-staging trap: `leaf_cs_depth.py` correctly counts the native shared+per-lane chains, so effective B HI3 can be checked against planHI3. However `stage_lfcs_netlist.py:leaf_depths` blindly writes the plan depth into source HI_D and defaults HI_GS=HI_D. Restaging a B planHI3 through that helper unchanged would create sourceHI_D3 plus XR1 = effectiveHI4. Keep sourceHI_D2/GS2 and represent/price the effective third per-lane stage in the plan. `--hi-gs2` alone cannot fix the double stage. An explicit XR-aware source-depth mapping is required for that source-staging path. No tool/source body was changed for this finding.

Last GRT watch00:34: t28 extra14/30, t34 extra26/30, t72 extra12/30; no5_1 checkpoint. t62 restarted its extra iterations again because GRT disabled NDR on `clknet_0_fclk_in_ft4_i[0]` after extra11/30 (earlier fallbacks: `clknet_0_clk_t47`, `clknet_1_1_0_clk_t47`, then `fclk_in_ft4_i[0]`), now extra4/30. This is ongoing automatic congestion fallback, not a dead job or finished result. Preserve all four jobs.
