# QW-CALR ctlm9c: CTLM successor with PRIVATE_CALR=1 + F16WTN=1 (Q.STA.TTC.4), 10-20

## Decision: CALR=1 is REQUIRED for the release (not droppable)
Without CALR the CTLM calendar is CALD: entries live in the 1024-PW programme store, base >= 16 x programme words.
- Release programme = 25 ISA instructions = PW 0..399, so CALD holds at most (976-400)/2 = **288 entries** (nent is also 9 bits <= 511).
- The real CALR10 image (rtl/test/qwen_dv/calr_port, 7e515 lineage) has **1009 entries**; the decode-layer descriptor ALONE
  is **406** > 288. So the full decode layer cannot be installed: the seal faults (fault_code[4]).
- dv_layer (TOK.QW.LAYER.4 "PW capacity") already records it: one layer needs 13,942 PW (calendar 854 + slice tables
  12,608 = (PROG 72 + BTAB 188 + CROM 528) x 16) vs CMD_CEIL 976, and CROM post-scales / norm gains differ per layer
  (36 x), so a per-layer table stream is needed. Without TABLE_ROM there is no per-layer table load, so layers 2..36 run with
  layer-1 norm gains / post-scales and produce **wrong tokens**. CALR (CALENDAR_ROM + TABLE_ROM -> table_req -> the CLOSED
  qfd_dv_slice_tload ROMs, 3,816/4,096 rows = 93.2 %) is the release fix.
Exact capacity (tools/qwen_romcap/calr_capacity.py, branch claude/qw-calr-ledger-1020): 1009/1023 entries (98.6 %, 10-bit
limit; 253/4096 ROM rows), 36 LOCAL4 table loads = stages 1..36, every first entry T_0 >= 8 (= 5 + NU-1, the +1 CALR fetch
edge) -> PASS. Two ROM266 (121.8 x 62.9) + the closed wtn (86.4 x 77.76) fit the free NE area of both TTC8 outlines at lattice
slots m0 (475.2,388.8), m1 (475.2,475.2), wtn (648.0,388.8): fill safe8u 46.6 -> 51.0 %, safe8bu 50.0 -> 54.7 %.

## Netlist + bench (Verilator 5.050, fleet)
- Source = claude/qw-ctlm8-1020 833cae8db (= the r7 candidate8 source of lp8_np) + chparam PRIVATE_CALR 1 / F16WTN 1, the wtn
  bound as the CLOSED hard child (blackbox abstract wtn_bb.v; view physical/ref_tile/qfd_tt_ctlm_dv_wtn, record wtn1-9fa6fd27d).
- Depth fix (this branch): qfd_dv_calendar_rom range check moved behind the request pin register (first try: 1290.3 ps / 40
  levels through calendar_rom.sv:28-29; now **718.5 ps / 24 levels**, r7 params-0 baseline 686.8 / 23). valid/data edges
  unchanged; a bad request raises `fault` +1 edge later (fault only; rom_mis still faults on the valid edge).
- Bounded netlist rtl/qwen_dv/lp9c_np (construct 67,448 -> 68,627 cells, 13 macros incl. 2 ROM266 + wtn): native census
  **PASS max 32**, textbook WARN (ck_core 11,904 FF + 12 macro pins; ck_hr 5,184), reset 1 sink, in->out 0.
- Landed lockstep tb_np9 (flat qfd_tt_ctlm_dv_lpf CALR=1/WTN=1 vs np netlist at the lp record offsets):
  random rnd_mut0 PASS / mut1, mut2 FAIL; directed CALR (real image installed through dh: image_ready=1 at warm 1150, 39
  descriptor starts for 4 users read from the two ROMs, 4,510 cmd edges) calr_mut0 PASS / calr_mut2 FAIL / calr_rommut
  (np m1 macro loaded with m0 content) FAIL -> the ROM data path is observed. CALR_ROM_LOADS 4.
  Bench-local ROM266 model copy (ot_rom_4096x266_m8_calrbench.v) only adds +CALR_ROM_DIR loading by instance suffix (the np
  netlist drops INSTANCE strings; the die ROM_BIND binds content).
- Unit regression calr_port (ported cal_mu == F16 reference, both on the fixed ROM): m0 PASS 1,059,923 edges, 1,871 issues,
  144 table loads, 0 mismatches; m34 FAIL 5,750; m2 FAIL. run_calr_port.sh source list fixed (observer_p, ot_ks_add).
- Not covered at parent level: table_req pulses (0 in the directed run) -- table loads are explicit-range starts (OPSEG
  leaf), and the leaf ROM in both sides is empty; covered at unit level (144 loads edge-exact) and f16_tload bench.

## SAFE checklist (ctlm9c vs ctlm8)
1 pins: unchanged landed record (f16_auth/f16_obs in from hr, f16_st/table_req out of hr, landed since CTLM5) PASS.
2 reach: ROM266 at x 475-597 vs calendar glue x ~215-260: <= ~380 um; gate decides. 3 fanout: native max 32 PASS.
4 depth: 718.5 ps / 24 lv (guidance 600; freeze: route timing decides, same class as ctlm8 686.8). 5 storage: calendar in
2 ROM macros PASS. 6 floorplan: slots above on 43.2 lattice, fill 51.0 / 54.7 %. 7 clock: ROMs + wtn on ck_core (raw sinks).
8 schedule: CALR fetch +1 = 0 cycles (T_0 >= 8 in the image); table load priced serial 124 cyc/layer bound (ledger).

## OPEN (release blockers named)
- PRODUCER: no compiler issues the 36 per-layer LOCAL4 ranges for user 0 (the OPSEG leaf refuses user 0 entries; the dh
  face start carries no range) -> mu_opcal / leaf (or a LOCAL4 inside the decode descriptor with stage-relative field) owed.
- Die GEN: bind table_req (CTLM -> slices beside cmd), f16_auth (SYSFACE u_join), f16_obs (slice typed events); ROM_BIND
  content for u_gi.u_cal.g_calrom.u_rom.m0/m1 (calendar_m0/m1.viamap.hex).
- Kit safe9c (= TTC8 winner + 2 ROM266 + wtn child + lp9c_np) + gate after TTC8's safe8u/8bu verdict.
