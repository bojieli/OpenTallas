#!/usr/bin/env python3
"""CLAUDE S81-PH: regenerate rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv from ot_hdc_v41x_sel_ctl (see its header).
The generation was done once in the 2026-10-07 commit; this stub records the source and the edits:
  module rename; WAIT / HOLD / HC0 / HF0 / CLRW = 2 x the slow-edge latencies + gate phase, XRH = XR/2 - 2;
  u_cs / u_fs on ck_h = clk & latch(hen) with XR = XRH; the C_W2 res_eq wait + 2."""
