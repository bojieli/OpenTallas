# qfd_dv_stream_t_1019 -- Q-DV slice stream face as a safe hard tile (Q.SAFE.STREAM)

Owner QW-CLUSTER3/STREAM (LEAD2-QW) 10-19, branch claude/qw-cluster3-stream-1019. Spec generator
tools/ref_tile/specs_qw_stream_1019/mk_specs.py (this kit + the parallel fallback outline qfd_dv_stream_t_fb_1019).

Top `qfd_dv_stream_tile` (rtl/qwen_dv/qfd_dv_stream_tile.sv): the slice stream face of qfd_dv_slice2 `u_stm`
(qfd_dv_stream), with the static x-packer equations of qfd_dv_stream_packer STATIC_PACKER=1 (9587da800: 64 independent
BF16 slots, highest-lane priority, duplicate fault). Ports are qfd_dv_stream's, split only for the pin plan:
sw_i = {sw_v, sw_hi, sw_lo}, se_i likewise, tw_data = {tw_data_hi, tw_data_lo}, xt_d = {xt_d_hi, xt_d_lo}.

## What changed against the open item (cfg/SU source, physical parent)
The 1195cd50b native consumer left 146 header copies, cfg 2, SU write-enable 25 / address 6 and reset 95 copies for the
parent to supply. Here the tile owns them: every input is registered at its face and every wide select is a kept
(* keep *) copy per 32-bit group decoded from the pins at that same edge (relay valid pe/pw x34, table-tap hit te/tw
x33, x-tap hit xe/xw x33, write-any x36, config enable x5, direction x34 per side, emit x36, open-beat x4). The parent
supplies ONE port per bit; no repeated ties, no predecessor copies.

## Static schedule (priced; no credits, no backpressure)
| path | edges vs qfd_dv_stream | note |
|---|---|---|
| sw_i / se_i / sid -> relay so_e / so_w | +1 | the face register replaces the slice's sw_q / se_q capture: net 0 per slice hop when bound |
| xw_* (SU own x writes), cfg_* (STREAM command) | +1 | SU issues writes / the STREAM cfg one edge earlier; II unchanged (8 elements per edge, full beat per 8 edges) |
| table tap tw_*, x tap xt_* | +1 (+ the face edge) | interior tap relay; table writes are load-time; x tap -> column heads +1 edge per x beat |
| reset assert / release | +2 | kit landing, 2 registered stages, scheduled constant |
Relay throughput unchanged: one 1,088-bit word per edge per direction plus own insertion. Exactness is source-level:
the bench compares every output bit on every edge against qfd_dv_stream with inputs delayed one edge and taps one more.

## Benches (Verilator 5.050 on the fleet, ot-epyc5; witnesses results/rtl/qw_stream_tile_1019/bench/)
`bash rtl/test/qwen_dv/static_stream/run_tile.sh <out> <MUT>`: 10,000 edges, two resets, two SIDs, random kinds and
destinations (own SID / broadcast / other), both relay directions, config changes, full 8-lane packs, random lane subsets,
duplicate addresses, abandoned beats, late undefined kinds; per-edge fault cause (bad / pbad) compared as well.
m0 PASS (946 emitted beats, 2,511 table taps, 1,993 x taps, 4,298 relay edges, 3,691 fault-cause edges).
Mutants FAIL: m2 RNE->truncate (xt c39), m21 no lane priority (xt c260), m22 no duplicate fault (bad c204), m31 relay
group 17 on the E valid copy (so_e c33), m32 tap group 5 without SID match (tw c55), m33 emit copy 9 stuck 0 (so_w c2823),
m34 write-any copy 3 stuck 0 (xt c39).

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | pin regs + reset landing | PASS: every input is captured in an RTL face register and every output is a register (flow pin_regs opted out with that reason: a second stage would add an edge and fold the kept select copies). Reset: kit reset_landing 2 stages, last stage 16 kept copies (reset_relay_split max 32); reset only on control state (~470 flops), payload registers carry none |
| 2 | reach <= 405 um | PASS by plan: W/E pins bit-aligned (sw_lo/sw_hi bottom half W, so_e bottom half E; se top half E, so_w top half W), so the relay is a 302 um horizontal hop; the tap mux is an interior relay (each hop <= ~345 um to the N/S tap faces); valid pins mid-segment (copies <= ~400 um to every group). CHECK at the gate placement |
| 3 | fanout <= 32 | PASS by construction: every register-driven select drives <= 32 loads (copies above); combinational nets (complete = &nm, BF16 lane data -> 64 slots) are buffered by repair_design. CHECK kept copies survive (gate textbook high_fanout_top) |
| 4 | depth | unchanged packer equations (static decode, balanced OR); face decode is <= 4 levels pin -> flop; no combinational in -> out |
| 5 | storage | PASS: 1,024-bit assembly + 1,024-bit completed word + 64-bit mask, written per 32-bit group, no runtime-indexed array > 2 kb, no delay line >= 3 deep |
| 6 | floorplan | WAIVED pin-bound: 6,946 pins (W/E 2,176 each, S 1,482, N 1,113) need >= 371 um W/E at <= 6/um; 302.4 x 380.16 (aspect 1.26), W/E 5.85 / S 5.0 / N 3.8 pins/um, no macros, one full std-cell band. Fallback kit 345.6 x 440.64 (5.0 pins/um) gated in parallel |
| 7 | clock | single ck, TritonCTS leaf tile, ck pin centre of S; gate rule pin-flop spread <= 80 ps TT+FF; io_hold_margin 0.03 |
| 8 | schedule | static, no backpressure; every added edge in the table above |
