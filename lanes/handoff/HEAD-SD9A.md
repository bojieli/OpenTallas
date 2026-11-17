# HEAD-SD9A -> handoff to FABLE-FIX-HEAD-SERDES (hd_serdes). Lane HEAD-SD9A STOPS here (COORD FABLE-PD-HEAD-2045 s3).

## sd9c run: ENDED, FLOW ERROR AT GRT (not a design verdict). No 5_1_grt.odb, so there is no rem_q read
- Kit: /srv/opentallas-scratch2/claude/head-sd9a/gen/hd_serdes (replicas at the same path on epyc7/8/9/10; reset_tree.tcl sha 5be86bfb2b5a).
  epyc8 unit oth-ubuntu-4115587-1794884149 RAN, exit 2 (~04:5x UTC). intel2 client log ~/head-sd9a-logs/sd9c_route.log; kit log run_route.log.
- Before the error: synth/place/CTS done; CTS TT repair wns -204.38 -> -15.70 (tns -12276.6 -> -114.3, 87 cells, KEEP), 4_cts.odb
  written 04:14; GRT routed (extra iterations to 24+/30). Place render flags only fanout_spread=541.9 (sd9a: 1131.1).
- ERROR global_route.tcl:195 "OT_VCLK_MEASURED_HOLD: pin-register mean unavailable (samples 1669 missing 0 clocks 2)".
  Cause: NF15c gen sets config.mk OT_GRT_MEASURED_HOLD = 1, which the sd9a kit did not have. vclk_measured_hold.tcl ot_vmh_pinreg_mean
  excludes only the OT_FWD_RING_INPUTS families. The native pad input pma_rx[*] (constraint.sdc "# OT_NATIVE_PAD_INPUT pma_rck pma_rx[*]",
  input delay on pma_rck) puts pma_rck boundary registers into the census, so there are 2 clocks and it fails closed. Any kit with a native PHY pad clock is exposed.
- FIX (source): in tools/die_plan/vclk_measured_hold.tcl, exclude the OT_NATIVE_PAD_INPUT ports (and their clock) from din, as is done
  for OT_FWD_RING_INPUTS. Then resume from the kept CTS (4_cts.odb is TT-repaired): do-5_1_grt onward, by do-* targets or a resume.json
  (the kit has no resume.json; a plain re-run of run_kit.sh route would rebuild from synth). Opt-out alternative (not structural):
  OT_GRT_MEASURED_HOLD=0, which is what sd9a ran with. NOT relaunched (COORD: hand off and stop).
- Read at GRT (in the GRT RC frame of tt_setup_repair.tcl): use my measure script on epyc7
  .../head-types-r/sd9a_grt1/hd_serdes/sd9a_meas/{tail.tcl,meas.sh} (head -80 tt_setup_repair.tcl + violator dump) with K repointed.

## Form sd9c = sd9A on NF15c with a coherent reset tree
- Plan copy epyc8 /srv/opentallas-scratch2/claude/head-sd9a/planA15b/prep = NF15c prep + ONE edit: u_phy.u_link.u_dec.u_chn origin
  1900.8,250.56 -> 1548.0,109.44 (sd9A form A). M8 grant 9469b3cd4954b3ea, 1525 tracks. Kit RTL = NF15c kit_rtl export
  (head-sd9a/rtl_nf15c; same as sd9a RTL except NF15c clk_landing_ca/meso_fifo). Gen script head-sd9a/gen_sd9c.sh, log gen.log.
- reset_tree.tcl replaced (copy+mv) by the NF15c bootstrap tree (rtl_nf15c/bootstrap/hd_serdes/reset_tree.tcl) = the tree of the published
  wrapper: RTL-vs-tcl WRONG 0 (gen.py copy had WRONG 40; kept in KIT/source_gen_replaced/, record KIT/sd9a_reset_tree_source.json).
  0 relay sites in the moved u_chn rect. Preflight PASS. No RTL/cycle change vs sd9A (+2 RX edges DKREG1/DOREG1 as sd9A).

## Why sd9A failed (measured, 47 TT endpoints on sd9a_grt1 5_1_grt.odb, wns -189.61)
- 8 reset/start relay endpoints -81..-190 (start_o_0 -189.6, rst_o_0 -187.9, rrl_32->33 -182.7, srl_32->33 -143.7, rrl_72->73 -132.6,
  rrl_25->32 -112.6, srl_25->32 -81.2, rrl_81->82 -80.8). Cause: kit RTL = published wrapper tree (u_chn at 1900.8,250.56) but gen.py phys
  re-solved reset_tree.tcl from planA (u_chn moved) -> relay renumbering: 129/155 relay flops placed at another relay's site (rst_o pin reg
  u_rrl_34 at x=1345, 1165 um from its port; u_rrl_32 at the port). Face registers already exist (u_rrl_34/u_srl_34): no +1-cycle face-reg needed.
- Datapath (inside gate): enc rem_q[26]->rem_q[111] -40.0 (clk), dec u_syn S_q[7]->bm -15.7 (pma_rck), rest > -11.
- Source guard: claude/head-reset-tree-coherence-1116@b56e08e96e1 READY (GREEN 15/15, baseline 1), awaiting COORD approval.

## Plan-delta request posted to HEAD-DIE-R (posts d7547f44)
- u_chn (ot_s81_kp4_dchn 276.48x138.24 MY) origin 1900.8,250.56 -> 1548.0,109.44; keep the published-wrapper reset relay tree
  (or republish wrapper + reset_tree together). No cycle, pin or outline delta. sd9c qualification needs this plan event.

## Open for FABLE-FIX-HEAD-SERDES
- GRT read: rem_q slack, launch/capture arrival, HB4 on D (Fable predicts -40 at GRT RC, -45.9 ps skew; successor sd9d in FABLE-PD-HEAD-2045).
- DRT decision (see !! above), sign-off, LOOK at layout, export (ffht_export.sh pattern). sd9A/sd9B/Form C stopped (sd9B never run by this lane).
