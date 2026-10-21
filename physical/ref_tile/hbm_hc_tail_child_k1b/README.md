# hbm_hc_tail_child_k1b -- HC Sinkhorn tail child tile (H.STA.BLK.1), HBM-HC7-TAILK 10-20

Element ot_hbm_hc_tail_child_static (hard child, x2 in ot_hbm_hc_root_static TAILC=1).  PARALLEL FALLBACK of hbm_hc_tail_child_k1.
Outline 440.64 x 293.76 um (aspect 1.50), no macros, synthesis cell area 62,976 um2 ->
util 0.499 of the core.  Pins: {"N": ["launch", "mixes", "bases", "scales"], "S": ["result_v", "result", "fault"], "W": ["clk", "rst_n"]}  (1,633 inputs, 770 outputs; densest face N 1,633 / 440.64 = 3.7 pins/um <= 6).

## Source = gate-level cloned netlist (method of results/rtl/fp32_add_native_clone_1020, ROOT-approved opt-in)
`rtl/hbm_accel/generic/peers/static_hc/native/ot_hbm_hc_tail_child_static_bfc24.v` (sha256 ad143cfc...20b9):
RTL ot_hbm_hc_tail_child_static.sv @22ea15f97 -> per-module ABC map (ASAP7 RVT TT; flat ABC never finished in >1.5 h) ->
tools/hbm_hc/bound_fanout_clone.py --limit 24 (6,734 clones, every clone same primitive + same input functions, ledger
results/rtl/hbm_hc_root_safe_1020/tail_child_hc7/native_childh2.v.ledger.json) -> retained re-synth -> compact_netlist.py
(text-only: one-line instances, packed wires, sink-clock net renamed sclk).  ORFS synthesis reads library cells only (ABC has
no generic logic left), so the gate's own synthesis is fast and its mandatory native census sees the cloned graph.
Equivalence: tb_hbm_hc_tail_child_eq lockstep of THIS netlist (cells.v of tools/prepare_fp32_fan32_models.py) vs the released
tail unit (bench tailc_native_lockstep); RTL m0 PASS 48, MUT1 FAIL 44/48 (Verilator 5.050).

## SAFE-DESIGN CHECKLIST (owner 10-19) + PRE-GATE NATIVE CHECK
1 Pins: PASS -- RTL pin flop + 2nd stage on every data input, output pin flops (pin_regs opted out with reason: they ARE the
  RTL's); io_flop_at_pins anchors them; rst_n reset_landing 2 stages, then ot_rst_relay 3 regions + kept leaf stage per region.
2 Reach: PASS by plan -- side <= 440.64 um; pin->core and core->pin hops registered (2nd stage); post-GRT 405 um check
  by the gate.
3 Fanout: PASS -- native32 census of the cloned netlist max 24 loads, 0 violations, 616,857 roots (uncloned map: FAIL 2,483
  drivers > 32, max 1,797); clones are real cells (not buffers), Yosys cannot merge them (library instances).
4 Depth: PASS -- arithmetic is the released LAT fp32 add/mul, fdiv, Sinkhorn units; operand selects are registered one-hot
  (ot_hgi_hc_tail_os_static); no combinational in->out path (pin flops both sides).
5 Storage: PASS -- no runtime-indexed flop array > 2 kb; the 5-bit index delay lines (D 3/3/49/19) became age-decoded write-backs.
6 Floorplan: PASS -- no macros, util 0.50 from synthesis area (40-60%), aspect <= 2:1, one full std-cell band, pins on
  full faces <= 6/um.
7 Clock: one core root on clk (the register mass is the whole core; no macros) + generated /7 sink clock sclk
  (physical/hbm_hc_tail_child/tailc_sclk.sdc: create_generated_clock -edges {1 3 15} on iv4540_c/Y, 3,088 sinks; every
  clk<->sclk arc a single-period synchronous check).  Pin-flop spread <= 80 ps TT+FF judged by the --cts gate;
  route.hold_margin_ns 0.03.
8 Schedule: static -- child result_v = unit + 2 edges (pin stages), handed to the root (TAILC=1, HC_MIX +2); reset landing
  adds 2 cycles of reset latency only (scheduled constant).
