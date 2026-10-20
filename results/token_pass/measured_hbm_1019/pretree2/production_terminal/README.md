# PRETREE2 exact-file runtime evidence

All 12 production PRETREE records and four regression records pass the actual
full-shape direct RTL binary, Verilator 5.050, source a5cc6f083. These are model
csum8/ordered-max goldens, rather than the old calendar-order reduction.
`exact_file_acceptance.json` names and hashes every selected log. It intentionally
reports `original_six_negatives_all_causal=false` and `timing_adoption=false`.

The original data-QW negative and both PRETREE-unbound negatives produce real
numeric ERROR and FAIL. The original DS data corruption targets read777 while
the fixture has160 reads, so it is inactive. Both original join-pairing mutants
pass their fixtures: these are preserved as insensitive results. Directories
also preserve copied baseline logs; the checker selects the exact mutant
filename instead of concatenating those baselines.

The sensitive production-shape DS q_norm1280 fixture uses first join operands
4096,1,2,3 (squared leaves2^24,1,4,9), all other seed words zero. The independent
model expects4b800006: canonical (2^24+1)+(4+9) rounds to2^24+12. Baseline PASS;
actual RTL MUT1024 returns4b800007 at scalar edge197 and VM edge236, FAIL2.
The active data mutant changes the first actually filled seed word4096 to0,
keeping the independent expectations. It returns41600000 (14) at the same
scalar/VM edges, FAIL2. Programme retires at236+WR10=246, minus dispatch4 =242
serial edges. This uses existing binaries; no additional whole-SU build.

The original SFU32 fixture's join-pairing mutation remains insensitive; the
sensitive DS fixture establishes the common pre-tree join arithmetic mechanism,
not a separate causal SFU32 topology test. No affine8row capacity law, complete
die integration, native-cell functional equivalence, rate or SS/FF closure is
claimed. The separate phase4 packet proves actual no-reset2+2row execution,
1422 charged serial edges,4098 reads/writes,16 scalars and two phase2 failures;
its scheduled nonalias certificate records zero prior-write conflicts.

Runtime directories are ot-epyc5:
/srv/opentallas-scratch/claude/hbm-pretree2/suvop/{vec_pt,vec_ptreg,mutw,codex_qw4}.
Pairing fleet unit is recorded in sensitive_qnorm/fleet_pairing.log; active
first-fill fleet unit2427342-1792485254. Exact logs, including wrapper exit0
for expected-negative suites, distinguish actual DUT FAIL from process status.
