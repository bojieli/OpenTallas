# Remaining sender proof classes — finite static diagnosis

No proof/CAD/source change. Flow owns ROOT-authorized aliases/hunt/16ld finite lemmas. This adds an untrusted proposal, not authorization to expand the proof run or to trust a new assumption.

## 256 matched-only points

Smallest retained point a_v has13 reported support keys. Actual gold.aliases.json a_v driver is $aldff D=launch, AD=0, ALOAD=rst_v0 (local8). Actual final synthesized netlist a_v cell D=launch, RESETN=local8, SETN=_103743_ driven by tieHI: the output flop reset/data interface itself matches.

Actual gate launch cone: NAND2(OR2(QN pace_ok,QN rep_ra0), OR3(QN up,QN rdy_k2,QN ski.o_valid)), with buffers only. It implements (pace_ok && rep_ra0) || (up && rdy_k2 && ski.o_valid). RTL launch uses (pace_ok && rep_r) || accept_c. Retained final hyp.json maps GOLD rep_r to GOLD u_k_rep_o.q; no hypothesis relates matched rep_ra0 to matched u_k_rep_o.q. Thus the same-copy registers are independent in the retained induction cut. Source ep lines817/851/852 give both the SAME next-state expression accept_a?rep_1:rep_0; reset leaves differ: u_k_rep_o uses rst_v14, rep_ra uses rst_v2, reset values both0. Source assertion also checks rep_o==rep_r, but an assertion does not supply a proof.

Concrete candidate: UNTRUSTED_replica_residual.json. Prove nativeBASE64 plus STEP including actual resetleaf equality before binding it. Same data expression alone cannot justify equality under independently free reset leaves. Reduced combinational illustration (not an original ABC counterexample): rep_o1/rep_ra00/pace_ok1/accept0 with both reset conditions deasserted gives goldlaunch1/gatelaunch0; equality invariant removes that free-state assignment. Reported64-key truncated support lists contain BOTH keys in212/256 points, rep_ra0 in238/256. This is a bounded mechanism candidate; no claim all256 fail for this cause.

All256 reported lists also contain bout_coll_oa.u_ep.eq and la.rxen. Do not infer these should be equal: actual gold eq D=rst_n_t2 with its reset=rst_n_t2; rxen D=1 with reset=r_misc. They have distinct source/reset scope and may appear through common miter/model constraints. Preserve source contracts.

## 27 gold-X points

20 la pace bits, la pace_ok_r, la/lb pv, la/lb pnak, la/lb fault. Gold-X support is syntactic, not evidence of a live unknown. Actual retained gold.aliases.json has:

- pace: outer procmux2702 S=launch, B=defined launch-result, A=inner2694; inner2694 SAME S=launch, B=allX, A=increment/hold result.
- pace_ok_r: outer2698 and inner2689 with SAME launch selector and the same overwritten-X pattern.
- la pv: outer2477 S=rr_ok0 B=1 A=inner2469; inner2469 SAME rr_ok0 B=X A=remaining result.

Identity mux(s,b,mux(s,X,a)) = mux(s,b,a) makes those particular X arms unreachable. Keep native ternary/gold-X comparison semantics unchanged. Fault/pnak and remaining dependencies need exact cone reduction after the replica invariant is proven; do not classify every gold-X bit as this pattern without extracting it. No constant assumption, invalid-output waiver, source edit, or equivalence claim follows.

Next action: parent approves narrowly adding the single replica/reset relation to flow finite lemma set after existing authorized set. If nativeBASE/STEP fails, retain mismatch and inspect exact local2/local14 reset transition; do not assume related reset taps or transfer a proof from another module. After a proved relation, locally reevaluate these original matched/X cones with the same native compare rules; retain each unresolved point and its smallest counterexample. No8h stochastic full proof rerun.
