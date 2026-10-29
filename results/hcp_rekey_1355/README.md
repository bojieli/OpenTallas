PARKED ON EXPLICIT CLAUDE RESET14:02. DIAGNOSTIC ONLY, NOT EQUIVALENT.

Base = explicit current-main fb1fc7959; branch codex/clock-hcp-1355.
HBM owner confirmed no active HCP successor and authorized reuse of the SAME
retained AIG proof. This changes no RTL, clock, reset, timing or physical plan.
Current selected recipe/pin identity was not requalified before reset; this is
only a retained-source correspondence candidate, never a current-core signoff.

Runtime: intel1:/srv/opentallas-scratch2/claude/codex-hcp-1355.
Exact old normalized.pkl and lec_engine.py copied from codex-hcp-0848; complete
original AIGs/maps/aliases/hyp.json remain in that previous runtime inputs/.
Prior baseline5 exactly reproduced9658/9246PASS/412DIFF and identical failure set.

Candidate removes ONE false name match:
 gate nout_r[1] -> nout_r#t[1], paired to gold nout_r[3].
Gold noutbit1 loadsZERO; surviving gatebit named1 loadsONE (goldbits3/4 do too).
Adds9goldconstants(noutbit1+d0[6..13]), all original4-cycle reset bases atedge1.
Old474hypotheses otherwise retained; zero state constraints. The new equality's
gold and gate source reset bases both0. No gate obligation masked or waived.

Completed before explicit reset, ot-run unitoth-ubuntu-508598-1793307768:
 joint528/528PROVED; fullcompare9667 total:9312PROVED/355DIFF; exit1.
This closes57 of the original412 differences, but is NOT full equivalence.
Remaining failing names concentrate u_div d_bad/d_e/d_mb/d_sign/f1_st and
reciprocal g_rec pipeline; full list in proof/compare.json. No further cone
diagnosis after reset. Wrong-inverse control was planned but NOT REACHED because
full comparison failed; do not claim that control passed.

No live own job remains. Check tail of runtime/rekey.log. Failed outputs are
retained; no retries overwrite them. Continue diagnosis on the355 retained
failures, using the prior AIG/cache, only after takeover resumes.

Shared clock collection in this interval also closed the09:59 duplicate-clock_port
finding by existing current-main15598c002 (DIE-HEAD-29); no duplicate patch made.
No duty sweep or frozen-plan change was started.
