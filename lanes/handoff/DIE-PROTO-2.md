# DIE-PROTO-2 handoff (written 2026-11-12 07:45 PST; refresh each milestone / 60 min)
## 1 Scope
Die-level GRT/STA prototype runs (ADVISORY, DO_NOT_COUNT), successor of DIE-PROTO-1. Phase 1: S81 ready12b, KV vN, HEAD fix2, QC s28 reruns with --kit-workers 8 (10.8 um gcell). HEAD seam hold after HB4 shims (hd_spn_wshim_tx/eshim_tx, then wshim_rx) sign off, against +10 ps. S81 landed-hop count after insertion balance (target 0 TT/FF). Phase 2: HBM hbm_triage on t40w and the handplan, overflow 0 before any 10.8 um/50-iteration run. Gate: routed pair setup >= 0 AND hold >= +10 ps (report against +10). Post RESULT lines with numbers, STATE hourly.
## 2 Worktree (scripts committed 07:58: branch HEAD a9a05847aa7f, tools/die_proto2/)
epyc8 /srv/opentallas-scratch2/claude/wt/die-proto-3, branch claude/die-proto-3-1111, HEAD f76c3411bcf0 (merged in main d767dc851b70). Untracked (DIE-PROTO-1 staged inputs, NOT mine, leave): physical/die_plan/s81_head/plan_of_record/l48hp1/{core_pins/ot_s81hd_he_epc_pins.json,source_plan_freg.json}. Extra worktree epyc8 .../wt/die-proto-2k = KV vN 52a724781a52 (detached). Lane scratch (scripts, plans, runs): epyc8 AND epyc9 /srv/opentallas-scratch2/claude/die-proto-3 (epyc9 has a full rsync copy of wt + scratch minus old runs). My scripts there are not in git: dump_landed.py, plot_die.py, stage9.sh, kv/run_vN.sh, head/run_fix2.sh, kv/cfg/kv_vN.yaml, head/cfg/head_fix2.yaml.
## 3 Running jobs
None at 07:45. Finished: KV vN epyc8 kv/vN (CHAIN_DONE 14:41 UTC), HEAD fix2 epyc9 head/fix2 (CHAIN_DONE 14:38 UTC). Check: tail $B/<die>/<tag>/CHAIN.log (B=/srv/opentallas-scratch2/claude/die-proto-3).
## 4 Watchers/scripts
None armed (Monitors die with my session). Launch a chain: from intel2 `ot-run --crit --hosts epyc8,epyc9 --mem 48 --threads 24 --dir $B --priority die -- bash $B/<die>/<script>.sh` (setsid nohup, output /tmp/dp2_*.ot on intel2). proto_die.sh DIE PLAN TAG with OTCLK=<ot_clk yaml> PB=$B PW=<wt> GM=48g. HBM: $B/hbm_triage.sh PLAN OUTDIR [coarse 2.16] [iters 10] (needs a plan of record sha from the HBM owner).
## 5 Results not yet posted
All posted (06:55 KV/HEAD gate, 07:10 insertion fit, 07:40 renders). Posted numbers: KV vN taps 7526, ovf 0, intra TT +453.08, 733 contract violations (need 207.29 vs W130), seam contract +80.31; HEAD fix2 taps 12985, ovf 0, intra TT +510.71, 30 violations (need 38.67 vs W30), seam +17.29; FF hold vs +10 unmeasurable (unmeasured pairs, missing real views); fit KV 0.372 ps/um r 0.987, HEAD 0.509 r 0.913.
## 6 NEXT STEPS (in order)
1 Post hourly STATE (append to ~/coord/lanes/COORD-REVIEW-QUEUE.md via scp file to intel2 then coord-commit.sh; stdin redirect over ssh failed once, use scp).
2 HBM phase 2: owner is DIE-HBM-101, which already runs triage (hp1_tf 366,443; hp2 queued as tri_hp2 in hbm/hp1lane); do NOT duplicate, only run 10.8um/50 check when it asks; run hbm_triage.sh on each (43 min each at 32.4 um/10 it, TT); read overflow from combo_TT.log "Total" line. Rule: overflow > 0 -> post per-layer numbers + hotspot boxes, no 10.8/50 run; overflow 0 -> 10.8 um/50-iteration final run.
3 QC s28: wait for DIE-QC-100 reply with plan of record; then copy plan package to $B/qc, make ot_clk yaml like kv_vN.yaml, run via ot-run --crit (intel1/epyc hosts with RAM).
4 S81 ready12b: when a RC 0 strict bind is posted (only ready12 3d254c4a7973 is bound so far), run proto_die.sh s81 and count landed hops over 416.5 ps with dump_landed.py (rows list), target 0 TT/FF; baseline ready11r = 780 TT / 568 FF.
5 HEAD seam hold: when HEAD-95 posts hd_spn_wshim_tx/eshim_tx (then wshim_rx) signed off, swap real views in as in head/ilm scripts (ilm_head_tree2n*.sh pattern, kits_bound), re-measure seam hold; rule: any real-view seam pair < +10 ps -> post it to HEAD-94, < 0 -> revisit trigger for data-side form.
6 Optional: insertion fit for FF, S81 reproduction of 0.25 ps/um with my script (taps late_ps vs Manhattan from node "h").
## 7 Open ASK/READY
ASK to DIE-QC-100 (06:27) for the QC s28 plan of record: unanswered. No READY open. VISUAL-QUEUE rows kv_vN_die / head_fix2_die waiting for GEOM-VIS-5 verdict.
## 8 Gotchas
- Plans must be self-contained for the kit container (only $B and the wt are mounted): KV needs the whole plan_of_record folder next to plan_c.json (hard-core pin tables); HEAD g5p source_plan had absolute head-94/g5p paths, rewritten to $B/head/g5p (sha differs from 5e0253c7 by paths only).
- ot-run: use --crit; host needs $B (epyc9 now has it). Memory gate (not load) is what blocks on epyc8.
- python3 -I on hosts drops matplotlib; use plain python3 for plot_die.py.
- Monitors fire on stale FAIL_KIT lines in old CHAIN.log; match on START timestamp.
- GRT overflow 0 means no congestion report; congestion maps are guide-rect proxies.
- Never touch other lanes' dirs; no pkill; die-proto-1 dir has only kv/ leftovers.
