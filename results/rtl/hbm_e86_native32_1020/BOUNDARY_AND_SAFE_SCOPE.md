# e86 FAN32 enabled-capture and source-safety scope

Source 4aa724d4e, opt-in FAN32=1/PRE=1/CREP=1; default FAN32=0.
Mapped top is ot_hgi_coll_tkm_tile_e86, not the generic diagnostic probe tile.
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
   all active mapped selectors, must fit the unchanged clock target and uncertainty.
5. Storage: OPEN source-role review. Sorted X state64x86bits and continuously
   accessed compare/control state are distributed parallel comparator/shift
   algorithmic state. The actual e86 wrapper ties tau controls to zero and
   leaves tau_o unconnected, so generic runtime-indexed tau selection is pruned
   from the synthesis top (verify mapped graph). There is no random-indexed
   read/write array in this top. Reconcile the storage rule against the actual
   parallel algorithmic role, not the generic diagnostic probe. No SRAM waiver
   or legacy CLOSED transfer is claimed.
6. Floorplan: OPEN until exact fresh synthesis cell area,40-60% std-cell band,
   four related regions, face capacity and complete source-cut model are priced.
   No new macros/ports; no lattice exemption.
7. Clock: OPEN actual clk+four regional roots, reference constraints,
   <=80ps TT/FF spread, io_hold_margin>=0.03 and source-control phase contract.
8. Schedule: source intent adds0edges and0memoryports. Final RTL lockstep,
   causal mutants and actual enable/capture ages must pass before zero-delta
   schedule is accepted; actual physical phase or relay additions must be priced.

Any criterion still OPEN blocks gate. Native32 PASS alone is not approval.

## Exact parent clear and first-use source trace

ot_hgi_coll_tkm_static.sv has synchronous functional clr = busy &&
(tick==1 || tick==clear2). Each clear is ONE parent tick; production does not
hold it for four edges. The standalone bench holds its initial clear four
edges, then also exercises random single-cycle clear reassertions while active.
Those are separate scopes and must not be conflated.

Initial issue1 is tick>=9, and entry_v is itself registered before dv[0]. Thus
source calendar leaves at least ticks2..8 idle between tick1 clear and issue1.
The second read2=clear2+5; actual buffer read/entry registers add more latency
before tile input. Both waveforms must be traced, including every regional
root, to certify actual clear capture and first usable input. No changed
schedule or >=4-held-clear production assumption is introduced here.

All five roots of each parent tile instance are wired tile_clk[t] in RTL. This
is an RTL common-source relation, not proof of physical insertion phase. The
regional related-clock and actual boundary-age audit remains open. The parent
instantiation does NOT set FAN32; default0 remains. Standalone synthesis sets
FAN32=1 via exact Tcl dict, candidate only, no production bind.
