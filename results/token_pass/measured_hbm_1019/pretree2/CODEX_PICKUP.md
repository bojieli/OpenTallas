# PRETREE2 pickup

Pinned existing builds2332523/2332525 and chain2364203 are preserved.
The scratch collector was redirected from the paused Claude worktree to the
Codex worktree. Its original bytes are saved beside it as
collect_pt.claude_original.sh. collect_pt_codex.sh preserves the new exact recipe.

Collection is blocked unless all12 pre-tree records and all4 regressions have
SU_TOP PASS without SU_TOP ERROR/FAIL. All6 mutation runs (corrupted input,
join-pairing1024 and unbound pre-tree, each for two production shapes) must
produce actual SU_TOP ERROR and FAIL, without PASS. Crashes or missing markers
never qualify. The acceptance JSON records every predicate before timing update.

Golden-order contract: prod_compile --pretree emits aligned model csum8
subtrees and ((Q0+Q1)+(Q2+Q3)); compilation asserts each row against the model.
Actual RTL exactness and causal witnesses are still pending. The8-row exp_sum
entry remains an affine law from1/2/3 rows; it must retain that label even if
those measured records pass. No rate or physical closure is established here.
