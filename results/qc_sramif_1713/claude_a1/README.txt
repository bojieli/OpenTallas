PATH-QC-SRAMIF2 2026-10-25 place-only prototypes of the NEW R0 prog/btab 354.24x259.2 profiles (Codex a1.1, CK 177.132/.042 M5 per 2bc3495e27).
Same 1_synth netlist (copied from signed prog_s8b / btab_s8 kits; keep_check 21/21), fresh floorplan+place only, no CTS/route.
M = signed recipe (face_flops + macro_pin_flops), macros R0.   P = Codex planned_if_sites FIRM (released at DPL).
F = M + SRAM macros MY (LEF SYMMETRY X Y): rd_out/addr/clk + 137/136 wd pins move from W to E edge, facing the E-face read ports.
             F6 max   r2r max  p99    >290  >405
prog M       9.9      422.6    384.5  552   1      (old signed prog_s8b 3_place: 446.4 / 416.7 / 512 / 90)
prog P       13.7     414.7    384.8  769   1
prog F       9.9      322.8    292.5  49    0
btab M       11.4     354.9    320.3  565   0
btab F       11.0     336.2    283.9  49    0
r2r = geometric launch->capture Manhattan um (r2r_reach.py), every flop Q through comb cells to next flop D / macro pin / out port.
Kits: intel2:/srv/opentallas-scratch2/claude/path-qc-sramif2/prog_a1{m,p,f}, intel1:.../btab_a1{m,p,f}.
