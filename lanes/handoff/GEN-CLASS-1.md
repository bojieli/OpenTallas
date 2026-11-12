# GEN-CLASS-1 lane handoff (refreshed 2026-11-12 ~13:1x PST)

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
- CLAND-RING-LOCALITY proof 1 (HEAD wshim_rx, GRT->route->signoff): ot-run client intel2 pid 3314400, host epyc9, kit
  epyc9:/srv/opentallas-scratch2/claude/gen-class-1/proof/wrx/hd_spn_wshim_rx (copy of HEAD-95 wshim_rx_main + new
  ft_hop_maxwire.tcl), log intel2 ~/gc1log/wrx_cland.log. Gate: SO SLEW_VIOL 0 TT/FF (base 154/134).
- proof 2 (S81 t45 fresh kit): kit_wave run-item, intel2 pid 3508038, spec+log intel2
  /srv/opentallas-scratch2/claude/gen-class-1/kw_t45/{spec.json,unit.log} (AP_DIR=kw_t45/ap, NOT wave state); work epyc9
  /srv/opentallas-scratch2/claude/gen-class-1/kw_t45_root/items/slice_station__t45/attempt_1; src tree epyc9
  /srv/opentallas-scratch2/claude/gen-class-1/src_s81_cland_c4f3e873a1 (symlinks to bsrc4_r12ng + tools/rtl copies).
  After place: run W/gen/run_kit.sh K grt; compare GRT slew/fanout vs base t45 (1158 TT pins).
- probe data: epyc9 /srv/opentallas-scratch2/claude/gen-class-1/loc/wrx (cland_nets.tsv, cland_insts.tsv).
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
- Branch claude/cland-hop-maxwire-1112@c4f3e873a1 (CLAND-RING-LOCALITY A): READY after proofs. (B) plan option: band next to capture (HEAD-95 band rects).
a. When wshim_tx signoff done: count TT/FF slew pins (signoff/tt/sta.log "SO SLEW_VIOL"); expect 125 -> ~5 (the 5
   non-ft relay nets); if ft hop violators remain -> report (then COORD decides on M4 guide floor).
b. t45 GRT: confirm "OT_FT_MAXWIRE: 0 ft hop nets" or count, usage table vs base.
c. Commit branch claude/ft-hop-m2-1112 (message file style, Co-Authored-By line), push hub, post READY with
   numbers (slew before/after, buffers added, M2-M5 usage base/fix, +5 point rule), tell HEAD-95 the ECO can drop.
## 7 Open READY/ASK
- READY ft-hop-m2-1112@689f54a2fb (posted ~10:0x); READY tcl-puts-quote-1112@475f0c5d0e (08:14). Offered: grt_maxwire GRT183 bypass fix, S81 cland fanout class.
FT-HOP-M2 READY pending proof. Answered COORD (07:5x): CLAND dch = cland-slew-1112b (wshim_rx needs a fresh kit at a src with it); window-floor scan posted (S81 36 ports < 10 ps in 13 types + phy__t1 per_type 0; QC/KV 0).
## 8 Gotchas
- ot-run is ~/.local/bin/ot-run (not on PATH in ssh); --dir must exist on the target host.
- kit_resume manifest: copy the WHOLE kit except run/ (lec/, signoff/ too) or decide() says full rebuild.
- Never write into a resumed kit's hardlinked files; replace by rm+cp.
- ssh heredocs mangle quotes: scp python scripts; commit with git commit -F file.
- Never git in /home/ubuntu/OpenTallas on intel2/localhost. ~/coord only via coord-commit.sh.
- epyc8 load ~230: avoid for heavy runs; epyc2 lightest.

## 2026-11-12 14:04 PST update (CLAND-RING-LOCALITY)
- Branch claude/cland-hop-maxwire-1112@aee2a3f4707 (worktree intel2 /srv/opentallas-scratch2/claude/wt/gen-class-1). Not READY: no routed proof of LOCAL yet.
- wshim_rx proof with the hop pass only: 152/131 slew, NOT SIGNED (epyc9 gen-class-1/proof/wrx). Root cause is the write-side tc decode (OR3x4 fo35 -> fo67 slot enables). The fix is LOCAL=1 on plain rings >64b (equiv 80/80 PROVED: epyc9 gen-class-1/eq_local/out).
- S81 t45 proof is blocked. (a) The overlay src with a symlinked physical/ fails the dead-input repo-relative check. Use a cp -al copy of s87bind/bsrc4_r12ng with real tools/ and rtl/ instead. Never edit hard-linked files in place; replace them by rm plus copy. (b) The r12ng sidecar is stale: s_5N_L1 was retyped t44__clf6cf8492 -> t52 after compose, so the x2 bus is not in t52 local_sources. Asked DIE-S81-88 which stage did it.
- Stopped my t45 place (my units and container only). The s81bind attempt at epyc9 gen-class-1/s81bind failed at the bind step (ELAB ok).
- Next: resolve the sidecar, rebind r12ng with aee2a3f4707, t45 kit -> GRT. Get the HEAD bind recipe from HEAD-95 for a LOCAL wshim_rx proof. Then READY.

## 2026-11-12 update: HEAD wshim_rx proof (WREG)
- The wshim_rx link_i ring is cas (count-aligned), so LOCAL does not apply. The proof uses the plan field landing_ring_wreg {buses [link_i], dsrep 8, write_chunk 16}.
- Tree: epyc4 /srv/opentallas-scratch2/claude/gen-class-1/tree (own blob:none sparse clone @aee2a3f4707, plus 7 head-93 prep links). Plan: gen-class-1/pd/rp16_wreg.json (pd/ siblings symlink head-95/pd).
- Build: intel2 pid 732695, log ~/gc1log/wrx_wreg_route.log, kit epyc4 gen-class-1/proof/wrx_wreg/hd_spn_wshim_rx. Gate: SO SLEW_VIOL 0 TT/FF except the u_srl_17/u_rrl_17 hop (HEAD rp17).

## later 11-12: read-side START class + t45 bind
- eshim_rx rp17 (wreg on) is still 124/134. The violators are the u_sel copy INPUTS fed by cland_start broadcast (BUFx10 fo 94). The copies themselves are local (loc/esh/sel.out, trace3.out on epyc9). Proposed: a reader-START stage + RSTREP per-chunk rule. Awaiting COORD.
- WREG reach default (ring_wreg_reach) is in the intel2 worktree, uncommitted, with tests. K-change lists: gen-class-1/wreg_list_{head,kv,qc}.txt (HEAD 54 buses / 20 types, KV 127 / 13, QC 0 on the sidecar pair, unverified).
- t45: tree epyc8 gen-class-1/bsrc_t45 (cp -al plus a patched real copy), out_t45 BIND rc 0, ring has DSREP 8 LOCAL 1. Verify is re-running (verify_t45.sh, bind.f repointed). Next: kit-rtl/gen/place/GRT.
- Running: wrx_wreg route (intel2 pid 732695), full suite log ~/gc1log/suite_wreg.log, verify intel2 pid 1403168.
