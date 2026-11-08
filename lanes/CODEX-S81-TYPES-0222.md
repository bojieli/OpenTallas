# S81 types takeover 2026-11-08 02:22 PST

CODEX took over: S81-TYPES-6 / LEAF5 / LNB / COLH / XRT views. No merges, tags or plan-of-record changes.

## CODEX notes
- t5 vA FAIL: GRT-0183 on vp_driver_hw_d_q[114] (boxed-in local congestion), 45m22s GRT. Viewed intel2 .../s81-leaf5-1/pilot/t5_vA/gen/ot_s81sl_leaf__t5/run/layout_review/grt/congestion.png. CLASS CHANNEL: VN W-face escape remains crowded; VP/VN horizontal seam + west LN and NE FT clumps. No retry.
- t5 vB ALIVE GRT repair; tmp log advanced at 02:24. vC ALIVE GRT extra iteration 7 at 02:29. Both intel2 /srv/opentallas-scratch2/claude/s81-leaf5-1/pilot/t5_v{B,C}. No class batch until final GRT and image read.
- t56 LN copies ALIVE CTS on intel1 /srv/opentallas-scratch2/claude/s81-lnb-1/pilot. Prior synth/LEC EQUIVALENT 69883/69883 and viewed PLACE retained; no duplicated build. GRT read pending.
- COLH vS3 ALIVE GRT extra iteration 11 on intel1 /srv/opentallas-scratch2/claude/s81-colh-1/vS3/gen/col_h10_r1__t1__cl95b37463. Read final 3D overflow, then act on S-slot class if residual.
- t31 FAIL remains CHANNEL + WEST-LANE. Private prototype widens VN seam 17.28 -> 69.12 um, moves VN a/b +/-25.92 and adjacent VP buffers with them; all macro + FT-slot nonoverlap checks PASS; weighted bus cost +3.89%. West lane remains unresolved, so NO BUILD yet. Work /tmp/codex-s81-types-0222/leaf_channel_reform.py + t31_new.json; code branch pending after viable complete geometry.
- t37 a3 collected FAIL GRT-0116: overflow 22134 (M6 21849, 98.7%), M6 max H14, overall utilization only 6.64%; structural local horizontal CHANNEL, not global load. Already on facing macro form. Geometry image read + class matching next. Kit epyc5 /srv/opentallas-scratch3/claude/kw26-wave-1106/runs/s81/kit-wave/s81/e9eda32d41c/items/ot_s81sl_leaf__t37/attempt_3/gen/ot_s81sl_leaf__t37.
- XRT1/3 detail-OBS fix 166005e6c53 landed. c3x_C t1 / c1x_C t5 relaunched by wave. c1x_C t3/t9: watch for exact DRT-0073, then same existing class fix; no blind retries.
- gunit plan bind/clock checks owned by parent S81, not duplicated here. SVC and RCK owned separately.

## Next
Collect final t5 B/C, LNB t56, COLH vS3; view GRT. Complete t31 west-lane structural geometry, match t37 hotspot, and inspect col_h9 new fail. Coordinate all wave changes via root wave owner.

## CODEX notes 02:37
- c1x_C t5 a12 KIT_TOPOLOGY_BIND_STALE class diagnosed: full reset_context digest changes only because unrelated four LP clock.taps lists changed. Selected native type hash, actual asbuilt, global reset, clock table and transport match. Canonical producer full plan reproduces receipt exactly; no source stamp allowed.
- Own hub branch codex/s81-reset-scope-0222@7d2ba37c59, on main 289149dea5b: opt-in OT_NATIVE_RESET_SCOPE=selected fallback validates producer receipt + selected reset/hard/clock/global reset. Default OFF. Tests 10 PASS including selected-tap/reset, global-reset, transport, actual-asbuilt and producer-context mutants. Actual failed capsule predicate default FAIL -> opt-in PASS; selected tap mutant FAIL. Private topology pilot through ot-run is pending on epyc4 /srv/opentallas-scratch3/claude/codex-s81-types-0222/reset_scope/pilot_rtl. Original a12 files untouched. Wave owner notified.
- col_h9_r0_p2__t1__cl9f71e63d a12 FAIL: 114812 overflow (M6 76892), retained failed GRT DB. Read-only render completed at epyc2 /srv/opentallas-scratch3/claude/codex-s81-types-0222/colh9/grt/{congestion.png,density.png,smells.json}. VIEWED: deep vertical choke through array centre, top W/E macro band channels; high station clumps on E and long fanout spread 2371um. CLASS CHANNEL+STATION, not safe for simple colh10 windows transplant. Needs own windows and station slot reform; no retry.
- ot_s81sl_kv_leaf__t4 a4 LEC NOT EQUIVALENT: 621 differs/0 undecided on 90738 CP; 90117 proved. All differences in unblackboxed VN_B arithmetic (g_j.u_a.g6 error flags + removed k3 registers), while VN_A is macro blackboxed. Same full-VN_B proof class owned by S81-KVLEAF-LEC-1; 64-edge proofs still alive. The route failure is a proof failure, no route retry or waiver.
- t35 a4 moved automatically to intel2 S2/codex-fleet-0222/staged/t35a4/gen, same frontend 2249349, unit 3746226-1794134103 at 02:35:04. Track this physical result; no duplicate.

## CODEX notes 02:46
- Shared topology integration READY now hub codex/s81-reset-scope-0222@faa6c88d4a. kit_wave forwards ONLY exact gen_env OT_NATIVE_RESET_SCOPE=selected to topology preparation; absence unchanged, invalid values reject. 7 helper tests PASS in addition to 10 topology tests. Default OFF, canonical runtime/config unchanged.
- ONE private fullpipeline c1x_C t5 candidate launched on intel2 scheduler /srv/opentallas-scratch2/claude/codex-s81-types-0222/c1t5_attempt1/{spec.json,unit.log}. Source epyc4 /srv/opentallas-scratch2/claude/codex-s81-types-0222/source at exact faa6c88d4a; clean own sparse clone, 1.8GB. Work epyc4 S2/codex-s81-types-0222/pilot_c1t5/attempt_1. No canonical queue entry; run-item ends at PLACE+geom. No route authorized for this private source pilot.
- Review: viewed actual preceding c1t5 a11 geom/auto_geom.png (epyc2 wave path); macro footprints/positions unchanged by reset scope and detail-OBS access fix. Existing sparse fields and clock sink imbalance remain advisory geometry liabilities; pilot limited to PLACE and mandatory image read, no pass claimed for route. Picture copied /tmp/codex-s81-types-0222/c1t5_geom.png. Next stage requires new placed review.
- New col_h9_r0_p4__t1__cl8ef405e8 a11 GRT-overflow job6fff290504ff joins the COLH own-window/station-slot class; no retry. Exact source54cce old class. Read its GRT totals/image separately before any reform.
