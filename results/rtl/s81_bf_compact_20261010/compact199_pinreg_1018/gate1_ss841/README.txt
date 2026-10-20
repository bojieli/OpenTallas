Gate 1 (HOURLY-S81/C199, 10-19): Codex compact199 pinreg gate rerun with pinflop_band.tcl scope fix (proc globals).
Band: 839/840 ports register-at-pin (skip a_ctr[13]); all 61 PQ output bits (pnseg/prow/ppos/pval/pseg) and all 10 failing capture pins banded; check_placement clean.
Clock (CTS, ck.json): boundary TT 554.0-622.2 (spread 68.2) FF 442.8-491.7 (spread 48.9) -> <=80 PASS; mean 592 TT (closed view R 517).
Native TT probe (CTS placement RC): capture max 44.6 ps (i2x_q0[99]) PASS (was 206.7); launch max 517.6 ps (pseg[2]), 64/64 outputs >220 FAIL (was 243).
Cause: route-time IO reference CK_SS_MEAN=841 (stale) vs measured 592/594 -> CTS hold repair (hold WNS -306, ~26k buffers) padded ~23 BUFx2 (~450 ps) between each PQ flop and its pin;
  under the signoff SDC (L measured) the same output has +404 ps hold slack. PQ flops (pseg[2]$_DFF_P_) are NOT g_pin.r_* so they sit on the ordinary tree (559 ps), not bf_pinclk.
Next: gate 2 with CK_SS_MEAN=594 (measured pin-group mean) -> /srv/opentallas-scratch/claude/s81-c199-pinreg-ss594 on ot-epyc4.
