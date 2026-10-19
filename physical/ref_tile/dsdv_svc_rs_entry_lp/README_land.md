# S81-CTRL-SVC 10-19: landing SRAM regen (OT_SVC_LAND_SRAM)

Why: the three 369345f28 gates (lp / lp_np / entry_lp) timed out after 8 h in yosys (`synth` coarse OPT loop 4.3.x,
11+ rounds of opt_muxtree/opt_share/opt_dff, log on ot-pve1 ref_gate/dsdv_svc_rs_lp-20261019-000640). Cause: the attention
landing `land[0:639]` x 256 b in dsdv_svc_att, a flop memory with 3 runtime writes (PC 0 / PC 1 responses, ROWS) and 4 runtime
reads a cycle (the 4 release lanes); SYNTH_MEMORY_MAX_BITS 163840 kept it in flops = 164 kb + four 640:1 x 256 b read muxes.
Fix: 12 x ot_sram_1r1w_256x256 = 4 row banks (row[1:0] = release lane) x 3 write copies (one writer each: no bank write
conflict by construction) + a 640 x 2 live-value table; banks read at the release edge (rc - 1), SRAM read-old == the flop
version's nonblocking read: 0 cycles added, bit-exact by construction (16-slice benches base ST0/ST2 + mut6 running).
SYNTH_MEMORY_MAX_BITS 20480 so no >20 kb flop memory can come back.

Safe-design checklist (this regen):
1 Pins: unchanged (source-registered faces, reset landing in RTL rs_rl) -- PASS.
2 Reach: land banks W stack (bank 0 / 2) and E-mid (bank 1 / 3) beside the engine staging columns; Q -> 3:1 LVT mux -> engine;
  gate measures placed reach -- OPEN (gate).
3 Fanout: lw write data fans to 4 banks of one copy (4 macro loads) -- PASS.
4 Depth: LVT read 640:1 x 2 b + 3:1 x 256 b mux after SRAM Q -- PASS (to confirm at gate).
5 Storage: land 164 kb -> SRAM (fixed). STILL FLOPS > 2 kb (single-write FIFOs, depth <= 32, no synthesis blow-up):
  wq 6 x 8 x 341, sw 32 x 512, pvq 8 x 2120, qmem 16 x 512 -- OWED (next: 32x546 / 64x512 SRAM rings).
6 Floorplan: macros on the 43.2 lattice except two N-S abutted stacks (W x 43.2 MY, E x 1425.6; SRAM N/S faces bare,
  pins on the W face -> MY faces E); macro face pin density is the library's (821 pins / 41 um) -- WAIVED (library).
7 Clock: unchanged (ck_c / ck_sm roots, landed crossings) -- gate measures spread.
8 Schedule: static; 0 cycles added -- PASS.
