# FIX-QC-STA-BTW handoff (Opus 5.5, started 2026-11-23 03:3x PST by FIX-LEDGER acd269758d3b62a53)
Item: rc96 QC st_a b_tw: u_bin_b_tw_data_i/q -> u_u_r3 cfg_* setup (-22.5 CTS post-hook / -27.1 GRT pre-repair on cled3c1d7b).
Report to FIX-LEDGER (acd269758d3b62a53) at ROOT-CAUSE, ROW-DRAFT, GATED/REASONED. Compose via OPUS-FIX-QC-V4-R2 (a0667f53915fbc5a6), c4 08:00, GATED by 13:00. Choice of form due to FABLE-RC-QC + FIX-LEDGER by 05:00. Row must pass PRE+G0 by ~07:00.
## Inputs
- Kit: epyc2 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V2/items/sle_st_a_v1__cl989804f6__cled3c1d7b/gen/sle_st_a_v1__cl989804f6__cled3c1d7b (4_cts_post_hook.rpt, 5_1_grt.odb, tt_setup_repair_grt.log)
- SLWSLE handover msg 03:3x: net map (one 1080b bank ot_dp_st, cfg [27:0]/[28:0], tw_addr [52:29], tw_data [1076:53]...), STA-1 fast probe 840 um.
- FABLE-UNC-QC row STA-BTW-0 (0 cycles, relay_sites: bank bits q[0..28] FIRM at (412.5,666.8)), hub lanes/handoff/FABLE-UNC-QC-STA-BTW-0.c2b.json sha256 7d6aa569146e, base c2b 4ee5a470fef2. STA-BTW-1 (+cycles) WITHDRAWN (cfg shift must be equal over u_r0..u_r7 of a slice).
## Findings (03:5x)
- CTS post-hook b_tw class (path = 8 stages: DFF + INVx4 + 6-7 BUFx12f, ~75 ps each, 0 stations; launch tap 252-267, region ck pin -9..-25 with internal latency in the macro arc):
  cled3c1d7b -22.52 (r3 view qfd_dv_s8_station_tail1_h17_n7_s8, cfg arc credit 82-92 ps, arr 921-932)
  cl67389ecd +19.24 (r3 view ..._h17_n9_s10, cfg arc credit 125-128 ps, arr 922) -> same wire, +40 ps from the macro view
  clf4365a62 +34.41 (n7_s8 view credit 80-91, arr 854 = ~70 ps shorter wire)
- Kit GRT basis (tt_setup_repair_grt.log, setRC_rcx + OT_RC_SIGNAL x1.25): worst endpoint after repair u_u_r3/cfg_nwords_p[5] -216.8 (repair stall), wns -218.27. Own STA on final 5_1_grt.odb: running (epyc2 meas/cled_grt).
## 04:0x ROOT-CAUSE (hub post c7b845c)
- Own STA on final 5_1_grt.odb (epyc2 FIX-QC-STA-BTW/meas/cled_grt, btw_meas.sh/tcl): b_tw q[22] -> u_u_r3/cfg_nwords_p[5] -218.27 (= type WNS); r3 arc 1073 um Manhattan, 17 stages, 0 stations; r2 724 um -18.9; r0/r1 +236/+274. Region cfg pins r0 (430,163) r1 (404,490) r2 (395,831) r3 (395,1172); bank output buffers (430-505,293).
- Form ruled: adopt FABLE-UNC-QC STA-BTW-0 (0 cycles; q[0..28] FIRM (412.5,666.8)). Reasons: one cfg shift per slice preserved; +1 station form withdrawn (needs st_b RTL).
- Gate: epyc8 /srv/opentallas-scratch2/claude/FIX-QC-STA-BTW/gate_btw0.sh btw0g (apply on c2b -> reprice 0 lanes -> TAPNAME 0/0 -> latency -> pgp check -> G0). Local log scratchpad gate_btw0.out.
- Asked HCST-R3 (ad1cb539e214811d9) for the STA-1b/btab_s4r btab origins, to clear the (412,667) site.
- NEXT: when PRE+G0 pass -> ROW-DRAFT to FIX-LEDGER + V4-R2 (a0667f53915fbc5a6) for c4 08:00; probe = sealed st_a kit on c4 bound (or a private bind of btw0g) for setup >= -42 on the b_tw class + census incl q[29..1079] -> btab.
## 04:2x
- Estimate posted (hub 01fb016): 0.645 ps/um buffered at the GRT basis, overhead 196, required 916.45 -> bank->r3 at 529 um slack = 365 - T_bank (+67 at 298, +15 at 350); landing->bank about +400. FABLE-RC-QC agreed, no per-hop station (892ab26d); acceptance = probe >= -42 on the 3 types from the final GRT, report the bank tap, re-read if SEAT-1c lands.
- What-if on the DB (epyc2 FIX-QC-STA-BTW/whatif/cled_w*) INVALID: remove_buffers ignored the list and removed all 116k buffers, and the clock was not re-tapped (launch 567). Not used. Placement-basis base reads -88 vs -218 at GRT.
- Row sent to V4-R2 for c4 as a key-merge applied LAST (btw0_rows.py --apply). No private bind: c2b-size fork needs 107 GB on epyc8 (c2b bind was refused for disk).
- pgp check + G0 running (epyc8 btw0g, started 11:47 UTC).
