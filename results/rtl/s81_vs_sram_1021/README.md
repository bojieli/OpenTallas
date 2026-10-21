# S81 VS SRAM successor (candidate, default off)

Source 474637070, define OT_S81SL_VS_SRAM. Eight 32x128 SRAMs store eight
logical 8x64 parity/copy banks (4096 useful bits). Read ports share predicted
next counter addresses; phase-exclusive REDUCE/ADD/FLUSH reads permit one
read per bank. Same-edge read/write bypass is split into 16-bit groups.
Default RTL remains byte-equivalent outside the define.

Existing leaf ENG bench (Verilator 5.050, seed7) PASS: partials4, half_rows16,
mismatches0, faults0; reduce_cmd_to_last_partial159, add_cmd_to_last_write73.
Existing MUT7 caught16 wrong rows with the same measured latency159/73.
Original logs retained here. Existing VS base/MUT9 and actual-Lib mapped
native census remain live. No layout gate, kit, route or adoption yet.
The intended zero added edges is demonstrated only on this ENG case so far.

SAFE planning: pins preserve existing registered seams; reach and clock require
new macro floorplan after census; fanout must be measured on mapped output;
storage is SRAM under the define; depth requires census/mapping; macro
lattice/utilisation/regions are not yet a built or qualified layout.
No input, clock, uncertainty or protocol constraints were relaxed.
