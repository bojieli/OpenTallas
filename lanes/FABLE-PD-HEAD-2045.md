# FABLE-PD-HEAD-2045 -- HEAD stand-in closure review (2026-11-16 20:45 PST)
Scope: technical PD only, read only. Plan NF15c, 833 ps. Gates: DRC 0, routed TT >= -42, internal FF hold >= 0, bind + LATCHECK.
All numbers below were read from the kits at 20:35-20:50 PST unless marked (handoff) or (predicted).

## 1. State of the 7 stand-ins (20:50)
| stand-in | form | measured | closes as is? |
|---|---|---|---|
| hd_host_e | he12h_drc2 | SIGNED, DRC 0, TT -24.28, internal FF +0.69, archived both | DONE, replace now |
| hd_spn (ot_s81hd_spn_strip) | hd_spn__nf13a_a5eco1116 | SIGNED on NF13a, archived both (rtx-pro INDEX) | DONE if NF15c pins/outline of hd_spn equal NF13a (not checked by me) |
| hd_host_w | hw4e2 | DRT 0 violations, CLK_GEOM_DIFF PASS (0 of 4005 clock nets changed), 41 HB4 at 40 pins, session TT -31.32; at final count | likely YES (TT has ~10 ps to the gate) |
| hd_host_w | hw5 | GRT TT -0.92, FF +0.22, DRT iteration 2 (~3000 viol) | NO at first sign-off (predicted TT ~-18, internal FF ~-12 on ~30 ends); YES after one HEI pass |
| hd_serdes | sd9c | post-CTS TT -15.70 (placement RC; reset family gone: -204.38 -> -15.70, 87 cells), 12337 hold cells; GRT in congestion iterations | UNCERTAIN, setup risk (section 3) |
| hd_mesh | NF15c g_hd_mesh | post-CTS TT -5.80, taps 426..462, cross-tap hold 12346 ends ws -112 | YES with one HEI pass (predicted) |
| hd_ctl | NF15c g_hd_ctl | post-CTS TT +1.60 (-111.48 before, 16 cells), taps 420..461 | YES with one HEI pass (predicted) |
| hd_lep0N | NF15c g_hd_lep0N | in CTS, 310983 non-tap cells (77.7 % of cap) before hold cells | no timing number yet |
Not a stand-in but needed: hd_tile TP2 hold1 SIGNED 20:34 (TT +12.07, DRC 0, internal 0 negative, archived hd_tile__nf15c_tp2_hold1_1116). hd_spn_end SPEPRD3: ODB signed; V re-exported (alias check PASS), branch 9dd182a70bd GREEN.

## 2. Shared class (hd_host_w, hd_serdes, TP2): clock skew between and inside landed taps, paid for with hold cells
It is NOT skew at hard-macro boundaries, NOT reset relay placement (that was sd9A only), NOT pin access.
Evidence:
- TP2 worst internal hold -6.46: line[376] -> line[392], both on the SAME leaf buffer clkbuf_leaf_46_clk_t19. Launch CLK wire 0.72 ps, capture CLK wire 11.43 ps = 10.7 ps skew on one routed leaf net. Data path 44.3 ps (QN 38.0 + INVx1 6.3) against hold uncertainty 25 + library hold 15.1 = 40.1. Margin for skew is 4 ps. All 33 data endpoints are this g_line shift family.
- hw4: GRT TT -8.71 -> routed -25.5 (slip 16.8); GRT FF +0.47 -> routed internal -12.32 on 31 ends (slip 12.8). The t-pass ECO then moved TT to -44.24 and internal to -15.54/40. Hold repair ran with margin 0 at GRT RC.
- Same residue elsewhere: he12h -18.64 before ECO, spn_end -3.75/-6.9, HE-EPC south -3.27/17 (xpn_f shift pairs).
- Size of the debt: hw5 24119 HB4 of 159802 logic cells (15 %), 40 tap ports; sd9c 12337; hd_mesh 12346 cross-tap ends at -112; hd_ctl 5212 at -88. Tap means after balance: sd9c 396..460 (spread 65), hw5 clk_t6 mean 356 (346-472) against target 450.
- Setup side of the same class (sd9A, GRT RC): u_enc.rem_q[26] -> rem_q[111] = -40.0 with launch clock 474.0, capture 428.1 (skew -45.9) AND hold cell hold64642 (HB4, 57.2 ps) on the D pin of the setup-critical endpoint. Without those two the path has +63 ps. The hold fixer pads at the capture pin, so it taxes every path into that flop.
- hw4 setup -44.24 is a different cause: SRAM g_bank[4] rclk 447.2 -> rd_out (CK->Q 352.2) -> 3 gates -> two wire repeaters 163.6 + 86.6 ps (274 fF load) -> b_pay[260]; launch/capture skew only -5.7 ps. It is SRAM access + ~1 mm wire, not skew.
- Pin access: only one item to watch. sd9c GRT: 7 gcells, each one a tap port net (clk_t1/4/7/11/12/16/20) at y ~31 um with vertical capacity 0; GRT-0273 dropped the NDR on 8 tap nets; 1 gcell left (clk_t20 x 1998) at iteration 20. sd9A had none (pre-M8-grant). Matches the NF15c advisory "serdes grant ~0 tracks in tap rows".

## 3. Per stand-in: cause, ranked fix
### hd_host_w (HEAD-HW-ECO)
1. hw4e2: collect the sign-off now. If TT >= -42 and internal FF >= 0: export, replace the stand-in. This is the fastest view.
2. If hw4e2 TT lands below -42: run the TP2 HEI recipe (insert-only + route touched nets, no setup repair) on the ORIGINAL hw4 route (epyc10 fable-fix-head-types/hw4: TT -25.5, internal -12.32/31). It has 16.5 ps of TT headroom; the t-pass repair is what cost 19 ps.
3. hw5: keep running. Stage the HEI dump/plan scripts now so the pass starts when signoff_codex ends. hw5 is the better die view: hw4 has 460 output-port hold ends (coll_o0 -31.82 at the port) that the die seam will see; hw5 puts u_bout_coll_o0 on its own tap. Swap hw5 in when signed.
4. Only if hw5 routes below -42 on b_pay: register next to SRAM bank 4 output (placement bound of b_pay[*] to the bank), not a new tap.
Note: hw4e2 RCX read reports STA-1652 pins not found on cland_fwd_fclk_out_coll_o0 (forwarded clock out). Check that net is annotated before trusting the port numbers.

### hd_serdes (HEAD-SD9A)
Cause sd9A: 60 wrong relay sites (kit incoherence) -> fixed in sd9c, guard b56e08e96e1 GREEN. Remaining: rem_q skew + HB4 on endpoint (above); S_q[7] -> bm -15.7 (pma_rck) is inside the gate.
sd9c shows the identical -15.70 at post-CTS, so the PHY link placement is the sd9A one; expect rem_q ~-40 again at GRT RC, then ~-45..-55 routed = miss.
1. At sd9c GRT: read rem_q slack, launch/capture clock arrival, and whether an HB4 sits on the D pin. If rem_q <= -25, do not spend the DRT; go to 2.
2. Successor sd9d = sd9c + all u_enc.rem_q flops on one tap (tap_chain_affinity.tcl exists in the kit) + no capture-pin hold cell where endpoint setup slack < 60 ps (pad the short branch instead). 0 cycles, no RTL change. Form C (retime, +1 cycle) is not needed first.
3. Let the 1 capacity-0 tap gcell go to DRT (do not restart GRT for it). If DRT fails there, the fix is a plan item: tap landing sites for hd_serdes outside die M8 runs (HEAD-DIE-R).
4. Plan: sd9c needs u_chn at 1548.0,109.44; canonical is 1900.8,250.56. HEAD-DIE-R should build that one-block event now (bind + LATCHECK), not after sign-off. It is the longest pole of the 7.

### hd_mesh, hd_ctl, hd_lep0N (HEAD-TYPES-R2)
No structural finding. Setup is healthy after CTS. Expect the class residue (tens of internal hold ends at -5..-15) at first sign-off: stage HEI for each now. lep0N: watch cell count after hold cells (310983 + est. 15-25k).

### Class fixes (ranked)
1. Make HEI a standing stage: any routed sign-off that fails only internal FF with TT headroom runs dump -> plan -> insert-only -> route touched nets -> sign-off automatically. Measured cost on TP2: 34 HB4, 68 nets, DRT 28 min, DRC 0, TT unchanged (+12.06 -> +12.07).
2. New launches only: GRT internal reg-to-reg hold repair target +15 ps instead of 0 (covers the measured 6-13 ps GRT-to-route slip). Not a gate. Do not patch running kits.
3. pregrt_ff_hold / HEI: never place the hold cell on a capture pin whose setup slack is below the cell delay; pad the short branch.
4. Tap balance: clk_t6 356 vs 450 and spread 65 are the source of the 12-24k hold cells; tightening to <= 20 ps would cut them. Next plan event, not now.

## 4. Fastest path to 7 real views in die STA
- Run the NF15c real-view die STA NOW (HEAD-SPE-EXPORT run, E2 head-spe-export/nf15c_real) with hd_host_e (he12h_drc2), hd_tile TP2 hold1, hd_spn_end fix, and hd_spn a5eco if its NF15c pin/outline check passes. Remaining types explicit stand-ins. Do not wait for all 7; rerun per view (ILM).
- +~0.5 h: hd_host_w (hw4e2). +3-6 h: hd_ctl, hd_mesh, then hd_lep0N, each route + one HEI pass.
- Last: hd_serdes. Needs sd9c/sd9d sign-off AND the u_chn plan event. Start the plan event in parallel today.
- First real seam risk to read in that run: hd_host_w coll_o0 port hold (-31.82 in hw4).

## 5. STOP list
- hw4e1 and any further t-pass setup repair on hw4 (it cost 19 ps of TT).
- eco_ab206 rip4 / four-net rip reruns (DRT-0255, no evidence).
- sd9A relaunch, sd9B (+3 RX), Form C retime before sd9d is tried.
- Restarting sd9c GRT for the 1-gcell tap congestion; in-place edits of running kits.
- NF13a wave hd_spn_end attempt_4 retries (20:06 late-ECO FAIL, drc 3): superseded by SPEPRD3.
- Any claim from old real_sta/speprd3_die or run_speprd3 (null seam coverage, alias cycles).
- A second full hd_host_w rebuild while hw4e2 and hw5 are both alive.
- Waiting for all 7 before the first NF15c real-view die STA.

## Not verified
hw4e2 final TT/FF (count was running); hd_spn NF13a view validity on NF15c; sd9c rem_q at GRT (prediction from sd9A); hw5/mesh/ctl routed numbers (predicted from hw4 slip); renders were not opened by me (Codex/lanes LOOKED records exist for hw5, sd9c place, TP2, he12h).
