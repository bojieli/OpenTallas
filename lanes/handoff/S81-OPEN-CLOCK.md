# S81-OPEN-CLOCK handoff (Opus 5.5; started 11-23 19:11 PST). FAMILY lane under S81-ALLFIX-INT.
Brief: localhost scratchpad s81_open_brief.txt (+ allfix_brief, rules, resume_1123b). Rows: hg-S81-CLOCK-SKEW, hg-S81-CLOCK-TAP, hg-S81-REACH, rc66. Deadline 22:00 PST.
Dirs: E9 /srv/opentallas-scratch2/claude/s81-open-clock (dumps d_{j8,b1,c6}, revert_c6.json, tapcount_c6.json, my_tail.sh); E10 same path (leaf_regen.sh, regen_c7a*, ops).
## 19:2x-19:4x
- FINDING posted: c6/c7a step LEAF-ALLFIX-1 r2_near resets 73 leaf types' clock.added_taps to J8 (3645 vs B1 6508): all TGR5 v4 leaf taps lost.
- STATES posted: CLOCK-SKEW 12/14 IN-BASE/IN-COMPOSE (planR2 lockup, HC-INPUT-REACH v3, VSW-LAG-1, CRR_PRE2, RHI); REACH 15 IN-BASE/IN-COMPOSE; rc66 IN-BASE (serdes taps 204->703); CLOCK-TAP lepe_nh_mus_C IN-BASE.
- ROW TGR5-LEAF-REGEN-1: E10 leaf_regen.sh (TGR5 v4 s1+s2, read-only tools) on c7a pre-tail aebbf78417d7. Run 1 (70 types) shard 7 died on t32 pre-existing anchor error -> run regen_c7a_b (69 types, no t32).
- Next: my_tail.sh (E9) = INT compose.py + tail on c7a + regen delta + t16 ops (serdes t16 R7 suggested clk_t53) -> PRE; then scoped strict bind on changed types; post ROW-REBASED to INT.
- My partial fork E11 s81-open-clock/tree.forking-149703 (stopped, 4K): ot-delete later.
## 19:5x
- regen_c7a_b DONE: E10 regen_c7a_b/plan_s2.json 093fb7633726 (copy E9 plan_tgr5_leaf_c7a.json), 62 types +2712 taps, FIXCHK PASS. ROW BUILT posted.
- rc66 ops E9 ops_t16_dens1.json 4c61a4e8438a.
- E9 unit oth-ubuntu-1681604-1795491483: my_tail.sh recipe_oc1.json oc1 scope_types.txt -> tail_oc1/ (compose ff7ee10ae698 OK, then relay/LLR/fill/deadin/anchor/census/PRE allfix2/scoped strict 70 types). On finish: post ROW-REBASED to INT with PRE + scope bind result; if ANCHOR/PRE flags leaf types, compare vs INT j9tail_c7a.
