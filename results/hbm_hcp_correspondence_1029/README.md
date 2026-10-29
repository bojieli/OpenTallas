PARKED ON EXPLICIT CLAUDE RESET. DIAGNOSTIC ONLY; no HCP LEC closure claim.

Original retained HCP kit on intel1:
/srv/opentallas-scratch2/claude/hbm-cores-kits-12/k3/kits/ot_hbm_hc_root_static__hcp_sys1_0690dba9b78d-_k12
Actual originals retained gold/gate AIGs, maps, aliases, hyp.json and failed lec.json.
Own complete scratch packet: intel1:/srv/opentallas-scratch2/claude/codex-hcp-0848.
No live own HCP job; no RTL, reset contract, timing or physical changes.

Baseline5 reconstruction exactly reproduces9658 comparisons:9246proved/412differs
and the identical original failure set. The inherited claim that all412 failures
have only d0[6..13] gold-only support is wrong. Exactly8 boundary NV failures are
that class; remaining404 include control and a false matched-register name.

Gold CMD_RST1 resets nlast_r low8 to0 and cmd_nchunk0x0a00/W256 loads256, so
all low8 remain0. d0[6..13] takes last_r?nlast_r[8:0]:256 every clock.
All16 gold constants have reset baseedge1 under the original4-cycle contract.
Proof4 directly replacing8nlast gold-gold equalities with constants and adding
8d0 constants proves526/526 joint obligations; full compare remains9262/9666,
404differs. This is NOT full equivalence. Original failed results remain intact.

The exact second root cause is a narrowed-vector name correspondence error.
Gate.map has ONLY nout_r[1] surviving; gold nout bit1 loads0 (cmd_nout=24),
while gold bits3/4 load1. At reset0 both gold/gate next states are0. At reset1:
  gold D = !cmd_valid && Q
  gate D = cmd_valid || Q
The truth table is in diagnostic/truth6.log. The gate cell named nout_r[1]
is a loaded-ONE state, not the gold loaded-ZERO bit1. Existing renamed() requires
at least2 disagreeing matched bits and misses this lone survivor. Minimal9-fact
candidate const-both:nout1=0 was correctly REJECTED by gate induction; never mask
its gate obligation with goldX or claim that candidate is valid.

NEXT PROPOSAL (NOT IMPLEMENTED / NOT RUN due reset): re-key the single gate
nout_r[1] as nout_r#t[1], then prove its actual correspondence to gold nout_r[3]
(or4) with reset base; gold nout_r[1]=0 and d0 low8 constants can then be proved
without constraining that incorrectly matched gate state. Keep all other original
hypotheses and prove every original compare/remaining hypothesis, with a wrong
correspondence/constant control. No change to RTL or comparison thresholds.

normalized.pkl is the immutable original normalized Lec object with474 original
hypotheses and0constraints, before candidates, at the own Intel1 run root. Use it
to avoid repeating mapping; original AIGs are in inputs/. The copied engine is
pinned source. Candidate_hints.json and prove.py are REFUTED/unfinished diagnostic
9-fact attempts, NOT hints for production adoption. Full diagnostic attempts1-4
and baseline5/truth6 retained on Intel1; no failed verdict overwritten.
