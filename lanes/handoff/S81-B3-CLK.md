# S81-B3-CLK handoff (Opus lane for COORD; S81 B3 clock + reset slice, integrates into DIE-S81-91 B3)
Started 2026-11-14 ~00:10 PST. Work dir: epyc7 /srv/opentallas-scratch2/claude/s81-b3-clk (M below). intel2 launch logs ~/b3clk/.

## 1. Clock taps (DONE as a plan delta; bind running)
- Tool M/b3taps.py (tools = B2u bind tree): LOAD leg -> one added tap at the weighted median of the far half of the leg's sinks
  (legal site per added_tap_recentre.legal); RADIUS leg -> one added tap at the median of the out-of-reach sinks; then reset tree
  re-solved and published (event_taps form). --uncap drops the B2u tap_max_sinks 2000 override (default cap 1500 again).
- 30 overloaded types (B2u_tapcap_types): 1 tap each (clk_t39 for clk_t19/t16, clk_t37 for clk_t21), max load 1614/1853 -> 1373,
  reset depth unchanged (6/6, 7/7); changed reset keys = taps/n_clock_taps/tap_depth/core_resets/n_reset_consumers. M/b3t30.json, M/b3t30_rep.json.
- 6 held col_h10_r0_p1 types (frame form from die-s81-90/fp/plan_tapleg.json): reach tap for clk_t18 at (1580.74, 987.808) + follow-on
  split taps (3-4 added per type), max load 1500, depth unchanged. M/b3t6.json, M/b3t6_rep.json.
- chainT (M/chainT.sh): B2u + 36 types -> die_refloor -> tapleg -> delta_frame_collector (plan + sidecar) -> base_b3 ->
  strict bind + LATCHECK with the serdes define + re-proof. Outputs M/ev/{B3t.json, side_b3.json, base_b3.json}, run M/run/b/B3t, log M/log/B3t.log.

## 2. svc_lo reset-collector reach (PARTIAL; tool ready, rerun after the svc re-pack)
- The H8 band plan's svc_lo collector trees are stale vs the H8 outline (tree planned at 380 um, hops now 406-426 um; 26 over-reach
  edges in 4 types per collector_reach.py, bind shows only the first per type; t5 tap rst_n_t25 sits at y 2892.9 > outline 2851.2).
- Tool M/collector_fix_b3.py (zero cycle change): source miss -> reattach to nearest same-depth relay within 405; edge miss -> nudge one
  end relay to a legal site keeping all its edges <= 404.5. On H8: t5 CLOSED (attn_i1 -> rst_n_t24); rs_w attn_i0 -> rst_n_t24;
  8 edges nudged; LEFT: chains whose length > n x 405 (t1/t6 rst_rl_31->28 406.04, t7 rst_rl_492->491 406.04 / 200->199 406.2,
  rs_w 128->119 406.16 / 28->24 412.64). Those need one extra relay (depth +1 on that branch) or the tree re-solve; both move reset depth.
- Recommendation: the S81-B3-SVC re-pack changes these outlines anyway; republish the svc_lo trees with delta_frame_collector after the
  re-pack (planned at 380 um -> no over-reach by construction), then run collector_fix_b3.py for any source misses. Re-solve on the
  H8 outline gave depth 11 -> 12 (t1/t6/t7/rs_w), t5 10 -> 10 (M/rt_h8.out).

## 3. Serdes reset tree define (DONE in code; bind proof running)
- tools/die_plan/dead_inputs.py patch (M/dead_inputs.py, test M/test_dead_inputs_reproof.py, 2 passed): a proof whose define list differs
  from the manifest is accepted only when a manifest "dead_input_reproofs" file (repo-relative) is a PASS made under exactly the manifest
  defines with identical dependency_modules and identical declarations (re-proof params a subset: svc_sx H=16 absent). The old rows stay applied.
- Re-proof = die-s81-90/dprove/out/proof.json (DIE-S81-91), shipped at results/token_pass/s81_dead_inputs_2148/proof_rsttree_reprove_1114.json.
- Overlay M/ovl_b3 = overlayG (hardlinks) + patched dead_inputs.py + test + re-proof. Runner M/run_bind_b3.sh = run_bind3.sh + REPROOFS env
  (adds dead_input_reproofs to asbuilt_run.json). Proof bind B3s (B2u plan + define): M/log/B3s.log, M/run/b/B3s.

## Update 11-14 ~02:xx (COORD: LIMIT-BIND-1)
- LIMIT-BIND-1 (train S 235ca3a3123) makes tap sinks/reach AND collector reach info-only, so item 2 no longer blocks bind;
  collector_fix_b3.py stays an advisory zero-cycle improvement.
- B3s (B2u + define + re-proof) bind = the SAME 76 errors as B2u (1 EMIT ot_s81sl_leaf__t1 clk_t17 radius 246/200 + 75 LF_CS_DEPTH
  follow-on); no dead-input error -> the serdes define + re-proof are accepted. B3t run stopped (in G0) per COORD.
- B3v = ev/B3t.json + LIMIT-BIND-1 overlay (M/limit_bind_1, apply.sh) + define + re-proof, elab reused from B3s/out (same asbuilt + define),
  G0 skipped. Runner M/chainU.sh, log M/log/B3v.log, out M/run/b/B3v. (B3u failed only on a SIGPIPE in my overlay step; fixed.)
