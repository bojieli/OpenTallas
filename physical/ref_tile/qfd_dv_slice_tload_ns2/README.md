# qfd_dv_slice_tload_ns2 (QW-F16SUB 10-19) -- structural successor of qfd_dv_slice_tload / _b

Both tld1 gates FAILED clock_rule (TT/FF pin-flop spread 105/95 ps and 90/79 ps): the 1,051-bit stream-in band (W) and the
joined-out band (E) sat 300-390 um apart on opposite faces with the clock entering on N over the ROM rows; fill 24/32%.
Successor (same RTL, same edges): stream in on **N**, joined out on **S**, clock on **W at mid-height** between the two
register bands. The N->S bus crosses the ROMs on vertical M5 (ROM OBS = M1-M4 only); nothing crosses W-E over the ROM
M4 blockage. PARALLEL fallback 388.8 x 259.2, ROM rows centred, wider E strip (fill 32%, fill_reason pin_bound).

## SAFE-DESIGN checklist
1 Pins: PASS -- kit pin regs on every input/output (pin_regs enable, keep_pin_regs); reset_landing 2 stages; RTL face reg on treq.
2 Reach: PASS -- N/S bands <= ~240 um apart, every single-cycle hop < 405 um.
3 Fanout: PASS -- loader write enable as 34 kept tw_we copies (WE_COPIES, <= 32 select loads each).
4 Depth: PASS (tld1 gate: no setup/depth fail; only clock_rule + fill failed).
5 Storage: PASS -- tables in 4 x ot_rom_4096x266_m8 macros, no flop arrays.
6 Floorplan: fixed -- macros 2x2 on the 43.2 lattice, ROM pin faces (W) open onto >= 43 um capture channels (4.5 pins/um),
  pins on full N/S faces (~3.0 pins/um), aspect <= 1.6, std-cell band across the full width under/over the ROM rows.
7 Clock: fixed -- clock entry W mid-height between the two register bands; target pin-flop spread <= 80 TT+FF; io_hold_margin 0.03.
8 Schedule: PASS -- no RTL change, no added edge (f16_calr_edges.py prices unchanged).
