# HEAD-SERDES-O handoff (Opus successor of FABLE-FIX-HEAD-SERDES) 11-16
Goal: sign off hd_serdes (s81_head): DRC 0, TT setup >= -42 ps, FF non-port hold >= 0, LEC.

## Where things are (epyc10 /srv/opentallas-scratch2/claude/fable-fix-head-serdes = W)
- W/repo: branch claude/head-serdes-fanout-1116, rebased on origin/main c03ba6c3b9 (not pushed yet):
  - ab32fbbe30 fanout copies DNGB 12 (KP4 PE groups 4->12) + RMRPC 32 (rate-match read select copies), +0 cycles
  - 3176b99392 DKREG 1: register on k_v/k_lo/k_L/k_any in front of hard u_chn inside ot_s81_kp4_dec, ddly DDX 1 (DD 55->56),
    +1 pma_rck RX latency (pre-approved; HEAD-100 asked to price it + name the LATCHECK row)
  - only ot_s81hd_serdes_link(_ls).sv set the params; defaults unchanged for S81.
- Benches: W/sim (pre-DKREG): fanout eq PASS (differ 0) + mutant FAIL; link gate serdes/ucie PASS, DMUT2 FAIL, KP4 PASS.
  W/sim2 (rebased, with DKREG form + DKREG_MUT_NODD mutant): running, log intel2 ~/head-serdes-o-logs/bench2.log.
- W/sd3: control kit (sd2 CTS DB + C3b + GRT TT repair keep-if-better, private leaf), in GRT TT repair (before -73.04).
- W/sd5: NEW kit from main tools (W/repo) + plan NF13a + kit RTL W/sd5rtl (wave attempt_6 bootstrap + branch files),
  gen env = s81_head die_gen_env + OT_PG_DIE_PHASE=1 + OT_PGCAP=1 (OT_TT_SETUP_REPAIR=both). Script W/gen_sd5.sh, log W/gen_sd5.log.
- W/sd4: old hand-copied kit (fanout RTL only), superseded by sd5; not launched.

## Next
1. bench2 green -> push branch, ot-gate-remote, READY (RTL) to MERGE-QUEUE.
2. sd5 full run to sign-off via ot-run (run_kit.sh sd5/hd_serdes route 64 12); check DRC, TT, FF hold, LEC.
3. bind + LATCHECK on the kit RTL once HEAD-100 names the row.
