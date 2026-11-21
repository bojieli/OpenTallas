# QC-PLAN-R10 handoff (started 2026-11-21 06:4x PST; succeeds QC-PLAN-R9). Read QC-PLAN-R9.md (06:5x b17 section) first.

## 07:0x state
- epyc8 scratch2 at 79 GB free (disk-ETA HOLD on all admissions; a b17 bind writes ~59 GB). R9's epyc8 waiters (g0cand.sh 3044587/3046540,
  its held ot-run client 3046543 (never admitted), chain_b17.sh 3075086) were stopped by R10; nothing had run.
- b17 moved to epyc7 at the SAME absolute paths: /srv/opentallas-scratch2/claude/qc-plan-r9/{b15in,b17in,v1ctl,b16/{extra_final_*,r8_final}.json,
  bisect/b16_lat.json, scripts} + rt/639df6b7b265 + qc-plan-r8/v2b_host/{proof_gen_v2.sh,rtl_main}. kw45 snap qwen_compute_v1r6 identical (manifest sha 80e4b0c4).
- LIVE epyc7 qc-plan-r9/chain_b17e7.sh (log chain_b17e7.log, OT_LANE=QC-PLAN-R10): latency regen (gen.py latency --inplace on b17in/plan_ctl) ->
  static G0 b17 + b16_lat vs V1 control (g0c/) || strict bind b17 (b17.out, dir b17/) -> post-bind G0 + census (event s29q103S4Q9N46R6V2b17)
  -> 8 proof GENs (b17/post_bind/gen_*.log). Local waiter on the chain log.
- Cleanup debt: epyc7 qc-plan-r8/v2b_host holds a partial 3.2 GB copy (b12/b13 dirs) from an over-broad rsync by R10 -> ot-delete those subdirs, keep proof_gen_v2.sh + rtl_main.
## Next
- If bind 0 + LATCHECK + G0 no new vs V1: proof GENs -> proof kits (private-spec, wave env) to GRT -> kit_wave_edit event-pending qwen_compute <event> -> pack/seal/apply.
- FAM-QC-COLL coll_core (b) ODPRE + (c) R-ring wd / xr_q regs + (d) input-hold lockup: not proven (pkw4 final -255 ps) -> V3.

## 07:5x state (supersedes 07:0x LIVE line)
- b17 (epyc7): strict RC1 = TYPE_SPLIT sle_ctl__cla4f6f12f 4 variants + EMIT; static G0 (g0c/b17) 13 new vs V1: geometry 8 (st_b v2 x_su_l0_ctl x3,
  native59 x5: ft_spread sites still on macros), latency 5 (su_vmw_ctl_E* pad fits no site). hops 12 + x_hc1_st_b fixed by R9 ctl_fix.
- Cause: R7 fix-7 x_su_l0_ctl bumps non-uniform per slice + su_l1 fixed 5->10 -> per-slice pads 2/4/3/4/1/4 at shared sle_ctl x_su_l0_i / sle_su_l0 x_ctl_o.
- b18 = b17 plan_ctl + compose_b18.py (14 slots -> V1 stations: x_su_l0_ctl on 8 st_b + sle_fe_v1__cl8210183c, native59 x5). Pad check 0 conflicts (E pad 4, W 3).
  LIVE epyc7 qc-plan-r9/chain_b18.sh (log chain_b18.log, bind b18.out, dir b18/, static G0 g0c/b18). Reverted rows -> V3 (with R9's 9 + 12 ENDPOINT_REACH).

## 08:5x state
- b18 static G0 PASS 0 (0 new vs V1). b18 strict: R8_STALE 30 only because rt/7ff721a00978 (r8_refresh) was reaped fleet-wide.
  bind_b18.sh = bind_b15.sh with RR pinned to own copy qc-plan-r9/rr_tools/tools (rt 24af28ef7d3c, r8_refresh sha cc66 = R8's).
- b18r (refresh works): TYPE_SPLIT sle_ctl E vs W on x_su_l0_i (E pad 4: su_l1 fixed 10; W pad 3: su_l1 fixed 9) + EMIT.
- b19 = b18 + compose_b19.py: E su_l0 x_su_l0_ctl lanes fixed_cycles 7->8 (0 end-to-end cycles; pad 3 on all 12, schema 0 conflicts).
  LIVE epyc7 chain_b19.sh (log chain_b19.log, bind b19.out, dir b19/, static G0 g0c/b19) -> G0 + census + 8 GENs.
- Apply prep: epyc7 qc-plan-r9/pack_b18.py (pack_b12 pattern; edit base/log names to b19 before use). Pinned rt 639df6b7b26533093f1c002e50f1cd35f430f272
  exists on epyc7/epyc8/epyc9 only. Apply steps = R6 handoff "Apply steps" + R7 seal_v1.sh / publish_apply (expect-source qwen_compute_v1r6, expect-event s29q103S4Q9N46R6V1).
- Cleanup debt (R10's own, ot-delete): epyc7 qc-plan-r9/b17, b18, b18r bind dirs; epyc7 qc-plan-r8/v2b_host/{b12,b13,...} partial copy.

## 10:0x state
- b19 static G0 PASS 0; strict RC1 TYPE_SPLIT sle_ctl E vs W on x_su_l0_i. Root (bind.py lane_pad): x_su_l0_i pad = su_vmw_ctl group arrival (su_l1 lane)
  - 2 - st - landing; su_l1 internal fixed E 10 / W 9 -> E 11 / W 10. b19's fixed move does not change it.
- b20 = b19 + compose_b20.py: slw_su_c__cl19bb38ef + slw_su_c__cl92142dac x_su_l1_ctl 32->33 (regs + bit_sites stage at the midpoint of a 40 um hop;
  +1 cycle W su_vmw lanes). LIVE epyc7 chain_b20.sh (log chain_b20.log; try1 failed schema bit_sites, fixed).
- Helpers: QC-PLAN-R10-CELLS DONE (epyc7 qc-plan-r9/cells_census.tsv). QC-PLAN-R10-R8S running (R8 strap class -> epyc7 qc-plan-r9/v3rows/r8_straps_rows.json).
- V3 row sources: FAM-QC-FEFW-R2 08:47 post (x_sc_i +1 station: slw_fw_v1 cl592e3d37, sle_fw_v2, slw_fw_v3, slw_fe_v1); OPUS-FIX-QC-SLE-R4-ROWS epyc8
  opus-fix-qc-sle-r4-rows/l2_rows.json 7b909920c732 + l7_rows.json a0fe0cfcd8b4 (apply_rows.py cb5fb63c579f; l7 needs R8 re-derive); FAM-QC-CB-R2
  fam-qc-cb-r2/p1/plan_b16_rp.json (cbf_q00 inst_taps t24/t25/t77/t76; needs bind); FAM-QC-HCST-R2 clf4365a62 face-home (copy cl9f076a5c floorplan);
  FAM-QC-COLL-R2 six defines; 0840 sec 4 items 1/5/8/9 (27 >405 rows, 212 re-legs, taps by region); cells from census.
