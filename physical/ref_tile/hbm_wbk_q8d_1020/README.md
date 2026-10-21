# hbm_wbk_q8d_1020 -- d4g wbk_<q> x4 (ot_hbm_svc_wb_kport_q), HBM-WBK8 census-safe successor (RELEASE_TREE H.STA.BLK.5)

Variant b (fallback, gated in parallel): every K bus spans the full N face (pin_ranges) as q2b.

Why: q2 (hbm_wbk_q2_1020, kq2 core) failed the mandatory pre-gate native census (CODEX-HBM preflight e8d69c19d:
2,219 drivers > 32, max 232) and its SRAM rows sat at a 41.04 um pitch, off the 43.2 lattice. Census analysis by Yosys
src attributes (HBM-WBK8 /tmp/wbk8/analyze.py, fleet ep5): the hbm-side combinational pop of a PC drove nine 32-b
crossing FIFOs plus nine skid slices (212..232); each 32-b reviewed ot_link_afifo (AW3, RCOPY4) had read-pointer copies on
65 mux loads and entry enables on 56; w_k_rdy drove 39..49; bank selects fanned out to 30-b muxes (~1.75 loads per
enabled bit on ASAP7, every enabled flop maps to an AO/OAI mux).

Design (rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_kq8.sv, kport_q FAW=2 PP=1):
- each PC's 285-b beat crosses in 20 slices of <= 15 b (18 data + 2 ordinal), each through TWO reviewed ot_link_afifo
  (W <= 15, AW 2, RCOPY 3) written / read alternately (ping-pong): 8 entries per PC, as q2 (FAW 3);
- hbm side pops all 20 slices in lockstep from kept REGISTERED pop copies (one per slice), decided one edge ahead from
  the FIFO empty flags (arrivals only add words); K pins come out of a 3-entry one-hot ring per slice; w_k_v is a flop,
  w_k_rdy drives one AND per slice;
- stream side: per-PC credit over the slice-0 pair with registered exact ok copies; one-hot lane select per (PC, data
  slice) in kept arrays; address from a registered grant copy; meta/ack tokens in split <= 7-b reviewed FIFOs;
- every wide select / write enable is a kept copy serving <= 16 b (fill bank x9, fill start x8, copy bank x7, done bank x3,
  window/receipt selects); copy start through a two-level kept relay; 3-level kept reset relays (<= 16 / leaf <= 32).

Census (actual mapped ASAP7 netlist, tools/ref_tile/native_census.py from origin/main, same Yosys image/flow as e8d69c19d):
q2 baseline 2,219 / max 232 (reproduced) -> kq8 c1 1,104/61 -> c2 4/35 -> c3 1/33 -> ... -> c8 PASS 0 violations / max 32
(fleet ep5 /srv/opentallas-scratch/claude/hbm-wbk8-1020/c8, 411,831 mapped cells, kq8 sha 832fe2a9).
Std-cell area (pre-buffer, c3): 54.2k um2 (q2 41.2k), 92.3k flops.

Benches (Verilator 5.050, fleet run b7 on the c8 RTL; results/rtl/hbm_wbk8_1020/): wbq_e / wbq_w / wbq_e_wopen PASS (8 blocks, 5,563 sectors,
lockstep vs the GEN0 master), PP=0 variants PASS; 9 mutants rejected (quad, span, premature, ksaddr, slice, commit,
credit, pp = stuck ping-pong read toggle, lock = pop ignores the K ring room).
Price: serial single-block fences = q2 for blocks 0..4 (142/57/75/287/1760 vs 142/57/72/289/1765); blocks 5..7 2596/403/
1073 vs 892/128/59 (VM-window phase interplay: the PP=0 build gives 877/142/60); with group traffic (wbq_e) the sum of the
8 fences is 26,333 vs q2 32,358 (-19%). Added edges: copy start +1 stream, pop decision +1 hbm, block enable +1 hbm.

## SAFE-DESIGN checklist (owner 10-19)
1. Pins: PASS. RTL registers every pin (stream pin flops + kept copies; outputs from flops; w_k_v a flop, K data from the
   ring registers through a 3-way AND-OR); each reset lands in 2 stages on its own clock (kit reset_landing opt-out).
2. Reach: crossbar relay xr between SRAM columns and PC FIFOs (as q2); measured by the gate.
3. Fanout: PASS by mapped census (see above); kept copies listed above.
4. Depth: no storage-dependent select; registered pop decision; no combinational in -> out except the K ring head mux.
5. Storage: payload in 32 SRAM macros; crossing FIFOs are reviewed flop FIFOs (4 x <= 15 b each, < 2 kb), WAIVED as q2
   (no admissible dual-clock macro for this shape).
6. Floorplan: FIXED (COL-WBK 10-21) -- FALLBACK: pins as q8b (every K bus spans the full N face); each SRAM column = TWO 4-high abutted stacks (pitch 41.088 at_exact, 0 off-track; bases y = 43.2 / 259.2 on the 43.2 lattice) with a 51.8 um E-W cell channel between them for crossbar xr traffic; W/E halo 10.8 um. (78 um column
   pitch channels for the 10 pins/um side faces of the macro -- macro pin density is fixed by the view, WAIVED). Outline
   777.6 x 518.4 is pin-bound (N face 4,626 K pins at 5.95/um), so utilisation is low (~20-30%), WAIVED (pin-bound).
7. Clock: regional roots per family; crossings only through reviewed FIFOs, ot_reset_sync and 2 level synchronisers;
   io_hold_margin 0.03; gate --cts checks pin-flop spread <= 80 TT+FF.
8. Schedule: static on the DMA side; K-side ready/credit only at the HBM boundary; added edges priced above.

## COL-WBK 10-21 successor (q8d)
Why: q8/q8b gate4 (3723c412f) local FAIL 28 x channel: the 43.2 re-pitch left 2.16 um gaps between the 41.04-um-tall
SRAMs of each column (4 columns x 7 pairs = 28), neither a >= 20 um channel nor an abutted stack. Fix: FALLBACK: pins as q8b (every K bus spans the full N face); each SRAM column = TWO 4-high abutted stacks (pitch 41.088 at_exact, 0 off-track; bases y = 43.2 / 259.2 on the 43.2 lattice) with a 51.8 um E-W cell channel between them for crossbar xr traffic; W/E halo 10.8 um.
RTL, ports, cycles, benches and census unchanged (kq8 @385c5755b; Verilator 5.050 b9 witnesses in results/rtl/hbm_wbk8_1020).
Local floorplan_checks: 0 FAIL (clock_span WARN only).
