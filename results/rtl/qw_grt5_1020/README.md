# QW-GRT5 10-20 -- Q.BIND.1 die fault-OR tree (source work for the next GEN)

Planning + leaf RTL only. Nothing here is bound into dv2f20g4g/g4h (those GENs are the Q.GRT reach proof).
physical_qualification_eligible = false until the next GEN emits the tree and it passes census, GRT and STA.

## Inputs
- `fault_inventory_g4g.json`: tools/qwen_split/fault_inventory.py (Codex 2a2067647) re-run on the dv2f20g4g GEN
  (source b9bf998e4, strict bind PASS 227 masters / 13,754 instances): 100 master ports, 425 instance ports,
  498 bits, 64 clock roots, 0 unresolved clock/reset, 0 unclassified.
- dv2f20g4g `out/case/place.tcl`, `elements.lef`, `phy_ew.lef`.

## Hardware: `rtl/qwen_split/qfd_fault_or.sv`
Sticky registered OR, N <= 16. Inputs registered at the face, 2-stage reset landing from the regional leaf, 3 ck edges
f -> o, one clock (crossings are made by landings outside the node). Bench `bench/tb_qfd_fault_or.sv`:
Verilator 5.050 PASS (cases 17), iverilog PASS; mutant `QFD_FAULT_OR_MUT_NOSTICKY` FAIL 784 errors (witness
`bench/logs/mut_nosticky.log`). Fail regex: `TB_QFD_FAULT_OR FAIL`.

## Plan: `tools/qwen_split/fault_or_plan.py` -> `fault_or_plan_g4g.json`
Leaves of <= 14 source bits (2 inputs kept for children) with every source pin <= 405 um from the leaf; one tree over
all nodes built by Prim from the sink (sys_face, n_clk_d2d); a clock change costs 5000 um-equivalent so regions merge
locally first; every cross-clock edge is a landed 1-bit lane (qfd_landh0_1, D4) whose own fault feeds the receiver.

| item | dv2f20g4g |
|---|---|
| bits / leaves / nodes | 498 / 253 / 254 |
| landed crossings | 85 |
| relay hops (<= 405 um each) | 450 |
| max source -> leaf | 403.1 um |
| max node fanin | 16 |
| tree depth / worst latency | 66 / 432 ck edges (observation only; never on the schedule) |
| errors | 0 |

## Safe-design checklist (tree as planned)
1 pins: PASS (node inputs/outputs registered; reset 2-stage landed). 2 reach: PASS (every hop <= 405 um, relays
counted). 3 fanout: PASS (rl[1] <= 18 loads; every tree net fanout 1). 4 depth: PASS (16-input OR + OR2). 5 storage:
PASS (<= 20 flops/node). 6 floorplan: owed to the GEN binder (node 65x30-class glue). 7 clock: PASS (one clock per
node, landed crossings). 8 schedule: PASS (static; STATUS observation latency bound 432 edges handed to the compiler).

## Findings that block emission (owed, next GEN)
- Pins do not exist for 455 of 498 source bits: GEN abstracts only emit pins of connected ports.
  * 383 bits = GEN landing glue `fault` outputs: the GEN binder must emit the pin when it wires the tree (no view change).
  * 70 bits = closed view `qfd_collective_static_io_production` (fault_code 5, transport_cdc_fault 20,
    transport_abort 5, ...): its physical view has no such pins. Either re-pin/re-close the collective view, or OR them
    inside the collective into its existing `fault` pin (RTL change + re-close). Decision for the collective owner.
  * 1 bit each on closed `qfd_sys_face_mu_dhobs` and `qfd_mu_ctx_rx_die`: same choice.
- Sink port: `qfd_sys_face` has no tree input. Owed `obs_fault` input ORed into tt_fab / result_cause face class
  (sys_face owner; the sys_face re-close for MU is already pending, add it there).
- Leaves on absent pins are planned at the instance centre (placeholder); re-run the planner on the GEN that emits pins.
