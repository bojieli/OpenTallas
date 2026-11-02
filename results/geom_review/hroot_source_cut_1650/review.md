# Hroot unchanged source/pin graph: independent infeasibility LOOK

Personally LOOKED source_preserving_cut.png and exact_constraint_cut.json at
/srv/opentallas-scratch/claude/codex-kv-hroot-reset-preserve-1131. Under the two
actual fixed pin<=150 obligations and four existing sequential hops<=405,
triangle inequality permits at most4*405+2*150=1920um between fixed pins.
Measured L1 separation2192.120um leaves272.120um deficit. The actual shared
rrl101.q fork has two2-hop branches (HBM ist3.eq/bout.eq and CTL ist0.eq/bout.eq).

This rules out pure placement of the unchanged source/pin graph even with
freely movable zero-area FFs. Real footprints, obstacles and clock restrictions
cannot improve that bound. No sweep is warranted for that alternative.
Source/parent interface event is required; no reset repoint, extra FF/cycle,
clock/pin relaxation, conditional reset projection or boot/START gate credit
is granted. Existing failures and all semantic qualification holds remain.
