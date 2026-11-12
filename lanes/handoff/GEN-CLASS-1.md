# GEN-CLASS-1 lane handoff (refreshed 2026-11-12 ~09:1x PST)

## 1 Scope
Generator / legalize / preflight CLASS fixes. APPROVED to merge (ROOT-MERGE-60): land-override-stale-1112@cef99b3203,
cland-slew-1112b@33e70e1695, street-fixedface-1112@a07f957bc5, preflight-sidecar-macro-1112@ad7c108277.
ACTIVE: FT-HOP-M2-WIRE class fix (COORD-approved plan (1)): post-GRT repair_design -max_wire_length 110 limited to
ft-station hop nets (other nets dont_touch, restored), 0 cycles. Do NOT do the guide-rewrite M4 floor unless (1)
leaves violators (per-net layer range does not exist in OpenROAD 26Q3-1510).

## 2 Worktree
intel2:/srv/opentallas-scratch2/claude/wt/gen-class-1, branch claude/ft-hop-m2-1112 (from hub/main d767dc851b7),
NOT yet committed: tools/die_plan/ft_hop_maxwire.tcl (new), grt_pre.tcl (sources it), gen_phys.py
(FT_HOP_MAXWIRE_UM=110, armed when the type has ft_slots, partition_types.<t>.ft_hop_maxwire_um override, 0=off),
schema.py (ft_hop_maxwire_um), test_ft_hop_maxwire.py (5 pass). Ignore the untracked ARCHIVED.json files (not mine).
Commit when the suite run (below) shows only pre-existing failures.

## 3 Running jobs
- wshim_tx proof DONE + SIGNED (STATE 08:51 posted): slew 125/124 -> 0, M6 +4.7 pt. Kit epyc2:/srv/opentallas-scratch2/
  claude/gen-class-1/proof/wtx/hd_spn_wshim_tx (keep until HEAD-95 adopts or drops).
- S81 slice_station__t45 GRT-only proof: client intel2 pid 950019, host epyc2, kit
  epyc2:/srv/opentallas-scratch3/claude/gen-class-1/proof/t45/slice_station__t45, log intel2 ~/gc1log/t45_ftmw.log.
  epyc7/epyc8 attempts were killed (exact PIDs) because of load gates.
- Code: claude/ft-hop-m2-1112@3bf9f167d4 pushed.
## 4 Watchers
None.

## 5 Results not yet posted
- t45 GRT proof (pass expected near no-op after the base 62-um repair); then post FT-HOP-M2 READY.
- Posted 08:14: READY claude/tcl-puts-quote-1112@475f0c5d0e (TCL-PUTS-QUOTE class).
- Base GRT usage: wshim_tx M2 3.26 M3 0.02 M4 0.02 M5 0.01 %; t45 M2 4.14 M3 4.70 M4 2.67 M5 0.21 % (GRT-0096,
  first full route). Compare fix with the same table + route.guide per-layer + 5_2_route per-layer wirelength.
- S81 slice_station slew violators (t45 a14, 1158) are cland ring nets with fanout 128-160 (u_cland_ft*_i place
  buffers), NOT ft hops: a CLAND fanout class, report to COORD with the READY.

## 6 Next steps
a. When wshim_tx signoff done: count TT/FF slew pins (signoff/tt/sta.log "SO SLEW_VIOL"); expect 125 -> ~5 (the 5
   non-ft relay nets); if ft hop violators remain -> report (then COORD decides on M4 guide floor).
b. t45 GRT: confirm "OT_FT_MAXWIRE: 0 ft hop nets" or count, usage table vs base.
c. Commit branch claude/ft-hop-m2-1112 (message file style, Co-Authored-By line), push hub, post READY with
   numbers (slew before/after, buffers added, M2-M5 usage base/fix, +5 point rule), tell HEAD-95 the ECO can drop.
## 7 Open READY/ASK
FT-HOP-M2 READY pending proof. Answered COORD (07:5x): CLAND dch = cland-slew-1112b (wshim_rx needs a fresh kit at a src with it); window-floor scan posted (S81 36 ports < 10 ps in 13 types + phy__t1 per_type 0; QC/KV 0).
## 8 Gotchas
- ot-run is ~/.local/bin/ot-run (not on PATH in ssh); --dir must exist on the target host.
- kit_resume manifest: copy the WHOLE kit except run/ (lec/, signoff/ too) or decide() says full rebuild.
- Never write into a resumed kit's hardlinked files; replace by rm+cp.
- ssh heredocs mangle quotes: scp python scripts; commit with git commit -F file.
- Never git in /home/ubuntu/OpenTallas on intel2/localhost. ~/coord only via coord-commit.sh.
- epyc8 load ~230: avoid for heavy runs; epyc2 lightest.
