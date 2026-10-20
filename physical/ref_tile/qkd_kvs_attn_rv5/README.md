# qkd_kvs_attn_rv5 -- rv3 successor r17: SYNCHRONOUS RESET of the attention calendar S1..S9 (KV-ATTN4 10-20, COORD 09:56)

Top `qkd_kvs_attn_fl` (rtl/lib/face_land/qkd_kvs_attn_fl_r17.sv) -> `qkd_kvs_attn_r17` (rtl/qwen_sys/kv_bootage_20261019/qkd_kvs_attn_r17.sv). Geometry 216.0 x 216.0 um exact. Sibling kits rv5 (216, = rv3 slot) / rv6 (302.4, = rv4 / ba1 slot) gated in parallel; bind the first to close.

## Change vs rv3 (r16) -- why
rv3's native parameter audit stayed NOT PROVEN 1089/1091 after the witness fix-point (KV-PARAMS6 09:04): 542 gold-only
registers of the UNRESET calendar data stages S1..S9 (qkd_attn_cal_gen_r16) carry a pre-reset value into the induction
(Codex CEX step 7/8; the pipeline is 9 deep, the reset base 6).  Those stages are control state (their values become the
compiled calendar, tx_first / end, the calendar fault), so under the owner 10-20 reset rule (control/valid reset, datapath
unreset) they get a SYNCHRONOUS reset from the landed rst_n.  Nothing else changes: module suffix _r16 -> _r17, same ports,
same edges, same parameters (RETIRE_STATIC=1, STATUS_DELAY=213).  0 added cycles (no KV-GEN9 hand-off).  Datapath (result
face 512-b beat, RX record, TX launch) stays unreset.
Reset loads: +~1,100 S1..S9 bits -> kit reset_landing 2 stages, 4 first / 96 final kept copies (rv3: 2 / 48), <= 32 loads per
copy (ot_rst_copies split, reset_relay_split max 32).

## Benches (Verilator 5.050, fleet)
* rv_pair_bench.sh RVB=r17 RS=1 SD=213: whole-tile pair vs ba5 (B = A + 1 edge, 11 modes) PASS; mutants 1-7 FAIL (witnesses
  results/rtl/kv_attn4_1020/r17rs_m*/verdict.log).
* cal_rst_bench.sh: random power-up state (--x-initial unique, 3 seeds): every S1..S9 data register reads 0 after reset, one
  command still completes -> PASS; MUT 8 (= the r16 form, no data reset) FAIL (results/rtl/kv_attn4_1020/calrst_m8/verdict.log).

## Safe-design checklist (owner 10-19) -- unchanged from rv3 except item 1/3 reset
1 Pins: PASS (RTL-registered faces as rv3); reset lands in 2 registered stages at the face (kit, balanced 4/96 copies).
2 Reach: PASS by model (rv3 gate reach 84.6 um at 216); measured by the gate.
3 Fanout: kept copies as rv3 (<= 16 flops per copy); reset leaves <= 32 loads; in-gate native census (GATE_NATIVE_CENSUS,
  mapped netlist) must report max <= 32 / 0 violations.
4 Depth: PASS -- the sync reset adds one AND level on S1..S9 D pins (calendar stages are ~6-10 levels).
5 Storage: PASS -- no runtime-indexed arrays (S1..S9 are 9 distinct schedule points, ~1.1 kb total, not a memory).
6 Floorplan: no macros; pin-limited square, full-core rows.
7 Clock: S-centre clock pin + local spine (one region); pin-flop spread <= 80 TT/FF measured by --cts; io_hold_margin 0.03.
8 Schedule: static; 0 added cycles.
Native census numbers + gate facts: lanes/KV-ATTN4.md (this README is gate-consumed).
