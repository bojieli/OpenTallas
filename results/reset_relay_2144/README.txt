Opt-in reset.relay_driver + reset.relay_pad_spread; defaults off.
Purpose: q_hub_nw G2 FF-2.93ps/1260 back-to-back relay holds and37slew violations, no timing relaxation.
Internal raw/run/gated relay: flop + explicit kept BUFx4f_ASAP7_75t_R. Boundary u_rst_in/u_run_in and rst_o/start_o relay outputs retain plain direct flopQ. Physical reset hook places and protects each internal driver beside its source register. G2 uses same driver in raw/run model.
Padspread: identical relay graph/depth/names, legal incoming L path sites at>=20um spacing where available, obstacle/wall checks; short/blocked remainder and interior tap's own pad chain remain stacked. No control/function/schedule cycle change.
Exactness: lockstep_r3 checks generated depth7 two-tap reset tree + gated reset/START cell,500edges,SYNTHESIS primitive path PASS. Inverted-buffer mutant_r3 caught edge11. Added boot/production cycles0.
Focused reset tests:14tree/drive +23wavefront/startrole/coreleaf PASS.
Initial bench compile FAIL used reserved SystemVerilog module name ref; retained initial source/log. Corrected r2/r3 bench golden module. No design waveform failure on corrected positive control.
Physical q_hub trial not yet evaluated; no SIGNED/adoption claim.
