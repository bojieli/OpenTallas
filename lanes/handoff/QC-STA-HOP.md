# QC-STA-HOP handoff (parent QC-ALLFIX). Updated 2026-11-25 08:50 PST.
Cause (CORRECTED 07:53): st_a b_hw_ctl_hc0 is a LANDED ft slot with explicit_stage0 + 5 bit_sites stages. The face_flops landed loop gives station i key i+1
and puts the last station at the out face, so bs[0] is dead and ring -> bs[1] = 653 um plan / 438 um placed (186 bits). 07:31 "artefact" claim was WRONG.
Checker: main 01b2d3adc8f (die_hop_scan explicit_full/landed model, adv_g0_hops, ft_reach_fix/ft_s0_resite skip, int casts). Fable r1 FAIL, r2 PASS-WITH-NITS.
  Latent nits left: explicit stations-1 S0 lane offset; ft_reach_fix/ft_add_station S0 for explicit; check.py:239, ft_station_probe, ft_xtap sibling models.
Row STA-HOP: 10 st_a types (W5 clf4365a62 to QC-STAV2-F436), b_hw_ctl_hc0 stations 5->6, explicit_stage0 dropped, regs_um[0] = in-pin centroid,
  bank_taps u_ft_b_hw_ctl_hc0_o_0..5 re-tapped (nearest plan_tree_taps to bank_xy), latency.lanes sl_{E0-5,W0-4}_ctl__b_hw_ctl_hc0 +1 stations/cycles/natural.
  Order (QC-ALLFIX accepted 08:4x): BANKRST-LAND c78ca1b08c5b FIRST, STA-HOP v3 built on it. v1 6b124ad8f7bd / v2 (aa3a base) superseded.
Script: epyc10 /srv/opentallas-scratch2/claude/QC-STA-HOP/row_sta_hop_v2.py (TREE launch_hop + ovl); outputs row/plan_sta_hop_c78c.json + ledger.
Trees (epyc10): launch_hop (PRE, clean), launch_hop2 (bind, forking). epyc12 tree_bind deleted (.fork.json write-through incident 08:44).
Next: PRE v3 (pre_hop.sh c78c on launch_hop) + scoped bind (bind_hop.sh ROWSHA, set T=launch_hop2) + latcheck; ROW-READY after BANKRST-LAND ROW-READY.
Cleanup owed: ot-delete epyc10 launch_hop.forking-3331121, .forking-3451048.
