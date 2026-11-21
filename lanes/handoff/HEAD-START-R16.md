# HEAD-START-R16 handoff (2026-11-21, STAND-DOWN -> HEAD-START-R17)

Goal: r16 HEAD transport bench 329/329 after re-planning START on the r16 die clock (e5c13), then decide which signed types re-sign.
Lane dir: epyc10 `M=/srv/opentallas-scratch2/claude/head-start-r16` (lane clone M/repo = main 625a0f6f0e, no local edits).
Hub client logs/pids: intel2 `~/head-start-r16/*.otrun.log`, `*.pid`.

## Inputs
- Plan r16 p5 1a7d319a9ba6 (M/in/plan_p5.json), sidecar 6fcd1d3dfc43 (NF15b K straps).
- r16 die clock = snapshot prep/NF15f/die_clock kit_tree 564220a7 / kit_ctree 8cd960ed (== head-crossing-1119/clock_early/tree_e5c13a
  ctree; 40 sites differ by 0.054 um) -> M/run/clk. Routed both-edge combo GRT arrivals TT/FF (13383 taps) from
  epyc10 /srv/opentallas-scratch/claude/opus-fix-head-lep0n-r2/dgrt -> M/run/out_{TT,FF}.
- fable-pd-head-clk/ring_declared.json is gone from every host. I rebuilt it as M/in/ring_declared.json = declared common latency on
  all types (types {}). This is an ASSUMPTION.

## Done
1. ca1 = head_current_ca.py (proof, fall merge, landed_phase_ocv, count_align_plan --start-tree clock 405, bind). Plan OK, but its bind
   form has 31 relay parts. Superseded.
2. ca2 = FABLE-DIE-HEAD ca4 form (--start-native-clocks --start-partition-origins --start-leaf-origins, partition table) on the ca1 proof:
   427 crossings, 0 fail, worst 106.8 ps, 1747 regions, 0 START hops >405 um.
3. bind2 (rebind2.py, rebind15b form: keep the adopted latency where it fits >=100 ps, FREG from the sidecar): bind PASS, sim 0/2000,
   margins 106.8/377.4 ps; 5 crossings +1 cycle; K changed on 125/427 ports; FREG set unchanged (30). start_stage_emit: 1389 stages,
   358 die outputs.
4. p6 (compose.py) plan 58f896b3fcbe, sidecar facc71b93198 (M/prep_p6b). gates.sh TAG=p6b (SRC=M/src = snapshot with writable tools
   copy): strict bind PASS, cohort 26/26 EQUAL, LATCHECK 329/329, G0 0 errors / 221 warnings. Lanes +1: chE2_b1, chE3_b6, coll_WN0_u,
   coll_WN1_u, coll_WN2_u.
5. Provider resets (start_reset.py): every stage reset is sited on the nearest EXISTING type raw export (969 reset ports, no new type
   port), then head_start_local_reset settle 88. 9 stage reset hops are 451-572 um (b1420 b1466 b1706 b2084 b2565 b3450 r1701_7 r465_3
   r529_3). M/provider_p6 = bench-only allowance (`--bench-allow-over`). Fix candidate: relay_over.py (one ot_dp_rrelay per stage at the
   hop midpoint, +1 raw release, within the settle guard). Not yet run.
6. hd_st_k5 1676 / hd_st_m 1261 um START hops: they are not in r16 p5 (measured on the older 52f4a81e5bcf plan). 0 over on p5; no rows.
7. Wrappers: published_p6 (head_publish_wrappers, no --private) is byte-equal to the r16 token published for all 27 type files; only
   s81_head_top.sv differs (K strap values).

## Step 5 answer (signed types)
K/PAD/EFALL are parent-tied count straps. The cohort is 26/26 equal, FREG is unchanged, and no type pin or relay changed. The START
stages are die-level only. **No signed HEAD type depends on the stale K straps or the START depth, so none needs a re-sign.**
The 5 lanes gaining +1 cycle are latency-table changes only (LATCHECK PASS).

## Bench results (tr5.sh/tr5b.sh = TOKEN tr4 recipe on p6 + new provider; assemble.py of token-1121-r2)
- tr7 (p6, provider_p6, ideal clock): **FAIL 251/329 (78 failing)**; attempt4 was 211 failing. 158 fixed, 53 persist from attempt4,
  25 new. The persistent ones are all the spine (sp0-5 b/x lanes, ch*_h/_r into the spine, sp_b0/sp_x0), ctl<->mesh/host (m0S/m7S/m7N
  tx/rx, host_tx/rx), kd (ctl.lepk_o0 -> lep0N.lepk_i0: plan 4, measured 5) and head_lep_fault_return (plan 8, measured 2, 104 ok / 96
  err). The new ones are tile chain links ch*_o<k>: pairwise +1/+3 mod ring depth 4 = one tile origin off by 1 cycle.
- tr8 (same, root SETTLE 200): tests whether a late stage reset release delays START. **Identical 78** -> reset release is NOT the cause.
- tr9 (RUNNING, oth-ubuntu-1657380-1795278106; tr9.sh + skew_tb.py): tests whether the failures are an artefact of the bench's ideal
  single clock. The tb is copied from tr7; every clk_region_<part> gets the median TT tap arrival of its part and every t_st_<id>__clk
  gets its node arrival, as transport delays (2 ns == 833 ps).
  Rationale: the plan's start offsets a_child-a_parent = PAD+2+J(d) and the K values both use the REAL clock d. In a zero-skew bench a
  stage is always 3 cycles, and the error per crossing is (n_nominal-3*depth)_dst - (..)_src + d/T. A crude predictor marks 35 crossings
  out of window at zero skew, and all 35 fail in tr7.
  - If tr9 passes or improves strongly: the remaining failures are a bench clock-model limit. Next step: make head_transport_depth gen
    emit real arrivals (tool fix + test, ot-push-main).
  - If not: diagnose the spine (hd_spn forwarded FSTART / in-type START chain vs bind part origin) and ctl, which also failed on the old
    provider.

## Fix candidates
(a) bench real-clock model (tr9); (b) spine/ctl in-type START origin vs bind origin (pre-existing, independent of the tree);
(c) relay_over.py for the 9 reset hops >405 um (physical, not functional); (d) start_tree.uses: still the rp18 copy.
head_raw_start_contract.enrich needs sidecar start_pins, which r16 does not have, so it was not updated. G0 passes anyway.

## Coordination
- FABLE-FIX-HEAD-LEP0N-R2 has p6 shas; HEAD event e1 79ac2973400d is on p6 and is gated green. **Do not apply until the bench
  passes.** One combined apply with LEP0N-R2 is agreed in principle.
