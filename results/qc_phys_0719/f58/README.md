# QC RP1 f58 -- structural control replica (PATH-QC-RP1, 2026-10-25)
Kit epyc1:/srv/opentallas-scratch2/claude/path-qc-rp1/f58 (from f57r4: same scripts/SDC/pins; run starts at CTS).
- 3_place = f57r4 retained 3_place + rp1_ctl_replica.tcl: replica u_c1w (DFFHQNx1 + INVx3 decode inverter), same D (pcr_addr[3]),
  same clock, placed at the W1 consumer centroid (30.73,171.99); drives g_cbk mask 0xABBF (12 W1 consumers); +0 cycles.
- Kit RTL carries the same replica (rtl_patch.diff, kff ID 3401). LEC (tools/die_plan/lec.py) f58 placed netlist vs kit RTL:
  3543/3553 proved, 10 UNPROVEN = u_twca *_mif gate-only anchors to g_crb[1].w_addr_in -- IDENTICAL in the f57r4 baseline
  (lec_f57r4_place_baseline.json), not from this change. Exactness of replica: codex/rp1-control-proof0719@19dc8bd8d8.
- Proto (CTS + GRT, no hold repair): replica on clknet_leaf_16_ot_ctap_W1_n with all 12 W1 consumers; their FF hold at GRT
  +17.85..+18.50 ps (f57r4 routed -11.10..-13.91); W0 four +12.2; replica D +88.7 hold / +614 setup. TT setup 217.38.
- Route via autopilot after GEOM PASS: run_f58.sh (f57r4 route flow, GRT FF hold repair with OT_VCLK_FF=auto, signoff --ff-vclk auto).
