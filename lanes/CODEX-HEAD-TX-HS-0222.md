# CODEX HEAD TX and HSPLIT takeover 2026-11-08 02:22 PST

## CODEX notes

- TX ot_s81hd_sc_tx vH_fold_a2: routed database exists on epyc4 at /srv/opentallas-scratch2/claude/dh85txf/kit/ot_s81hd_sc_tx_vH_fold_a2/run/results/asap7/hbc_ot_s81hd_sc_tx/base/6_final.odb plus SPEF/netlist. Existing route audit failure was missing audit_pins.json; lane repaired and PIN_AUDIT PASS1059/1059. Existing route split: TT setup zero violations; FF internal18/-10.30ps, port122/-32.15ps. NOT SIGNED. No ECO used yet. Original TT450/FF364.5 virtual-clock reference preserved; no timing contract changes.
- Started own base signoff collection through intel2 ot-run pinned epyc4,48GB8T; own directory /srv/opentallas-scratch2/claude/codex-head-tx-0222/base_signoff; log intel2 /home/ubuntu/codex-head-tx-0222/signoff.log. It initially waits for memory, no duplicate started. Current frozen default margin policy retained per METHODOLOGY6.1 OWNER12.24c (setup0/hold25); stale older role60ps is superseded. This is collection of already routed results, not new route.
- Geometry final-DB render being generated in own review dir before one bounded internal-only ECO. Read-only dump first failed because container login shell omitted OpenROAD PATH; corrected to absolute executable. This is an infrastructure probe failure, not design failure.
- HSPLIT hd_host_e GRT finished earlier: TT+7.91ps; four internal hold endpoints worst-5.14ps; overflow0, LEC EQUIVALENT48105. HOLD_ROUTE retained; route requires die-owner go, no new launch.
- HSPLIT hd_host_w fixed kitsG LEC still active on intel2 at /srv/opentallas-scratch2/claude/dh85hs/kitsG/hd_host_w: dpkit-hd_host_w-1927812, hyp21 newly written, CPU100%,3.53GiB/40GiB. No lec.json yet. Earlier kitsF KEEP FAIL344differs5undecided remains preserved. Fixed kitsG still has lane0 FIFO address-count hypotheses; no verdict inferred. Next: collect EQ/FAIL; only EQ permits approved GRT screen.

## Next

Read base signoff and actual final PNG, assess all actual gates, then at most one strict ECO with nonport hold scope if eligibility agrees. Collect routed LEC. Keep DO_NOT_COUNT until source branch lands and re-signing on current tag is allowed. Preserve HSPLIT e route hold; read w LEC and launch one GRT screen only after EQ.

## Final route geometry viewed 02:4x

Actual6_final.odb dump, reviewed /home/ubuntu/codex-head-tx-0222-review/final_density.png. SMELLS8: same alternating hold-buffer stripes density0.6-0.9 in x15-165 and230-350,y5-65; adjacent columns0.3, no broad clump or macro channel. FF fold cones spread over full width, LA2 R four compact east blobs. Corner margin underuse mild. RUDY38.55max atx140,26.89mean, below vE overflow onset44. No macros; no macro/clock obstruction. Pin/clock exact timing remains base-signoff obligation; image is density/class/RUDY, not a false clock/pin visual claim. Verdict: suitable for one bounded near-miss ECO, subject to actual signoff eligibility. No route retry.

## Source class fix READY

Own source /home/ubuntu/codex-head-faceguard-0222, hub branch codex/head-faceguard-0222@c462697287. face_guard planned pin census now matches existing netlist skip_re, so a pins.json clock/reset entry does not become a false missing data port. Targeted pytest6PASS, missing-data negative control retained. No RTL/cycle/plan change. No merge.

TX compact capsule1.2GB staged E4->hub->intel1 includes actual final/route results, synth netlist, kit, logs and pinned tools. Only my own two unstarted signoff waiters were cancelled as admission changed (E4client3487147 then intel1 client exact printed by --cancel). Current single launch flexible ot-run --stage own capsule, log intel2 /home/ubuntu/codex-head-tx-0222/signoff-flex.log; output HOST:/srv/opentallas-scratch2/claude/codex-head-tx-0222/capsule/base_signoff. No physical retry, no old kit changes. Check actual selected host in log.

Base signoff first spill stopped before any corner STA: standalone source tools lacked clock_family.tcl, despite kit having it. Restored exact kit helper into own source bundle, preserving kit/RTL. New signoff-only collection log intel2 ~/codex-head-tx-0222/signoff-complete.log now admitted spill epyc6, output capsule/base_signoff_complete; written results copy back intel1. NOT a P&R retry/ECO; no ECO yet.
