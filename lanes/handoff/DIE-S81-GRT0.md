# DIE-S81-GRT0 handoff (2026-11-14 ~21:50 PST)
## Scope
First S81 die-level GRT + die STA prototype on the plan of record (ADVISORY, DO_NOT_COUNT). Owner approved die GRT/STA prototypes.
## Tooling found (existing, nothing new written)
- tools/die_plan/die_trial.py kit (abstracts + clock + route.v), combo GRT via mk_combo_kv.py (signals M4-M7 ADJ 0.75, clock M8-M9, 50 it, TT+FF), trial_tap_arrivals.py, die_sta_related.py (--cppr-lca, --core-insertion declared, --kit-window-out), typepairs.py.
- Chain used: FABLE-REVIEW-CLK proto_reg.sh (intel1 /srv/opentallas-scratch2/claude/fable-review-clk) = proto_die.sh with the regional clock (ot_clk.py kit, yaml s81_r98.yaml: 98 landed regions of the sidecar, spt link feed, DME delay per region). Earlier runs: DIE-PROTO-1 B1 plan (die-wide tree: GRT 0 overflow, STA -470 clock-only), FABLE-REVIEW-CLK r98 on B3t/B3v (GRT 0, intra TT +420.3, seam +363.9, landed FAIL).
## Plan used
B6a/B6b/B6c G0 RC=1 (no finished bind), so plan of record B3x2d (epyc8 s81-b3-clk/run/b/B3x2d, bind RC0, plan_h2_2249.json sha256 97e1ec17edbd). Plan-shape abstracts for all 398 partitions; NO signed views fed (same as earlier S81 runs; die STA hold stays BLOCKED(kits)).
## Setup (epyc10)
W=/srv/opentallas-scratch2/claude/die-grt0-s81: src = hardlink copy of B3v/src with physical/die_plan/s81 + tools rsynced from B3x2d/src; in/regions.json from B3x2d sidecar_new.json (98 regions), in/feed.json from locality.py score --feed spt, s81_b3x2d.yaml, run_die.sh (calls proto_reg.sh, GM=96g), out s81/b3x2d.
## Launch
~/dgrt0_s81.ot on intel2: ot-run --mem 100 --threads 24 --hosts epyc10 --priority die (--priority plan is refused by ot-run for non-bind scripts). Queued: epyc10 admits 22 GB (load 268/96, 91 running). Local waiter dgrt0wait.sh polls CHAIN.log for CHAIN_DONE/FAIL_KIT.
Prior runs: kit ~66 min, GRT ~11 min at 18.7 GB RSS, STA ~15-25 min.
## Read results
$W/s81/b3x2d/CHAIN.log; grt_st_TT/combo_TT.log (overflow table, Maximum resident set size); sta/ summary; kitwin.json; typepairs.json.

Update 22:0x: moved to epyc8 (unit oth-ubuntu-3985401-1794721449, --mem 32); epyc10 queue entry cancelled; run dir epyc8 same path.
