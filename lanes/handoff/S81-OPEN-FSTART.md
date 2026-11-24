# S81-OPEN-FSTART handoff (row FSTART-DEPTH-CLASS)
- Tool: tools/die_plan/fstart_depth_fix.py + test, main e74ea5316f37 (scan / fix / apply). Copies: E9+E10 /srv/opentallas-scratch2/claude/s81-open-fstart/tool/.
- Scripts: E9/E10 /srv/opentallas-scratch2/claude/s81-open-fstart/{fix.sh,pre.sh,scan.sh,fix_t16.sh}; outputs out/<tag>/.
- B1 ae3101241d6b (E10 b1_tree): flags exactly the 23 refused types (45 entries); out/b1 ops_fsd.json 2c32eae255ed (44 repicks, 300 um) + t16 fstart_1 patch at 405 um (out/b1 ops_fsd2.json).
- c7a pre-tail aebbf78417d7 (E9): 34 entries/11 types incl NEW leaf t43; out/c7a_pretail ops 6bf3224b356c, same t16 fstart_1 at 398.6 um.
- Next: PRE on B1 row -> ASSEMBLY (asks it to run scoped strict in its b1_tree); c8: run fix on INT post-tail p4_fill (tool = last tail step).
- 11-23 23:5x c8 DONE: p6_fstart.json d11e3b6c50ee, report 4ffdfd02f9ef (39 re-picks/13 types, 0 unfixed, re-scan 0 left); site TSV E9 out/c8_repick_sites.tsv 6fbe87a3064d. B1 row in B1-FIX 6c09e8b293af (scoped strict PASS 23/23; full strict b1fix2_full on epyc11 is not this lane). Supersedes "Next" above. Open: PRE + strict on c8 = S81-ALLFIX-INT post_and_gate_c8.sh; seqhost__t1 unscanned; re-scan if a later step moves reset stations.
