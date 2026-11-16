# HEAD-SERDES-O handoff (Opus successor of FABLE-FIX-HEAD-SERDES) 11-16 ~03:30 PST
Goal: sign off hd_serdes (s81_head): DRC 0, TT setup >= -42 ps, FF non-port hold >= 0, LEC.

## Where things are (epyc10 /srv/opentallas-scratch2/claude/fable-fix-head-serdes = W)
- Branch claude/head-serdes-fanout-1116 @3176b99392c PUSHED (on main c03ba6c3b9). W/repo is a SPARSE checkout of it.
  - ab32fbbe30 fanout copies DNGB 12 + RMRPC 32 (+0 cycles)
  - 3176b99392 DKREG 1: k_* seam register in front of hard u_chn in ot_s81_kp4_dec, ddly DDX 1 (DD 55->56), +1 pma_rck RX
  - only ot_s81hd_serdes_link(_ls).sv set the params; S81 defaults unchanged.
- Bench W/sim2 (bench script W/bench2.sh, log intel2 ~/head-serdes-o-logs/bench2.log): PDIE_FANOUT_EQ PASS (incl DKREG form,
  DKREG_MUT_NODD FAIL, RMRPC_MUT_STALE FAIL), PDIE_LINK_GATE PASS.
- ot-gate-remote (epyc2): INFRA MISSING SOURCE physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v
  (queue defect). Asked MERGE-QUEUE-1 to fix; READY only after a GREEN gate. Rerun:
  ot-run --mem 48 --threads 16 --hosts epyc2,epyc9 --dir /srv/opentallas-scratch2/claude/mq-gate -- bash /srv/opentallas-scratch2/claude/mq-gate/ot-gate-remote claude/head-serdes-fanout-1116@3176b99392c45b2dd3f2f1687019edba58edbae8 16
- HEAD-100 asked (ASK post) to price +1 pma_rck and name the LATCHECK row; then bind + LATCHECK on kit RTL before READY.
- W/tree5 = hardlink copy of TOOLS-CONVERGE pin tree kw45/src_head_pin_e594a73db756 + the 43 files that differ e594a73..branch
  (script W/mktree5.sh). NOTE: cp -al shares inodes with the pin tree: NEVER write in place in tree5 (rm + write), never chmod.
- W/sd5 = kit from tree5 (W/gen_sd5.sh, log W/gen_sd5.log): plan NF13a, kit RTL W/sd5rtl (attempt_6 bootstrap + branch files),
  env = s81_head die_gen_env + OT_PG_DIE_PHASE=1 (M7 offset 8.448) + OT_PGCAP=1 + OT_TT_SETUP_REPAIR=both, no private leaf.
  Running from synth on epyc10: ot-run --mem 64 --threads 12 (log intel2 ~/head-serdes-o-logs/sd5.otrun.log), goal route.
- W/sd3: control kit (sd2 CTS DB + C3b + GRT repair keep-if-better + private leaf), in GRT TT repair (before -73.04).
- W/sd4: superseded, not launched.

## Next
1. sd5: read CTS/GRT TT repair numbers (tt_setup_repair.log, keep decision), route DRC, then signoff.py (TT setup, FF hold, LEC).
2. GREEN gate -> READY to MERGE-QUEUE-1 for the branch.
3. If sd5 TT still < -42: classes from the reloaded GRT DB (W/diag/classes.tcl pattern), next structural form.
