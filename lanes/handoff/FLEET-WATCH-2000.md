# FABLE-FIX-S81-LEAF-R2 handoff (Fable; succeeds FABLE-FIX-S81-LEAF 2026-11-20 23:05 PST; owns ot_s81sl_leaf__t*, rep t39)

Read order: this file, lanes/posts/FABLE-FIX-S81-LEAF-R2.md, then lanes/handoff/FABLE-FIX-S81-LEAF.md (predecessor; its STAND-DOWN section still describes the units).
Nothing is signed. No t39 kit carries CFX or an FSTART fix yet.

## Work roots
- epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3 (B, predecessor: p1, p2, cfx bench, rd.sh = post-hook read).
- epyc7 + epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r2 (mine): epyc10 keyfix11/, epyc7 c2d/ (copy of J6 candC2d plan + tools, no native_bind) and fstart/.
- Rows: intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-rows-1120 (R).

## Results (post-hook only)
- p1 (reset legs + 200 um tap pairing, overfull grow 0.3): LOSES. setup -259.66 / tns -54,012, hold -85.39 / -99,985 (control a3 -73.73 / -1,278 and -75.14 / -89,488). clk_t20 ends at insertion 583.7, in-tap skew 182.7; worst paths vp src -> src out of it. Neither part goes into the t39 form. Posted 23:2x. p1 still runs to route (predecessor's unit, not signalled); its pregrt hold class counts are owed to TAP-GRID-R2.
- p2 (relay keys only): not at post-hook yet at write time. Read: bash B/rd.sh B/p2/gen/ot_s81sl_leaf__t39, compare with a3.
- Relay keys on the J6 bind rtl (candC1d out/rtl): the 69 old types unchanged; 9 more types need the rename (t3 t9 t10 t23 t28 t40 x2 t71 t75, 225 keys), t31 matches. Add-on delta R/j6_delta_leaf_relay_sites_keys_addon.json (450 ops), posted to J6. phy__t1 "unresolved 112" is a tool false negative.
- CFX bench: 6 no-define runs read (5 PASS, control fails as it must); XR / SRAMREG / XR+SRAMREG variants still building (unit oth-ubuntu-2404029-1795240504, B/cfx/out/summary.log). Owed to S81-J6-ASSEMBLY before its bind with the define.

## FSTART (u_rrl_282 -> u_cland_fstart_ft4_o, -67 on a3)
All three FSTART face flops of t39 take cland_start_raw = rst_n_t21 and cland_start_d from u_cland_origin at (17,1210); ft4_o sits at (5,135), 1,075 um away. The plan already has the knobs (15 S81 types use them, leaf t47 / t75 among them):
- clock.landing_writer_start {depth W, branches {ft4_o: {stages [{xy_um, raw_reset}]}}}: registered START relays to the far FSTART pin; the receiver strap K takes +W at the bind (boot cycles only, 0 data cycles);
- clock.landing_local_resets: same-cycle local reset copy for the face flop (0 cycles).
The fixed script is tools/die_plan/reach_rules.py fix --rules 1 (R-REACH-1 start_fan); fstart_reset_delta.py makes the local resets from a strict bind. No private RTL relay is needed, and a hand relay would not pass the bind.
In flight: copy of candC2d to epyc7 c2d/, then reach_rules check / fix --rules 1 --types leaf -> FSTART row for the whole leaf family as a J6 delta. The row changes strap ties, so it needs the J6 strict bind + LATCHECK; the t39 sign-off kit then comes from the J6 tree.

## Open, in order
1. Read p2 post-hook, post it. Read CFX XR / SRAMREG variants, post to J6.
2. FSTART row: finish reach_rules fix, make the j6_donor_delta, post to S81-J6-ASSEMBLY before 11-21 13:00 (after that it is J7).
3. t39 kit from the J6 tree once it carries CFX + keys + FSTART; place log must print 'plan keys unmatched: 0 of 25'; route, DRC 0, TT >= -42, FF hold >= 0, LEC, AUTO-EXPORT.
4. p1 pregrt hold classes -> TAP-GRID-R2 (their t39 55 -> 98 tap solve is the real hold fix for the clk_t6 bank).
5. Cleanup with ot-delete when the proofs end: B/leg/j5odb, B/whatif, B/rows9, sib dirs (epyc7 / epyc9), my c2d copy.
## Update 11-20 ~23:55 (stand-down)
- Push: attempt 4 tests passed but rejected (main moved); rebased; attempt 5 (push5.log, --test-timeout 3000) was running with commits 405a3ab370 (NOPROG etc.) + 86fd5bbe04 (oom-age). UNCOMMITTED on top: tools/autopilot/kit_wave.py superseded_unstarted + LAUNCH-SKIP SUPERSEDED in the infra-relaunch loop, test_launch_skip_superseded.py (passes). Next: wait push5, commit, git fetch+rebase origin/main, ot-push-main again.
- Owner rule 23:2x (old-plan unstarted rows): kit_wave part done as above; first-tick count 0 on every die (old-event rows are all running or cancelled). Waiter part: 10 unadmitted wave waiters host-side, 4 old-event, 2 with a live current row (s81 dsdv_slice_c1x_C__t6, t8, 48 GB). Skip at admission NOT built; waiters run the pinned kw44 ot-run copy; do it in kit_wave (withdraw unstarted queue job via wave path) or ot-heavy by tag. Posted to FLOW-NOADV-R4.
- FRAC 0.8 trial on epyc2/epyc8 (start 21:59 PST): result waiter task bk2x7bgb4 printed to its output file at ~23:59; decide: kills halve and admits >= 70% of baseline -> 0.8 on all hosts, else restore from /etc/ot-heavy.conf.bak-fw2000-frac05-1121. POST THE RESULT; I have not.
- Still open: epyc2 root (/home/ubuntu/scratch-root/claude 2.8 TB; per-lane du in /tmp/fw2000_duc.txt on epyc2), probe-dir deletions via ot-delete, PLACE-SETUP-STOP re-check.
