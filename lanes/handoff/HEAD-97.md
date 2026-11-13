# HEAD-97 lane handoff (HEAD die owner, successor of HEAD-96)

Started 2026-11-13 05:38 PST. Coordinator: COORD. Freeze to 11-15 04:00 (no wave switch). Visual verdict gates sign-off.
Scope: (1) NEAR-MISS ECO on routed DB (hd_turn_a 89228387ea15; hd_turn_b 90983418bc07). (2) hd_tile DRT-0255 (a4b2265f9999).
(3) hold-class hd_mesh/hd_spn_end/hd_turn_b wait on R-CLOCK (HOLD-TAP-1). (4) post-freeze adoption list (rp19p wave switch 11-15 04:00).

## State
- 2026-11-13 05:38 STATE posted.

## Paths
- epyc7 worktree /srv/opentallas-scratch2/claude/wt/head-97 (full blob-less clone, branch claude/head-97-1113 @ main 4a5e3dcf7e; train 41 pinsites NOT on main yet: merge origin/claude/head-96-pinsites-1113@38f2fe1faf before any rp20 gen)
- epyc7 work dir /srv/opentallas-scratch2/claude/head-97 (so_main = git archive of main tools + physical/common_flow; turn_a/)
- HEAD-96 plan infra (read-only use): epyc4 /srv/opentallas-scratch2/claude/head-96 (pd/rp19d.json = rp19p, pd/sidecar.json, gates.sh, remap_start.py, head_reset_exports)
- ot-run: launch from intel2 (~/.local/bin/ot-run --hosts epyc7); epyc7's own ot-run does not know epyc7.

## Posted (all on origin)
- 05:38 STATE; ~06:00 RESULT DIEVIEW-F1 hold on hd_tile in kit_wave.json (backup autopilot/kit_wave.json.bak-head97-dieviewf1-*); 06:00 STATE took F1/F2; adoption list PLAN line.

## (1) hd_turn_a near miss 89228387ea15
- Autopilot ECO i1 (epyc8 .../hd_turn_a/attempt_3/gen/hd_turn_a/eco_20261113_122551_1562311/i1): TT +103.96, FF +6.26, DRC 0, 112 TT / 108 FF slew pins on 110 nets.
- Cause: BUFx16f "wire" buffers inserted by ECO repair_design on PLACEMENT RC drive single INVx1 ring dsel loads 175 um away, routed on M2/M3 only -> 450 ps slew.
- ECO2 running: epyc7 head-97/turn_a/eco2 (seed copy of i1 = turn_a/seed_i1), eco_loop main tools, OT_SLEW_MARGIN=50 OT_PRD_MAX_WIRE_LENGTH=120, --owner-override --lec. ot-run log intel2 /srv/opentallas-scratch2/claude/head-97/turn_a_eco2.otrun.log. Record turn_a/eco2/eco_loop.json.
- Note: rp19p changes hd_turn_a (write_chunk 16) -> an rp18 sign-off is superseded at the 11-15 switch; still worth it as a real view and ECO proof.
- hd_turn_b 90983418bc07 not local (R-CLOCK cross-tap class) -> no ECO.

## (2) hd_tile (DIEVIEW F1) - held, analysis so far (not built)
- DRT-0255 net u_core.u_xo/net34825: 2-pin BUFx16f hop from W of elemB to the 13.3-um band above elemB (elemB 216-501 x 734-1019.15; core top 1032.48). OBS M1-M5 on elemB.
- u_xo (the W->E i/o 565-bit pass, face windows y 708-1008 straight across elemB) = 2,751 cells: 334 repeaters in the N band, 218 in the 34.5-um A/B street, 815 W/E lobe buffers; 139 nets have guides over elemB. ft max wire 110 < elemB 285 um.
- Relay "column" x 338.9 = relay_sites of u_b.g_a[*].g_ais (2596 sites total, ~1220 A-input relays) sited AT elemA core pins facing the N-S street; moving them into the E-W street detaches them from their pins (pin_reg). Options: rotate/mirror A cores so the 245-pin faces point at the E-W street / outline (cores may move/rotate), or widen the street +17.28 (die event). Needs core pin face check (core_pins/elemA_pins.json).
- Taps clk_t10..t13 etc. are die islands (clock.die_islands_um, 44 ports, tap_max_sinks 1500; clk_t13 2077 over cap). Tap split = die clock island change -> needs the die clock run (DIEVIEW F3, unowned) for windows.
- Hold build added 21,273 hold cells (29%) on 117-ps windows.
## (3) hold types: wait R-CLOCK merge (HOLD-TAP-1 branch claude/hold-tap-1-1113).
## (4) adoption list posted (PLAN line). Plan diff rp18r2->rp19p: 6 types changed (turn_a, turn_b, st_n4, spn_wshim_rx, spn_end, spn_eshim_rx).

## NEXT (rp20 event on rp19p, one event, then private place/route hd_tile + hd_spn_end, READY)
- F1a tap_pair_affinity + split overloaded hd_tile islands (clk_t13/t16/t22) + windows from die clock run.
- F1b relay/landing out of the N-S street (see note above: core orientation or street width, decide on pin data).
- F1c reach_homes W/E lobes + reach_rules.py fix --rules 2; ALSO re-home the u_xo pass (station on the A-row E-W street or declared over-macro hop).
- F2 hd_spn_end one tap per station row (68 -> ~25-30), tap_pair_affinity hd_spn_end + hd_mesh; delete orphan taps hd_turn_b (clk 13 sinks @92,232; clk_t1 3 @92,17), hd_spn_eshim_rx (clk_t2 5, clk 19, clk_t1 15). Coordinate HOLD-TAP-1.

## F1b geometry facts (06:3x)
- elemA pins (core_pins/elemA_pins.json, R0): E 244, S 130, W 81, N 1, interior 10. Orients: eA0 MX, eA1 R180, eA2 R0, eA3 MY -> all four 244-pin E faces point into the N-S street (245 vs 245 per street_rule), 81-pin faces to the W/E outline.
- Horizontal budget per A row: 708.48 - 2 x 319.68 = 69.12 um (bottom row W 17.28 / street 25.92 / E 25.92; top row 17.28 / 34.56 / 17.28). street_rule rp19d hd_tile: N-S street 25.92 and 34.56 need 43.2; outline faces 17.28/25.92 with 81 pins need 43.2; elemB N outline_sliver 17.28.
- 90-degree rotation of the signed cores is not an option (layer directions); only R0/R180/MX/MY. So zero growth cannot meet street 43.2 + two outline streets (129.6 > 69.12). Choices: (i) street 43.2 + outlines 12.96/12.96 (81 pins each; seam partner gives the other half if outline streets are judged across the abutted seam, CHECK with RULES-STREET-1), (ii) +17.28 tile width (die event, pre-approved class), (iii) relays only out of the street (DIEVIEW zero-growth): but the street relays ARE pin relays of the 244-pin faces (u_b.g_a[*].g_ais relay_sites, ~1220), pin_reg would break.
- Tap/island edits (F1a split, F2 orphan/merge) are clock.die_islands_um entries = die clock contract: need the die clock tool run (DIEVIEW F3, unowned) to re-derive islands + windows consistently. Ask COORD to give F3 to HEAD-97 or a clock lane before rp20.

## 06:4x-07:xx
- hd_turn_a SIGNED OFF (ECO pass 2): LOCAL_PASS_NEEDS_PARENT TT +103.47 FF +6.26 DRV 0 DRC 0 LEC EQ; epyc7 head-97/turn_a/eco2/i1/signoff/signoff.json. RESULT+READY-COUNT posted (commit was slow on the hub lock; verify on origin).
- HEAD-CLKGATE-1 06:39: routed die clock gate on rp19p PASS; kitwin epyc4 /srv/opentallas-scratch3/claude/head-clkgate-1/routed/it4/routed/kitwin.json.
- rp20a = rp19p + hd_tile/hd_lep0N per_port windows = min(per_type, max(need+10,10)): epyc4 /srv/opentallas-scratch3/claude/head-97/pd/rp20a.json sha 10b23cca08b9 (winfix.py; side files symlinked from head-96/pd). Gates g_rp20a = rp19p, 0 NEW (gates.sh copy uses W=wt/head-96r3 read-only). hd_tile SDC windows -20..-26.
- NEXT: F2 (hd_spn_end clock.taps explicit list 68 -> 1 per station row; hd_turn_b / eshim_rx are tap_mode density from sink_bins -> orphan taps come from sink bins in the empty half: fix by sink bins / tap count), F1b (street: see geometry facts; RULES-STREET-1 ruling asked), F1c (reach_homes + reach_rules fix --rules 2; xo pass). After tap edits re-run HEAD-CLKGATE-1 recipe (its 06:39 RESULT line has the exact commands) and re-derive windows with winfix.py. Then private place/route hd_tile + hd_spn_end, package (head-96 package_r4.sh as template), branch off main in epyc7 wt/head-97 (merge origin/claude/head-96-pinsites-1113 first if train 41 still unmerged), READY.

## 2026-11-13 07:19 F2 review (Codex 06:59 candidate)
- Codex delta_f2.py (epyc4 scratch3 head-97) on rp20a: greedy tap removal under radius 200 / cap -> rp20_f2_raw (copied as pd/rp20f.json 39e7787c). hd_spn_end 68->30 taps, hd_turn_b 5->4 (removed clk_t3, NOT the DIEVIEW orphans clk/clk_t1), eshim_rx 0 removed; tap_pair_affinity added on hd_spn_end + hd_mesh; taps renamed contiguous.
- Gates rp20f: gen 0/26 (stale reset refs), 32 NEW clock_landings errors. After remap_start + head_reset_exports fix (rp20h): clock_landings errors gone, but gen still 0/26: hd_spn_end.x_i reader START raw rr_t63 has no wavefront driver (rr_t* reader-raw names not covered by remap_start; my rrfix.py could not map it). Also tap_sink_cap WARN on hd_spn_end clk_t13/15/16 = 1008-1161 > cap 1000 (the greedy cut used taps.sink_sites, G0 counts more sinks) and G0C clock_reach 301.7 on hd_spn_end; reset tree of hd_spn_end re-solved: 227 -> 167 relays, 312 refs moved up to 300 um.
- VERDICT: candidate NOT adoptable; keep rp20a as the event base. Better F2 form: cut only taps < ~100 sinks, check with the G0 tapcap inventory (cap 1000), and keep the reset relay solution fixed (find why tap edits re-solve the spn_end reset tree before cutting). turn_b/eshim_rx orphans: their sinks sit > 200 um from band taps, so the radius rule keeps them; moving those 3-19 relay sinks to the band (DIEVIEW) is the real fix.

## 2026-11-13 07:45 rp20a proof builds (COORD 07:4x)
- Kits: epyc4 /srv/opentallas-scratch3/claude/head-97/kits_rp20a/{hd_tile,hd_spn_end,hd_host_w,hd_host_e,hd_mesh,hd_spn}; gen log ../gen_kits_rp20a.log; gen args --slew-margin 50 --cap-margin 20 --max-wire-um 120, env OT_PLACE_MAX_FANOUT=32, tools wt/head-96r3.
- Launched from intel2 via /tmp/h97_launch.sh (ot-run --hosts epyc4, goal route = route+finish+signoff); logs intel2 ~/tmp/h97_rp20a_<type>.log; containers dpkit-<type>-*.
- Result per kit: <kit>/signoff/signoff.json, run_route.log. Post RESULT per type. ot-run "ROOT filesystem" warning is a false hit (scratch3 is md0 bind of /home/ubuntu/scratch-root).
- STATE posted (rp20 PROOF BUILDS RUNNING).

## 2026-11-13 08:48 rp20 proof builds, second launch (current)
- The first launch (kits_rp20a, plain gen on the raw plan) FAILED port_bind: missing rst_start_raw_* ports. A raw-plan gen does not add the private raw exports; you need the wave kit_rtl export.
- Prep: epyc4 /srv/opentallas-scratch3/claude/head-97/prep20a.sh -> prep20a/{prep,x}. Uses base/hp1, copied from epyc8 kw45/head_c90382b467/hp1. pd side files are added without overwriting. Prepared sha 0a679eb7bb58.
- Gen: gen20b.sh <types>, which sets item_env, --kit-rtl, --hold-ff-margin 0 and the R-FLOW args.
- Kits: copied to epyc7 /srv/opentallas-scratch2/claude/head-97/kits20b. Launched by intel2 /tmp/h97_launch2.sh (ot-run --hosts epyc7); logs intel2 ~/tmp/h97_k20b_<type>.log.
- All 6 port_bind PASS. Next: RESULT per type (<kit>/signoff/signoff.json); then F2 proper, F1b, F1c, die clock gate re-run, package + READY.

## 2026-11-13 09:05 F1b/F1c (COORD: build F1b+F1c, street-tool-2 correction)
- Tools tree: epyc7 /srv/opentallas-scratch2/claude/wt/head-97-rp20. Branch claude/head-97-rp20-1113 = origin/main 11e125f2c3 + local merge of origin/claude/rules-reach-1-1113 (NOT pushed). Sparse checkout widened to match head-96r3. Untracked links to head-97/pd side files. tools/die_plan/street_rule_st2.py = c2dac9c23d copy.
- epyc7 /srv/opentallas-scratch2/claude/head-97 holds: pd/ (rp20a + all side files, sidecar), base/hp1, f1b.py -> pd/rp20b.json (sha 7b677b4b8d48), g_b/ (street, st2, g0, rr), prep20b.sh.
- st2 verdict: all 4 A outline faces are non-sparse (81 pin relays per strip). G0 and gen error: corner sink (696.6, 16.2) has no tap within 200 um, because a 12.96 strip is under the 17.28 tap street.
- Posted ASK: (b') 17.28 / 43.2 / 17.28 (+8.64 per tile, die +190 um) + (c) pin-relay ruling, or (a) +60.48. F1c: rule 2 does not fire (no macro >= 405); ASK (i) RTL stage or (ii) u_xo W + bus:o internal_stations.
- Monitor on the kits20b builds: local script scratchpad/mon20b.sh (it emits KIT_END <type>). Post one RESULT per type.

## 2026-11-13 09:46 rp21 HEAD die event (COORD 11-13 rulings + REACH-TOOL-3)
- Tools tree epyc7 wt/head-97-rp20: branch reset (--keep) to origin/claude/reach-tool-3-1113 1a13fcec4a (street_rule.py with pin registers; reach_rules reach_pairs). Untracked links as before.
- Chain script: epyc7 head-97/build21.sh (WS=12.96 ES=21.6): ev21.py (tile 717.12, die +190.08, shore rows +95.04, edge channels) -> bins21.py (sink_bins hd_tile_rp21.json) -> pinreg.py (4x81 strip relays one per pin) -> reach_pairs x_xo + reach_rules fix --rules 2 (2 stations) -> street_rule legalize hd_host_e -> he_reblock.py -> rp21f; side21.py + street_rule sidecar -> pd/sidecar_rp21.json (tile collector_root_xy 717.12 patched by hand).
- rp21g = rp21f + hw_relayout.py (hd_host_w macros centred; GEOM-REVIEW note). Street check: 0 violations on tile / host_e / host_w; the sliver WARNs left are i,i+2 occlusion artifacts.
- 12.96 E face fails the density-tap rule (sink 698.76, 16.2), and 17.28 fails too. That is why E is 21.6. STATE posted.
- OPEN: reset re-solve. The die wavefront re-solves with the die stretch: tile depth 5 -> 4, and st_n3_transit u_rrl_44 moves. street_rule resetfix REVERTS hd_tile (u_rrl_78 / u_rrl_45: no same-role relay at depth 5). Do not use rp21h/rp21i (their hd_tile is reverted to the old form). Trying reach_fix fix --classes 5 --ref-plan rp20a (-> pd/rp21h5.json, log g_b/rf5.log).
- F1c RTL: a fork sub-agent is building XO_HOP=2 on branch claude/head-97-xohop-1113 (worktree wt/head-97-xohop). Delta script goes in head-97/xohop/.
- rp20 RESULTs posted: hd_host_e (GRT), hd_tile (DRT-0255 eA0 W strip). Monitor re-armed for the other 4.

## 2026-11-13 10:26 rp21 status
- Form is final: hd_tile W 8.64 / 43.2 / E 25.92. G0C needs the 8.64 lattice. Tile 717.12, die 17712 x 17556.48.
- SRAM blocks abut via track_offset +0.048 per macro. host_w head banks are MY at 449.28, sf at 544.32.
- Private tools tree epyc7 wt/head-97-rp20 @ fb5f5a8db8, local merges, NOT pushed: main + REACH-TOOL-3 1a13fcec4a + head-97-xohop 1bb0c4ec0f (fork; XO_HOP RTL, proofs in head-97/xohop/proof) + train 61 rules-flow-1 06a9b2cf28.
- Chain: head-97/build21.sh (full; it ends by running prep21.sh = KIT-OPS prep + kit_rtl + gen for 8 types -> kits21/). Plan out pd/rp21x.json, sidecar pd/sidecar_rp21.json.
- Reset: remap_start.py (local copy; ONLY/SKIP filter; rr_t raw copies follow their leaf). Pass 1: OLD=rp21e for hd_host_e. Pass 2: OLD=rp20a for the rest. Then head_reset_exports_rp21.py (offset fallback, 2 exports 1 cycle earlier: tile raw_0, eshim_tx raw_0).
- Last fail fixed: one hd_tile die_island collapsed to zero width under the endpoint map. Islands now move as a whole. Kits pending: launch with ot-run --hosts epyc7 like h97_launch2.sh, but on kits21.
- Posted: STATE, RESULT (plan gates rp21j), CORRECTION (DRT-0255 location uses 1000 DBU). ASKed COORD about the die clock gate re-run and hd_mesh / hd_ctl streets.
