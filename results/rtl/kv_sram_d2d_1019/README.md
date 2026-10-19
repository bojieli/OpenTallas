# KV-SRAM-D2D: right-sized D2D slot store + safe KV D2D source (claude/kv-sram-d2d-1019, 2026-10-19)

Scope: release tree K.STA.D2D.1 (safe KV storage and validation transport) and Q.STA.D2D.2 (KV twin safe source).
Base: the safe fan-out masters `qkd_d2d_static[_ovl]_sf` (claude/kv-d2d-1019 8cbe74cd0, census max 32).

## Why

* Codex HOLD 12:48: the sf / sfb kits store the 548-b slot payload in 4 x `ot_sram_1r1w_64x512_m1_r2c2`
  (LEF ec986c5e, 171.288 x 77.784 um), using 137 of 512 columns; W / E faces 793 / 792 signal pins = 10.195 / 10.182
  pins/um (> 6).  375 tied-zero columns per bank = 3,008 tied endpoints.
* The four sf / sfb CTS gates (fa42fd5d3) were WARN with negative reg-reg slack: r7w_sf -16.1 ps and r7w_sfb -23.4 ps
  at `u_rec.n[15]` (the recovery's 16-b drain counter), ovl_sf -95.5 ps / ovl_sfb -100.7 ps at `u_ctl.abc[*]` (receive
  CRC tree -> compare -> fault OR -> 13 epoch_abort copies in one stage).

## Storage family (truthful, generated)

`tools/mem_compiler/build_d2d_sram_1019.py` runs the repo generator (`sram_gen` + `build_aligned_v2`, the same code as
every catalog macro) for exactly the shape the logic stores, 64 words x 137 b, 1R1W, 2 spare rows / columns, with one
change, the signal-pin pitch.  Views (LEF, TT/FF/SS lib, behavioural .v, blackbox) in
`physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p{192,288}/`, index `d2d_sram_index_1019.json`.

| macro | size um | W / E pins | pins/um (max in 1 um) | TT clk-q / setup | area um2 |
|---|---|---|---|---|---|
| ot_sram_1r1w_64x512_m1_r2c2 (old) | 171.288 x 77.784 | 793 / 792 | 10.19 | 366 / 28 ps | 13,323 |
| d2d_sram_1r1w_64x137_m1_r2c2_p192 (primary) | 57.912 x 45.672 | 229 / 229 | 5.23 (6) | 323 / 28 ps | 2,645 |
| d2d_sram_1r1w_64x137_m1_r2c2_p288 (fallback) | 57.912 x 67.512 | 229 / 229 | 3.49 (4) | 323 / 28 ps | 3,910 |

Capacity / width / lifetime kept: FW 548 = 4 banks x 137 b, 64 slots (6-b slot address, the written-map lifetime),
same ports, same read / write timing (same generator model: registered write port, registered read), so the leaf's two
write-age bypasses (same-edge and one-edge-old write) are unchanged.  Names carry `d2d_` (no collision with the Qwen
compute-die `ot_sram_1r1w_64x137_m1_r2c2_p192` candidate, which is NOT used, nor with lane KV-SRAM-CTL).

## Source (generated: `tools/qwen_split/d2d_sram_masters.py` -> `rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv`)

Masters `qkd_d2d_static_sfm` / `qkd_d2d_static_ovl_sfm` (params SRAMV 1 = p192, 2 = p288; FEG 1 = guard on), derived by
exact text substitution from the sf sources (untouched; every closed / gated view still binds):

1. slot-store bank `ot_qkvd_llr_replay_sram_leaf_sfm`: the right-sized macro, all 137 columns written, no tied columns.
2. `ot_qwen_static_slot_ctl_sfm`: the receive CRC is computed on the arriving pin-flop word and registered on the same
   edge as `rf <= p_rx_flit`, so `rx_crc == crc(rf)` from the first edge; the fault cone loses the CRC tree.
3. `ot_qwen_d2d_recovery_sfm`: drain / reset counter `n` is 5 b (bounded by max(DRAIN, RSTC) - 1 = 31, cleared on
   every entry); it was 16 b.
4. First-epoch guard `ot_qwen_d2d_cal_sfg` (both calendars): receipt of every image write the image actually accepts
   (`cfg_we && !running`, 32 entries + segment-1 base) since the local cold POR (the image is unreset, so a warm rst_n
   keeps image and receipt; writes inside the 4-edge rst_n release window -- the DCAL cold INIT timing -- are counted).
   A start is authorised only with the complete receipt, no write on the start edge or the edge before (earliest start
   W+2) and no earlier rejection; an unauthorised start does not start, raises the calendar fault (-> end_fault ->
   epoch abort) and poisons the calendar (halted until local rst_n): fail-stop, never queued.  4 KEPT authorisation
   copies (one D net).  No port, 0 cycles on the healthy path.  Contract: POR released >= 6 edges before the first cfg
   write (an earlier write is not counted -> the start is rejected, fail-stop).
5. Z17 sideband `rx_zero17[16:0]` (Codex fe8eac3f2 / 8ec58f314 definition: Z0 = |[31:19], Z1 = |[31:5],
   Z[z+1] = |[32z +: 32], z = 1..15), 17 unreset flops on the exact `q_rx_payload` pin-flop edge; S-face pins after
   rx_payload.
6. TXDP: kits compile `TXDP = 0x03030416` (the GEN8 die code); every pair bench greps `QKD_D2D_TXDP = 32'h03030416`.
   Reset: unchanged sf structure (ot_rst_pipe 12-copy families, OT_RST_COPIES_MAX 24, reset_landing 2 stages).

## Evidence (ot-epyc7, Verilator 5.050 for the miters / leaf / guard, iverilog for the pair bench; logs in `logs/<kit>/`,
mutant witnesses in `results/closure_witness/<kit>/`; every bench is the kit job's exact command)

* `run_d2d_sram_leaf_eq.sh` (tb_d2d_sram_leaf_eq): as-built 64x512 leaf vs right-sized leaf, 100,000 random edges
  (6,649 age-0 / 3,289 age-1 bypass hits, 90,694 macro reads, all 137 bits random) 0 mismatches + 64-slot lifetime
  scoreboard (write every slot, idle 500, read back) PASS, p192 and p288, zero-init and X-init.  MUTW (column 136 not
  written) FAIL.
* `run_kv_d2d_sfm_miter.sh` (tb_kv_d2d_sfm_miter, as-built qkd_d2d_static[_ovl] vs sfm): FEG 0 every output every edge,
  5,992 compares 0 mismatches (both 66-write cold sequences, lifecycle, multi-entry program, random phases incl. 548
  one-hot RX words), ord / OVL, p192 / p288; Z17 oracle on every edge.  FEG 1 PASS in the legal windows with 2,000-3,000
  guard rejections in the random phases; RANDINIT (every variable random, OT_FO_CHECK copy == master) PASS.
  Mutants FAIL: MUTFO2 bypass select, MUTFO6 CRC one edge late, MUTFO7 Z17 flag 0 without bit 19.
* `run_kv_d2d_sfm_guard.sh` (tb_kv_d2d_sfm_guard): A missing entry -> no TX start, fault, RX authorised, no retry after
  the late write; B start at W+1 rejected per calendar; C W+2 runs, no fault; D POR clears the receipt; E warm reset
  keeps it; F writes inside the rst_n release window counted.  PASS ord / OVL; MUTFO5 (TX guard off) FAIL at A.
* `run_d2d_dies.sh KSF=2` (compute end + KV sfm end, TXDP 0x03030416): PASS 198/198 frames, 6 results, 24 KVN, 0 faults;
  LOCK 1,192 edges 0 mismatches; OVL user tags tx 198 / rx 206; mutants slot / OVL user FAIL.
