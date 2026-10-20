# KV-D2D3 (2026-10-20): native census of the bound KV D2D sfm2 views + the sfm3 structural successor

Release tree: K.STA.D2D.1 (safe KV storage / validation transport), K.STA.LINKCFG (bc4 DCAL + boot image), K.STA.DCALCYC.
Branch claude/kv-d2d3-1020 (base claude/kv-sram-d2d-1019 1c6c02ed7 + main tools 360c64320).

## 1. Bound sfm2 views: NOT native-census clean

`tools/ref_tile/native_census.py` (main 042aa171b; Liberty roles from the loaded libs, reset / macro data pins count,
BUF/INV transparent, endpoint pins) on the ROUTED synthesis netlists (`routes/*/physical_artifacts/1_2_yosys.v`):

| view | status | roots | max | violations |
|---|---|---|---|---|
| qkd_d2d_static_r7w_sfm2-sfm2-1c6c02ed7 (GEN9-bound) | FAIL | 29,537 | 152 | 72 |
| qkd_d2d_static_ovl_sfm2-sfm2-a71ab049e | FAIL | 29,626 | 152 | 72 |
| qkd_d2d_cal_seq_pin_bc4-k22a-89fec6b77 (GEN9-bound DCAL) | PASS | 1,460 | 31 | 0 |

The lane census of 10-19 (`results/rtl/kv_sram_d2d_1019/census`, max 32) used its own yosys/ABC script, not the ORFS
synthesis the route ran; ABC there folded shared combinational selects into every endpoint cell. Classes
(`census_sfm2/classify_*.txt`, driver -> source registers -> sink registers):

* 62 + 4 nets: calendar image write enable `cfg_we && !running && addr == w` -> 32 bits x 2 pins = 64, predecode terms
  36 / 37 / 40 / 128 / 256 (TX and RX calendars).
* 1 net, 152: STATUS `!bad_hdr` (392 payload bits + epoch16 compare) reached all 156 capture bits.
* 3 nets, 48-57: epoch_begin copies ebc[1] (s1 pipe), ebc[2] (e pipe), ebc[9] (RX alignment hold + ev2).
* 2 nets, 36: cal_seg pin copy 0 (first[17:0] select), TX and RX.

The Codex objection (c9c068a71: SAT shows 19 TX calendar seg1[1] copies not one-edge convergent) is about the Codex
gate-level fork of 353123a8d, not the sfm masters: there sel1_c1 takes the master's D net (sel1_d), so it equals
sel1_c0 from the first edge for any init (MUTFO 1 = the self-hold class; RANDINIT + OT_FO_CHECK catches it). The
miters run the exact 66-write cold sequence (seg1 bases at 164/165 and 3164/3165, seg1 starts 260 / 3460 / 3660, base
rewrite 3640/3641).

## 2. sfm3 masters (rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm3.sv), 0 cycles, same ports

1. Calendar image: accept predicate registered as one-hot strobes `wq[2w+h]` (16 bits each) + data copies wd_lo / wd_hi;
   the entry register takes `ed = wq ? wd : e` one edge later and every reader (first0_q prefetch, seg1 select, pointer
   select) reads `ed`, which equals the as-built image on every edge. Decode reaches only strobe D pins; 4 KEPT running
   copies (16 strobes each). Unreset like the image.
2. STATUS: per-group KEPT copies hk_c (static header predicate) / he_c (epoch16 field) registered from rf on the
   rx_flit edge (same D word, equal from the first edge); 13 groups x 12 bits, each with its own compare.
3. epoch_begin: 17 external copies (slot link 12: s1_d / s1-s2 / s3-s4 / e1 / e2 / e3 split; end 4: eb8 + 3 RX-alignment
   groups; STATUS/KVN 1).
4. cal_seg: 5 KEPT pin copies per calendar (first[8:0] / first[17:9] / first[31:18] / pointer halves).

## 3. Benches (Verilator 5.050 / iverilog, ot-epyc7, exact kit job.json commands, `scripts`: kitbench runner)

Kits physical/ref_tile/qkd_d2d_static_{r7w,ovl}_sfm3 (geometry identical to the CLOSED sfm2 kits). Every bench PASS /
mutant FAIL as expected: lint, leaf_eq (+MUTW), miter FEG0 / FEG1 / RANDINIT (5,992 full-output compares 0 mismatch,
OT_FO_CHECK incl. the new copies), MUTFO 2 / 6 / 7, guard + MUTFO 5, pair bench KSF=3 (+LOCK, OVL, slot / user mutants),
new: SFM3 directed WPH phase (rewrite segment-first entries one edge apart, start at RX write + 2: 3905/3906 -> 3908 seg0,
4107/4108 -> 4110 seg1), MUTFO 8 (readers use the image Q = one edge late) FAIL at cycle 3972, MUTFO 9 (header copies
hold) FAIL FO_COPY_MISMATCH, MUTFO 1 (seg1 self-hold copy) FAIL FO_COPY_MISMATCH. Witness logs:
results/closure_witness/qkd_d2d_static_{r7w,ovl}_sfm3/.

## 4. LINKCFG

GEN9 (claude/kv-gen9-1019 abbb4391c) binds the bc4 DCAL view byte-identical to closure record
qkd_d2d_cal_seq_pin_bc4-k22a-89fec6b77; its source d2d_cal_image.svh / _mu.svh / ot_qwen_d2d_cal_seq[_bc4].sv /
qkd_d2d_cal_seq_bc4.sv / qkd_d2d_cal_seq_pin.sv are blob-identical to GEN9's, D2D_TXDP_K = 32'h03030416 [22,4,3,3].
The sfm2/sfm3 kits compile TXDP 0x03030416 (pair benches grep it). Status readers for dcal adm_done/cal_ready/running/
layer and d2d recovery_cycles: KV-FRAMEPINS fc93e83d3 merged in GEN9 abbb4391c (OT_KV_HOST_OBSX=1, default off).

## 5. Gate native census (the mandatory PRE_GATE_NATIVE_CENSUS hook on the gate's ORFS synthesis)

| rev | commit | r7w_sfm3 | ovl_sfm3 | remaining class |
|---|---|---|---|---|
| r1 | 0e17d840a | FAIL max 41, 99 roots | FAIL max 37, 81 | 16-b image strobes fold into each reader mux (~2.5 pins/bit) |
| r2 | 508cde0dd | FAIL max 38, 2 | FAIL max 36, 2 | shared seg_we / write predecode net (cfg_we, addr[5], running) |
| r3 | aabf2e6ad | **PASS max 32, 0 violations, 30,739 roots** | **PASS max 32, 0, 30,876 roots** | -- |

(`census_sfm3_r1_*.json.gz`, `census_sfm3_r2_*.json.gz`, `census_sfm3_r3/*.json.gz`; r3 gates ot-pve1
ref_gate/qkd_d2d_static_{r7w,ovl}_sfm3-20261020-025653, past floorplan into placement / CTS.)  role_errors 0.  The 5
constant output bits (fdi_tx_flit[554..557], [566]) are the link flit body's protocol framing constants
(body = {0, e3, 0, 1, 00, s3, q}), checked by the receiver's slot_bad, unchanged from sfm2 -- not a tied port.
r2 -> r3 benches: 34/34 as expected on r3 (bench_logs/, scripts/kitbench3.otrun.log).
