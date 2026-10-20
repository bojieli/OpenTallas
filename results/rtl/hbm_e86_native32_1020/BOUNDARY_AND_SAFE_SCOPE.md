# e86 FAN32 enabled-capture and source-safety scope

Source 4aa724d4e, opt-in FAN32=1/PRE=1/CREP=1; default FAN32=0.
No extra pipeline edge, no inherited physical qualification.

## up_in first capture

Each bit up_in[86*s+b], s0..3,b0..85, has first sequential destination
X[60+s][b]. Clock is ckr[rg((60+s)/8)] = ckr[3] = clk_r3. There
is no arithmetic or comparator ahead of that capture. Its data expression is
(m[1]&up_in_bit)|(m[2]&ins_bit)|(m[3]&old_X_bit). With FAN32 each
m is a kept20-bit-slice-local one-hot register on the SAME clk_r3 edge as X.
m[1] is shift/convey enable, m[2] insertion, m[3] feedback hold; all zero clears.
This bounded enabled boundary capture is permitted by root01:31 clarification.
It does not require adding an artificial landing edge.

The preceding dsel_position decode is registered by m, then consumed by X at
the next edge; dsel_position originates in distinct kept pc copies on clk.
This preserves existing PRE1/CREP1 control age. It does not prove clock-root
insertion phase: actual related-clock constraints, face setup/hold, regional
crossings and source schedule must still be checked. The direct lockstep bench
compares every output on every simulated common edge and exercises convey,
insert, clear and idle; it is not a physical phase proof.

up_out/ovf_b are explicit registered outputs in their assigned regional roots;
busy/tau_o are registered on clk. up_in does not directly feed any output port.
Other raw pin data/control enter explicit pin-stage registers; FAN32 copies
preserve source edges. Exact mapped first-capture graph for the final passing
revision, its combinational depth, and reach remain pending. V1 mapped graph
cannot establish V2 qualification.

## Eight-item checklist before any layout gate

1. Pins: source enabled-capture roles identified above. Exact full mapped pin
   census still pending, including all raw controls and clear/initialization.
   clr is synchronous functional clear, not an asynchronous reset port. Do not
   claim two-stage reset_landing merely from PRE pipeline naming; a complete
   clear-age/initialization protocol and any true reset contract must be pinned.
2. Reach: OPEN. Old physical outline/regions not adopted; need new area-based
   full-cell regional ownership and every single-cycle path <=405um plan.
3. Fanout: V1 FAIL28 dynamic drivers/max53 (all preserved). V2b synth and exact
   all-driver/reset native census pending. No physical gate before zero >32.
4. Depth: OPEN. up_in uses only enabled mux. Insertion still includes85-bit
   comparator, count/selection and OR logic; actual max depth/timing, including
   runtime tau_o selection, must fit the unchanged clock target and uncertainty.
5. Storage: OPEN source-role review. Sorted X state64x86bits and continuously
   accessed compare/control state are distributed pipeline/algorithmic state;
   tau_o also has runtime-indexed X selection. The generic >2kb runtime-array
   rule must be explicitly reconciled with this parallel comparator/shift
   structure before claiming PASS. No SRAM waiver or legacy CLOSED transfer.
6. Floorplan: OPEN until exact fresh synthesis cell area,40-60% std-cell band,
   four related regions, face capacity and complete source-cut model are priced.
   No new macros/ports; no lattice exemption.
7. Clock: OPEN actual clk+four regional roots, reference constraints,
   <=80ps TT/FF spread, io_hold_margin>=0.03 and source-control phase contract.
8. Schedule: source intent adds0edges and0memoryports. Final RTL lockstep,
   causal mutants and actual enable/capture ages must pass before zero-delta
   schedule is accepted; actual physical phase or relay additions must be priced.

Any criterion still OPEN blocks gate. Native32 PASS alone is not approval.
