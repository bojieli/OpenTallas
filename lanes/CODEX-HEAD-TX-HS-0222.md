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

## Full TX result and structural successor

Actual uniform signoff completed NOT SIGNED on own intel1 /srv/opentallas-scratch2/claude/codex-head-tx-0222/capsule/base_signoff_complete (E6 spill copied back), unit oth-ubuntu-3167870-1794134101: TTsetup+12.90ps; FFhold-32.15/140endpoints (internal18/-10.30,port122/-32.15), TT/FF relatedskew56.8/50.8ps; DRC0antenna0; SDC/faceguardPASS. Additional blocker omitted by earlier route-split report: slew1740TT/917FF pins. Actual ODB mapping0unmapped ->919TT/580FF unique slew NETS. TT53nets>200um,833at100-200um,33at50-100um; FF48>200um,532at100-200um. Most drivers weak BUFx3(517TT)/INVx1(157TT)/OR5x1(94TT), FO1-4. TT sink families305cq,167p_d,81wb,18d0,348comb. CLASS DRIVE/WIRE, large miss; NO ECO STARTED. The apparent local hold near miss was incomplete. Exact mapping CSV/JSON + actual final PNG: epyc4 .../codex-head-tx-0222/review and hub /home/ubuntu/codex-head-tx-0222-review. Old failure evidence retained.

New source hub codex/head-tx-regional-src-0222@c4a3b7d429, based TX branch da608fea4a. Own sparse clone /home/ubuntu/codex-head-tx-regional-src-0222. Opt-in CH_REGION4(default0):4kept520bit CH_STAGE capture banks feed their own cq regions, sameedge, +1560regs, PIN CYCLES0. Physical helper tools/s81_head/head_tx_regional_layout.py pairs8mid/cqbits per16sink atomic group, re-groups internal d1..d8+p_d/PMA chains beside output slices, leaves d0/finalPMA face flops. RTL smallest lockstep vs originalFOLD0: continuous1578words/157parity, stallreset1550/154,0mismatches. Regional copy mutant7 caught37mismatches/378words. Bench unit intel1 oth-ubuntu-299355-1794134718 exit0; logs /srv/opentallas-scratch2/claude/codex-head-tx-regional-0222/{continuous,stall_reset,mutant7}.log.

Actual proposal PNG VIEWED hub /home/ubuntu/codex-head-tx-regional-packet-0222/proposal.png. Review in own kit results/geom_review/preplace.txt. Four banks, no macros/walls, local pairs0.54um; source ch_n shared reach ~300um remains an electrical risk (cannot claim replication alone fixes all long wires). Verdict ONE PLACE PILOT ONLY, no CTS/GRT/route until actual placed density + driver reach read. Own kit intel1 /srv/opentallas-scratch2/claude/codex-head-tx-regional-0222/kit; HOLD_ROUTE/DO_NOT_COUNT. Single ot-run48GB8T queue, log intel2 /home/ubuntu/codex-head-tx-0222/regional-place.log; initially waits on intel1, no duplicate or direct-bypass. Source SHA ready for collection, NOT merge-ready until pilot physical read.

HSPLIT w fixed LEC stillhealthy100%CPU,hyp26 at lastread. Preserve e HOLD_ROUTE (requires owner go), no e/w route launched.

## Corrected physical form B (supersedes initial regional proposal)

Geometry budget caught before PLACE: old DFF area0.2916um2 on0.27um rows =>1.08umwidth, so initial0.7um bankpitch was invalid. I stopped only own dpkit-kit-516061 before PLACE, no completed synth DB, own kit/STOPPED_PREPLACE.json retains reason. Source helper revised through465f896d02 to latest cbca72f096 (same RTL as bench):1.15um CH pitch, bank origins32+100r,y44; data/PMA4lane spacing8um, y10..37. Flop fill1670/4240~39.4%;7um open channel separates CH banks. Newcaptureflops add455um2 to20433um2 baseline ->35.5%overallfill. Actual proposal_vB.png VIEWED; record own kit_vB/results/geom_review/preplace.txt.

Current ONE PLACE pilot, new corrected form, own intel1 /srv/opentallas-scratch2/claude/codex-head-tx-regional-0222/kit_vB. Unit oth-ubuntu-672842-1794135442 admitted immediately48GB8T. Log intel2 ~/codex-head-tx-0222/regional-place-vB.log. KIT_PREFLIGHT PASS, early synth stage; HOLD_ROUTE/DO_NOT_COUNT; never advance to CTS/GRT without new actual density/driver-distance image read. Current source hub codex/head-tx-regional-src-0222@cbca72f096; no merge/tag/PORchange.

HSPLIT fixed w LEC hyp29 at lastread, healthy (original process retained), no EQ/FAIL receipt yet. e HOLD_ROUTE preserved.
