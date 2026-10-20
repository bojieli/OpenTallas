# R5: one-hot role rings (HBM-SMATT5 2026-10-20)

R4's standalone census (yosys synth -flatten + abc) PASSED, but the gate's in-flow ORFS synthesis census
(smh_pvm_ref_s6a/s6b @be8b041a9, routes/gate/work/orfs/native_census.json on ot-agidock128) FAILED: 26 roots,
max 134 -- timing-driven ABC builds binary-select muxes, so the select bits of every barrel counter fan out
51..134 (slice provenance counters 0..3, c_q, c_tag, c_nt), fr_c[1] 48, wrapper pubslot2t[0] 49 / tag2[14] 34,
and the node_tag write decodes (finish_slot) 33. LESSON: the binding census is the in-flow one (1_2_yosys.v);
a standalone recipe can pass while the flow netlist fails.

R5 (FAN32=1 only; FAN32=0 unchanged): every wide reader uses a KEPT one-hot ring (rotates each edge, equals
onehot(bp+offset), checked every edge) with AND-OR muxes: 4 slice-group rings, q_* rings (state / n8), pv_tag
halves, node_tag halves (own slot read + finish from slice copies 4/5), fold-ring write and read rings.
Wrapper: 9 kept pub_slot copies (2 tag bits each + slot0), 2 kept tag_d[14] copies (ev_c / e_c,e_n writes).
Rings sit on reset groups 16..27 (18 + 8 = 26 terminals). No edge / schedule change.
Benches (5.050, FAN32=1): exact/tight/reassert/stopclk/tight_reassert/xrand x4 PASS; pubearly, MUT1-13 FAIL
(kit_bench/ in ../r4 re-captured on r5); FAN32=0 xrand stopclk PASS; MUT13 with -DSYNTHESIS fails behaviourally.
Census verdict = the s6a/s6b gate's in-flow census on this commit.

r5 in-flow census (gate @432d088cf, ot-pve1 smh_pvm_ref_s6a-20261020-025107): FAIL 63,688 roots, max 45, 2 roots:
pubslot2t[1] 33 (2-bit node_tag read with binary select) and u_core.fd1 45 (fold ring write enables).
r5b: 17 one-bit pub_slot copies; fr_a slot rewritten at every visit (read only under fr_v of the same visit),
so fd1 drives only fr_v + the fold mux. Benches re-captured (9 PASS, 14 mutants FAIL, FAN32=0 PASS).

r5b in-flow census (gate @53fef2c47, agidock smh_pvm_ref_s6a-20261020-030241): FAIL 63,711 roots, max 33, 1 root c_sr[2] 33
(stack read rk mux). r5c: one-hot ring r_sr (group 28) for rk; c_sr binary only for the address bits. Benches re-captured.
