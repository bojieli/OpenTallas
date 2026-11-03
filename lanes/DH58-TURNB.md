# DH58-TURNB (helper of DIE-HEAD-58) — hd_turn_b RE-FORM (HEAD-045)
2026-11-03 14:34 PST DONE. Branch claude/dh58-turnb-1103@67f6d898239 (off rfplan c54bb8dd6db + main). Prepared intel2 /srv/opentallas-scratch2/claude/dh58/turnb/prepared_l48tb (event l48tb, plan 66536ebb5c20, sidecar bbdd2f7b5ad1 unchanged; only hd_turn_b republished; k_delta_l48tb.json).
Cause: raw cland_fstart_in_t_i (166.6 ps in) = ring writer start broadcast to 4x568 write enables (853 ps buffer chain), TT -73.1; DRV = same broadcast + dsel select INVx3->66 loads (429 ps slew).
Form: WREG-1 (face-registered writer start + 36 kept per-(slot,chunk) enable flops) + DSREP-1 (4 select copies/chunk); strap K+1 on 12 turn_b instances (59->60), 0 data cycles. Sim proof results/dh58_turnb_1103/wreg_equiv PASS, mutant caught.
Estimate: quick-place fstart +22.3 -> +580; worst becomes t_i input-contract path (QP +52.7, routed today +71.3, unchanged). GEOM: aspect 4.05 advisory (unchanged), rest PASS.
Kit source needs the RTL (rtl/common ot_dp_clk_landing_ca.sv + ot_meso_fifo.sv) on top of HEAD src 69e06c8b939; patched copy intel2 dh58/turnb/hsrc.
hd_turn_a: same cause (raw fstart broadcast, real-parent TT -55.8, WFALL T/2); not in l48tb; spec {"hd_turn_a":{"buses":["t_i"],"dsrep":4}} if its l48rf run fails. Note: l48rf published turn_a lacks WFALL(1) although plan ring_hold.write_fall_types lists hd_turn_a (republish adds it).
Units alive: none.
2026-11-03 15:05 PST UPDATE: turn_a added to l48tb (WFALL republish + WREG/DSREP 4, K 60->61 x12) @8c0ecb9755f, plan 7afa351d779a. turn_a QP kit SDC +44.8->+62.4; IOHP SDC fstart -348.5->+165.8 but t_i -354 (ft budget vs T/2 fall capture, contract issue). Units alive: none.
2026-11-03 15:45 PST UPDATE: FREG on turn_a @67cc18d2e8e plan f9623a82a239: K 60->62, +1 data cycle (bench proof). t_i under the corrected contract: +0.8 ideal / +156.5 after CTS with hold -102 (repair ~100 ps -> ~+55); +83 is not reachable on t_i under the 699.72 budget. Units alive: none.
