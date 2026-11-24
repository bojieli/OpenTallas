# S81-OPEN-CLOCK handoff (Opus 5.5; started 11-23 19:11 PST). FAMILY lane under S81-ALLFIX-INT.
Brief: localhost scratchpad s81_open_brief.txt (+ allfix_brief, rules, resume_1123b). Rows: hg-S81-CLOCK-SKEW, hg-S81-CLOCK-TAP, hg-S81-REACH, rc66. Deadline 22:00 PST.
Dirs: E9 /srv/opentallas-scratch2/claude/s81-open-clock (dumps d_{j8,b1,c6}, revert_c6.json, tapcount_c6.json, my_tail.sh); E10 same path (leaf_regen.sh, regen_c7a*, ops).
## 19:2x-19:4x
- FINDING posted: c6/c7a step LEAF-ALLFIX-1 r2_near resets 73 leaf types' clock.added_taps to J8 (3645 vs B1 6508): all TGR5 v4 leaf taps lost.
- STATES posted: CLOCK-SKEW 12/14 IN-BASE/IN-COMPOSE (planR2 lockup, HC-INPUT-REACH v3, VSW-LAG-1, CRR_PRE2, RHI); REACH 15 IN-BASE/IN-COMPOSE; rc66 IN-BASE (serdes taps 204->703); CLOCK-TAP lepe_nh_mus_C IN-BASE.
- ROW TGR5-LEAF-REGEN-1: E10 leaf_regen.sh (TGR5 v4 s1+s2, read-only tools) on c7a pre-tail aebbf78417d7. Run 1 (70 types) shard 7 died on t32 pre-existing anchor error -> run regen_c7a_b (69 types, no t32).
- Next: my_tail.sh (E9) = INT compose.py + tail on c7a + regen delta + t16 ops (serdes t16 R7 suggested clk_t53) -> PRE; then scoped strict bind on changed types; post ROW-REBASED to INT.
- My partial fork E11 s81-open-clock/tree.forking-149703 (stopped, 4K): ot-delete later.
