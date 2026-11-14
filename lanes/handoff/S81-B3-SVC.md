# S81-B3-SVC handoff (Opus lane, S81 B3 svc slice), 2026-11-14

Patch set: epyc7 /srv/opentallas-scratch2/claude/s81-b3-svc/patchset_b3svc/ (private, DO_NOT_COUNT). Consumer: DIE-S81-91 (B3 event).

## Shapes (task 1) - DONE
- svc_lo rs t1-t7 + rs_w t1: 1702.08 x 2998.08 (row re-pack, pack_lo2.py -> lo_pack2.json, render lo_pack2.png, 0 overlap, macro density 0.62).
- svc_hi rs t1-t6 + pvso_entry t1/t2: 1702.08 x 2851.20, nothing moves (already legal).
- die_refloor on B2u: die 32987.52 x 25997.76 fits reticle (2.24 Y / 12.48 X spare). 10 rigid-overlap conflicts are reported in every probe, base included: DIE-S81-91 resolves them in the event.
- Delta: b3svc_delta.py BASE LO_PACK OUT --delta (b3svc_delta_v2.json). It moves cores, taps and collector core_resets; drops pvso g_h[8..15] (32/type); renames t7 u_irg -> u_irg.u_rg3.
- ft stations re-sited with tools/die_plan/ft_sites_unblock.py through ftu_wrap.py (CLEAR 8.64, radius 80, retry tighten). Results are in ft_slots_delta.json:
  - t1, t7, rs_w: 0 stations added (tighten 40).
  - t6: +1 station on ft0, ft2, ft3 (E2, tighten 30). This is +1 cycle on those 3 N->W lanes (pre-approved), so the latency table and LATCHECK must be redone on the bound plan.
- Final plan: plan_b3svc_v2f.json (sha 0e01770d484d) = H8 band plan sg1077 + delta + ft.

## Bind (task 2)
- Base was 302 errors. b1 (v1 geometry) left 9, and none are tie/plan class (TIED_BY_PORT empty):
  - 3 lo t1 reverse collector hop 406.04 > 405;
  - 2 collector source reach (lo t5 attn_i1 424, rs_w attn_i0 451);
  - 4 col_h9 grid+explicit tap radius 240.7/200 (not svc).
  - All 9 belong to S81-B3-CLK (collectors/taps).
- Fixes:
  - asbuilt_band_h8_b3svc.json: 13 declared_ties rows, each with RTL file:line:sha proof in declared_ties_svc_h8_b3svc.json; dissolve dsdv_idx_rg3_nq(+_native).
  - Plan: pvso g_h[8..15] dropped; t7 IRG renamed.
- b2 (plan_b3svc_v2f, final geometry + ft): 15 errors, TIED_BY_PORT empty.
  - 9 are the same CLK-class errors as b1.
  - 6 are LANE_LATENCY/LANE_CYCLES on xtier__eng__s_6N_C (68->69 stations, 94->95 cycles) and xtier__eng__s_6S_C / xtier__s_6S_C__eng (37->38, 54->55): the t6 +1 stations.
  - Fixed by lat_fix.py (latency.lanes +1 on those 3 lanes, pad 0) -> plan_b3svc_v2g.json sha a25bd6251dfa, latency_delta.json.
  - (gen.py latency refuses the H8 plan: schema 'unknown key notes'.)
- b3 on v2g was launched via ot-run on epyc7 (unit oth-ubuntu-2679790-1794656297, log epyc7 s81-b3-svc/bind_b3.log, intel2 ~/s81b3svc/bind_b3.log). epyc7 then went ssh-unreachable (banner timeout), result not read. Expected result: the 9 CLK errors only.
- OWNER 11-14 'remove conservative limits' (delete bind reach/sink limits) would also clear all 9 CLK-class errors (405 reach, 200 tap radius).

## gen_lint memory (task 3)
- In H8, attn_staging is already a generated macro. The svc memory closure (kit_rtl_post.d/s81_svc_memory.sh) maps it to 8x ot_sram_1r1w_160x265_m1_r0c0 on every band svc type, hi t1/t3 included. The bound netlist has ot_hdc_v41x_attn_staging only as a blackbox stub.
- FAIL-S81-1 (claude/fail-s81-1-fatal-1113@e83e75e4b7) already raised the lint bound to 65536.
- Kit-rtl proof on hi t1/t3 is blocked: kit-rtl refuses while the global bind fails, and component-proof FAILs on the 9 CLK errors. Re-run lint_b3svc.sh (or lint_cp.sh) once B3-CLK clears them.
- No tool diff was needed or written.

## Open
- S81-B3-CLK: re-derive the lo collector relays/root on the new pack (the 9 errors above).
- DIE-S81-91: integrate plan_b3svc_v2g + manifest into B3, regenerate latency, run LATCHECK.
