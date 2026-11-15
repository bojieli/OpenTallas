# FABLE-SERDES-STRUCT: serdes hold/clock class, HEAD hd_serdes and S81 serdes__t* (2026-11-14 20:4x PST)

Scope: diagnosis only. No build was launched, nothing was killed. All numbers are read from kit reports on disk.
My own read-only STA class split (ot-run, epyc9/epyc7) was never admitted (fleet memory full); I cancelled my own
waiters. So the per-endpoint class split of the hold counts is NOT measured; where I rely on the worst paths only, I say so.

## 0. Final fixes, reconciled 20:5x PST with FABLE-TYPES-HEAD section 1 and FABLE-TYPES-S81-MISC section 1
These two paragraphs REPLACE the "ONE FIX" paragraphs in sections 2 and 3 below where they differ. The diagnosis
sections stand. The three reviews now ask for one event per die, not three.

**HEAD, FIX-HEAD-SERDES-BAND (one hd_serdes plan event, HEAD-99; TYPE-HDSERDES builds).**
Same event as FABLE-TYPES-HEAD section 1, with one change: its step 3 is required, not conditional.
1. Receiver in data order over the pma_rx pins (x 1400-2600): kp4_dchn to the east end, mirrored; SRAMs west of it; no
   logic west of the macros (FABLE-TYPES-HEAD steps 1). I WITHDRAW my island position "around the port at x 1106":
   the pins are at x 1603-2412, so the island belongs there.
2. pma_rck / pma_tck / pma_lock entry moved to the sink centre, x about 2090 (their step 2).
3. Raise the phy_supply_region floor from y 150 to y 400 over x 1400-2600 (kit keepout_phys.tcl / pdn.tcl rectangle), or
   grow the outline 250 um. Reason (MEASURED rate, INFERENCE on the result): one level is 60-65 ps per about 45 um; a
   1200 x 146 band still gives about 600 um of one-sided reach = 13 levels = about 800 ps and row-to-row leaf seams;
   a 700 x 350 island gives about 10 levels.
- No RTL change and no new clk taps: pd3 already balances 22 taps to 53 ps.
- One-build proof (place + CTS, then on to sign-off): no u_syn cell at x < 1400; pma_rck insertion < 600 ps;
  |u_chn/clk - register latency| <= 100 (now 432); pma_rck period_min < 1000 (now 3358); hold gate FF >= -150.

**S81, FIX-S81-SERDES-CLKPART (one serdes event, DIE-S81-92; SERDES-TXPIPE supplies RTL and defines).**
Same event as FABLE-TYPES-S81-MISC section 1 fix 1-4, plus two items from this review (5, 6):
1. Recovered-clock island under the PMA W end with the rck root at the island (kitH / kitH2 geometry).
2. u_chn on its own early tap from that root: clk at the macro pin >= 175 ps before register arrival, no delaybuf
   chain. I WITHDRAW "macros as sinks of the nearest leaf" for u_chn (its view needs 174.59 ps of hold).
3. clk taps assigned by pipeline group: all u_enc stages, and p_d + u_txl row 0, on one tap; delete OT_TAP_MAX_SINKS.
   I WITHDRAW "cap 1000": the cap split is what made the t12 -157 pair.
4. Bind defines: proven cone set + TXPIPE / RXPIPE.
5. NEW: OT_TAP_BALANCE target for serdes types 250 -> 450 ps (contract + vclk latency follow). At 250 the balancer
   cannot reach its target (trees are 500-790 ps): spread 302-331 on kitH / kitC2, 24 of 35 taps over. Pipeline
   grouping fixes u_enc; the balance fixes the remaining cross-tap pairs (rs_t -> u_rm, u_rrl, -58..-288).
6. NEW: RX row 0 (u_lrxi r[0] / u_rxf) captures on the falling rck edge. The PMA launch pin and the first row can
   never share a leaf (macro vs register tree); mismatch measured +344 (kitH, island at the entry) to +737. Falling
   edge opens the window to about -180..+530 (INFERENCE from clk-to-q 130 ps, half period 416). Cost <= +1 rck cycle.
- One-build proof: t12 to CTS (as in S81-MISC; t14 if the TXPIPE kit is ready first; same reads): u_chn/clk >= 175 ps
  before u_lpl_2_r; no u_enc pair across taps; OT_TAP_BALANCE spread <= 60; row 0 - u_prx/pma_rck inside -150..+400;
  hold gate FF >= -150 with under 1000 endpoints (now -246 / 5024 kitH; 2,014 on t12).
- TYPE-SERDES-T4: t4B3 finishes its route; no further density / repair-time forms for the family.

## 1. Root cause (both dies, MEASURED)
The hold class is insertion-delay mismatch between clock subtrees that are built separately, hit by zero-logic
register pairs (PMA face, lane rows, encoder pipeline rows). It is not hold padding debt and not distance.
Three subtree seams produce it:

| seam | S81 serdes__t2 (4_cts_final.rpt, TT) | HEAD hd_serdes |
|---|---|---|
| PMA launch vs first capture row (rck) | u_prx/pma_rck vs u_lrxi r[0]: kitC2 1501 vs 2238 = +737 -> hold -606; kitF 1459 vs 2112 = +653 -> -524; kitH 1533 vs 1877 = +344 -> -210. Hold = -(mismatch) + about 130 ps of PMA clk-to-q. t14 wave: -209, same pair | PMA is outside the block: pma_rx[0] -> u_prx.l[0][0] -1356 in pd3 (port latency 0, input min -265, capture flop at 1071 ps) |
| macro tree vs register tree (rck) | io_pma_rck port at (258, 1091) is next to u_prx, yet the PMA pin gets 1.46-1.53 ns: TritonCTS puts the 5 macro clock pins on one net (kitC2: avg sink wire 2672 um, depth 21) and the 28.6k registers on another (26-33 levels, avg 1246-1339 um) | rp18: u_chn/clk 1208 vs registers 2047. pd3: 1417 vs 1849 |
| tap vs tap (clk) | OT_TAP_BALANCE misses its target: target 250, result 240..542 (spread 302-331), 24 of 35 taps over 270; the tool itself asks for tap pitch <= 199 um. Pairs: u_enc d2 -> d3 258 vs 578 = -288 (kitH); p_d -> u_txl r[0] 330 vs 567 = -135 (kitC2); t14 d4 -> d5 229 vs 478 = -200 | rp18 (3 taps): trees 14/18/27 levels, 545..1563 ps, clk skew 1017, u_ptx.l[2] -> q -716, start_i -1203 against the 450 ps contract. pd3 (22 taps, cap 1000): OT_TAP_BALANCE 409..462, spread 53 |

Per-level cost is about 60-65 ps (rp18 rck: 34 levels = 2047 ps for 1523 um average sink wire; about 45 um per buffer).
So every 100 um of extra reach inside one clock subtree adds about 130 ps of insertion that its neighbour subtree
does not have.

What it is NOT:
- Tap count alone. HEAD pd3 already has 22 taps and balances them to 53 ps; S81 has 35 taps and still spreads 302,
  because the taps sit on the die grid, not over the logic island (taps with 3000 sinks reach 873-899 um).
- Landing-ring pairs. fclk_in_coll_i0 skew is 13-23 ps on both dies; ring paths are met or within -67.
- Hold padding. kitC2 stops at the structural hold gate (-574 FF, 3349 endpoints); buffers cannot pay 600 ps x 544 bits.

## 2. HEAD hd_serdes
State of the evidence:
- The "-580 to -602 over 14 launches" and the "3 taps" both belong to plans up to rp18 (epyc9 head_rp18_1112: hold gate
  FF -1106 on 4782 endpoints). They are STALE for the current form.
- Current form = private pd3 (epyc7 /srv/opentallas-scratch2/claude/head-97/kitsserdespd3/g_hd_serdes/hd_serdes; same
  22 taps and secondary clock as wave attempt_4). Hold gate after tap balance: FF -166.7 on 5234 endpoints, INFO (goes
  to repair). The clk seam is closed by structure already.
- What is left is the rck domain. 13.5k rck sinks span 1808 x 103 um (CTS-0024/25, rp18). The secondary clock makes
  87 leaves, but the trunk to them is 33 levels, 1786 um average. Leaf arrivals 1071 (u_prx.l[0]) to 1900; leaf-to-leaf
  188 ps on the zero-logic row pair u_prx.l[1] -> l[2] (-132); macro 1417 vs registers 1849. OT_LEAF_AFF leaves 5815 of
  7781 zero-logic pairs across leaves (skip_far 2356, radius 30 um).
- Same cause gives the setup failure: pma_rck -2525 (u_syn.ldr -> u_bm.dz, 3.3 ns of data path).
- The band is a plan rectangle, not a PMA macro: keepout_phys.tcl / pdn.tcl block y 150..1226.88 over the full 2885.76
  width ("phy_supply_region"). Logic has 146 um of height.

ONE FIX, HEAD (FIX-HEAD-SERDES-BAND): region/outline change. Move the phy_supply_region floor from y 150 to y 400
over x 600..2000 (or, if the PMA supply needs the area, grow the slot 250 um on the logic side; outline growth is
pre-approved). Put the whole pma_rck domain (KP4 decoder, u_chn, both SRAMs) in one fenced island of about
700 x 350 um around the pma_rck port (1106, 148). Keep the lane rows on the pin face. No RTL change, no new taps.
- INFERENCE: island 700 um wide -> trunk about 10-12 levels, rck insertion about 700 ps, leaf spread under 100 ps
  (scaled from 60-65 ps per level; not simulated). INFERENCE: the PMA supply region is oversized; on S81 the PMA
  macros are 130 um tall each. I did not check the HEAD PMA power plan.
- One-build proof: hd_serdes kit with the new rectangle, to sign-off. Read at CTS: pma_rck_regs sink region <= 750 um
  wide; trunk depth <= 12; |macro - register latency| <= 100; hold gate FF >= -150; pma_rck setup at CTS > -300 (now -2525).
- Owner: HEAD-99 (plan event: rectangle + region), TYPE-HDSERDES builds. Do not INFRA-retry attempt_4 unchanged: pd3
  already measured that form (R-CLOCK-4). Keep its 3_place.odb as the "before" picture.
- Open at die level (not a kit gate): pma_rx -> u_prx.l[0] reads -1356 with same-edge hold. With a 1071 ps capture
  clock the flop samples one beat later, 218 ps into the declared eye (166.6..568). INFERENCE: this is a constraint
  contract question (Codex flagged the PMA RX eye as unqualified), not a layout failure. HEAD-99 to state the capture
  edge in the die contract.

## 3. S81 serdes lane-row form
HARD-S81-SERDES-1 did not close because the lane rows fixed distance (setup) and left all three clock seams open.
kitH (island at the W end, where io_pma_rck enters) is the only geometry worth keeping: PMA mismatch 344 instead of
653-737, macro tree depth 8 instead of 21.

ONE FIX, S81 (FIX-S81-SERDES-CLKPART): lane-row clock partition, as one plan + flow form on the kitH geometry:
1. clk: taps over the serdes island at pitch <= 200 um, cap 1000 sinks, balance target raised 250 -> 450 ps (the HEAD
   pd3 setting, which measured spread 53). The serdes type insertion contract and vclk latency follow (die clock
   budget row, DIE-S81-92).
2. rck: adopt the secondary clock on io_pma_rck (HEAD tool; the S81 model with 114 groups exists, never applied) with
   two rules it does not have today: (a) u_prx/pma_rck, u_chn/clk and the SRAM rck pins are sinks of their nearest
   leaf, not a separate TritonCTS macro net; (b) leaves are cut by lane (x slice), so a bit's face flop and all its
   lane rows share one leaf. This closes the PMA seam and the row-to-row seam by CPPR, not by balance.
3. RX row 0 (u_lrxi r[0], or SERDES-TXPIPE's u_rxf) captures on the falling rck edge (lockup row). Window for
   L(row 0) - L(PMA pin) becomes about -180..+530 ps instead of under +115. INFERENCE from clk-to-q 130 and half
   period 416; cost at most +1 rck cycle on RX, pre-approved; LATCHECK row needed.
- One-build proof: serdes__t14 fresh kit that SERDES-TXPIPE is about to route (it already measured both seams: -200
  and -209), built once more with items 1-3, to sign-off. Read at CTS: OT_TAP_BALANCE spread <= 60 (now 302);
  L(row 0) - L(u_prx/pma_rck) inside -150..+400 (now +344..+737); hold gate FF >= -150 and under 1000 endpoints
  (now -246/5024 kitH, -574/3349 kitC2).
- Owners: DIE-S81-92 (tap sites, insertion contract, latency row; one serdes event with the TXPIPE defines).
  SERDES-TXPIPE (RTL edge of row 0, the proof build). TYPE-SERDES-T4: let t4 B3 finish its route; it does not have
  this form, so a pass is a pass and a hold fail is this class, no further forms.
- serdes__t1 (371k cells): no KP4 split is needed for the hold class. The split is a capacity question
  (TL-SERDEST1 / OVERSIZE-1); the clock partition above applies unchanged.
- t14 TX distance (-455..-576 on u_ptx/d): correct as owned (TXPIPE distance stages). Not this class.

## Not checked
- Per-endpoint class split of the hold counts (STA never admitted). Counts above are gate totals; pairs are worst paths.
- HEAD pd3 post-balance pair list (cts_final.rpt is written before OT_TAP_BALANCE; only the gate total is post-balance).
- HEAD PMA supply plan above y 150; S81 secondary-clock model contents; t4 B3 reports (route still running).
- Insertion estimates for the two fixes are scaled, not built.

## Sources
- epyc9 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp18_1112/items/hd_serdes/gen/hd_serdes (4_1_cts.log, 4_cts_final.rpt, hold_gate.log)
- epyc7 /srv/opentallas-scratch2/claude/head-97/kitsserdespd3/g_hd_serdes/hd_serdes (same files, keepout_phys.tcl, io.tcl)
- intel1 .../head_rp21z4_1113/items/hd_serdes/attempt_4/gen/hd_serdes (io.tcl taps, secondary_clock.json; 3_place.odb kept)
- epyc9 /srv/opentallas-scratch2/claude/hard-s81-serdes-1/{kitC2,kitH,kitF}/gen/serdes__t2 (4_1_cts.log, 4_cts_final.rpt, hold_gate.log, io.tcl, macro_place.tcl)
- hub lanes/handoff: TYPE-HDSERDES, HARD-S81-SERDES-1, TYPE-SERDES-T4, SERDES-TXPIPE, TL-SERDEST1, TL-SERDEST14; lanes/DIEVIEW-HEAD-1113.md F6
