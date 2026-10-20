# qkd_kvs_attn_rv2 -- STRUCTURALLY SAFE attention tile (registered RX validation), face-landed view qkd_kvs_attn_fl (KV-ATTN2 10-19)

Top `qkd_kvs_attn_fl` (rtl/lib/face_land/qkd_kvs_attn_fl_rv.sv) -> `qkd_kvs_attn_rv` (rtl/qwen_sys/kv_bootage_20261019/qkd_kvs_attn_rv.sv).
Ports = fl_ba5 / bs1 (boot-age i_ctl 109 b).  Geometry 302.4 x 302.4 um exact.  Sibling kits: qkd_kvs_attn_rv1 (216, main) /
qkd_kvs_attn_rv2 (302.4 = the ba1 die slot, parallel fallback) -- gated and submitted in parallel; bind the first to close.

## Structural change (tree K.STA.ATTN: core TT -569.32 ps / upstream 816 ps validation, graph audit 548178937)
The failing cone was landed RX record -> 493-bit zero test + 31-bit expectation compare + direction -> fault -> rx_valid ->
request_valid -> root accept enable of ~300 flops (ahs33 = ctx10), all in one edge.  Redesign (no squeezing):
* qkd_native_attention_record_rv: the whole RX check (record + time) is evaluated flop -> flop into b_rbad / b_tbad on the edge
  after the landing; the record moves with it (b_pl).  RX zero flags only from the landed copy (no raw-pin predecode).
* Registered admission: request_valid = 10 kept register copies written on the landing edge from the landed check + kind + the
  controller fault of that cycle; service-root accept slices <= 36 flops each (copy AND ready); boot_ok registered.
* Kept copies (<= 32 loads): issue (12 face landing copies of i_ctl[34]), descriptor-valid load (8, registered from the same
  operands), status_slot (17, precomputed from the controller next state; one per 32 TX data bits), calendar S10 strobe (8).
* Result face: 512-bit beat captured unconditionally (validity alone authorizes observation; removes the fin[0] 1038-load
  enable); calendar S1..S9 capture unconditionally (fixed-latency pipeline).  Fault root: every ufk pin lands in its own flop.
* Reset: no RTL relay; kit reset_landing balanced 2-stage (2 first / 48 final kept copies, reset_relay_split max 32 loads).

## Added cycles (priced, handed to lanes/KV-GEN9.md)
+1 edge K.rx_record: every RX observation, and therefore root start_qk/start_pv/ctx/ep/cal (ks_pvst, ks_ahs, ks_pvfst, acal),
the face window, RESULT/STATUS TX slots (tx_first 1750 -> 1751, end 1784 -> 1785: qkd_attn_cal_gen_rv TX_SHIFT 1), prg and arh
move +1 relative to the RX record / run edge.  Reset assert/release: kit landing 2 edges (ba5: async assert, release +3).
fin +1 / i_ctl +1 / K.tx_record +1 / ks_prg +1 / ks_arh +1 unchanged.  Cost: +1 edge per attention admission on the KV->compute
RESULT leg (~32-36 per token on 257,280 = ~0.013%).

## Equivalence (Verilator 5.050, fleet)
tools/qwen_kv_die/attn_rv_1019/rv_pair_bench.sh: whole-tile pair tb_kvs_attn_rv_pair, A = qkd_kvs_attn_fl_ba5, B = this tile;
shared i_ctl / RX stimulus, per-tile TX slots / fin stream / unit faults from each tile's own schedule.  B's ports equal A's one
edge earlier on every edge (valid-masked data): legal (3 commands, ctx 300/2000/77) + 10 fault modes, 155,024 checks PASS.
Mutants 1-7 (fields early, check misaligned, admission without check, TX_SHIFT 0, status copy early, stale face beat, fault root
one pin) FAIL; witnesses results/rtl/kv_attn_rv_1019/m*/verdict.log.

## Safe-design checklist (owner 10-19), pre-gate review by KV-ATTN2
1 Pins: FIXED -- RTL-registered: RX record/event -> codec landing flops (no logic, no enable), TX slot pins -> ls_* flops, uf* ->
  one flop per pin, fin / i_ctl -> ot_pin_land face flops (issue -> 12 kept copies); outputs from flops (OT_KEEP_PIN_REGS +
  pin_reg_split give each pin its own launch flop).  Reset lands in 2 registered stages at the face (kit, balanced copies).
2 Reach: model PASS (216: bounded placement max Manhattan 298.6 um / individual reach 328.2 um < 405); measured by the gate.
3 Fanout: FIXED -- kept copies above; post-synthesis high_fanout census by the gate.
4 Depth: FIXED -- RX check flop->flop (~10-12 levels), admission registered, no combinational in->out path.
5 Storage: PASS -- no runtime-indexed arrays; the 512-b stages (landing, checked record, Q register, prg / TX launch) are distinct
  schedule points of an II=1 stream, not a delay line of one value; no SRAM applicable.
6 Floorplan: no macros (lattice N/A); PIN-LIMITED low util (3,284 pins; N face 1,080 pins); full-core rows, square 1:1.
7 Clock: S-centre clock pin feeding the local spine; TT/FF pin-flop spread measured by --cts (must be <= 80); io_hold_margin 0.03.
8 Schedule: static; +1 K.rx_record priced (above).

## Gate review (--cts --remote auto @15138d8e1, ot-epyc5; PNGs personally viewed 10-19 17:10)
Verdict WARN (0 fail): util 3.2% (pin-limited), util_channel, clock insertion > 300 (guidance).  Synthesis 17,504 cells /
6,463 FF / std 2,791 um2 (native safe_pr 34,576 cells).  Pin geometry PASS 3,284 pins on-track.  Reset balanced landing proof
PASS (root 2 loads, first max 24, final max 30, 2 edges).  Textbook: in->reg 0 levels, reg->out 0, in->out 0, no net > 256,
depth 503.4 ps / 13 levels, reach worst 118.8 um (0 > 500).  CTS: TT/FF pin-flop spread 42.9/40.9 ps (<= 80 PASS),
insertion 503.5/413.9 ps.  TT placement RC: reg->reg worst +61.4 ps (was -569.32 placement-only / -15.15 bs1), reg->out
+293.2 ps, hold +42.3 ps.  Trial GRT overflow 0 (M2 11.33%).
Floorplan PNG: 302.4 square, full-face pin groups (N d2d, E tx/i_ctl, S ck centre + rst/uf/fin, W outputs), vertical M5 PG,
full-core rows.  Density PNG: logic hugs the W output face and the N RX face (landing / launch flops at their pins), sparse
interior (pin-limited), a few local bins ~1.0 in the NW corner, no overflow.
Checklist per item after the gate: 1 PASS (boundary 0/0/0, reset proof); 2 PASS (reach 118.8 um); 3 PASS for registers at
<= 32 flops per kept copy (transparent census: copy families 34-58 terminal pins = enable mux pairs; root start_qk 72 pins,
guard accept enable 71 pins (shared native59 guard), producer fault 57 -- all off the critical paths, worst slack +61.4 ps;
TIEHI 778 SETN split by repair_tie_fanout) -- a tighter <= 16-flop-per-copy successor is gated in parallel (rv3 / rv4);
4 PASS (13 levels / 503 ps); 5 PASS; 6 WAIVED util (pin-limited, reason above), shape/rows PASS; 7 PASS (spread 42.9/40.9);
8 PASS (+1 K.rx_record priced, lanes/KV-GEN9.md).
