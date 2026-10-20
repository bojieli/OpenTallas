# SM release pickup, 2026-10-20

No collected gate is qualified for submission by this packet. The new native
pre-gate rule requires every driver, resets included, to have at most 32 loads.

SM9 south `smh_rp4hs_a_km64` gate WARN: GRT zero, TT/FF child-flop boundary
spread 33.5/28.0 ps. Its old textbook threshold was 256. A fresh strict census
on the immutable mapped netlist fails: BDC `ov` drives 98 loads into G1.
`census32_codex.json` uses the same BUF/INV-collapsed load accounting as the
gate. The old gate WARN is therefore unqualified. North gates remain live.
The sibling south km32 is WARN/GRT0 at 47/37 ps. South b variants fail fill34%,
with clock/GRT clean; this packet grants no density waiver.

PVMD s5a/s5b are WARN/GRT0 at 37.3/35.5 and 23.4/22.9 ps respectively.
The committed prior mapped census already reports 160 adder flop outputs
above32, maximum142. Those were waived because the shared adder is unchanged.
The new rule rejects that waiver; the adder needs an RTL fix before a new gate.
The census is also flop-output-only, so it does not prove all combinational
drivers meet the new bound. No PVMD regate or submit was launched here.

Actual PNGs personally inspected: south a_km64 floorplan and density show one
W-face centre clock entry, seven children, a broad open band above the XS and
continuous side corridors, most soft density at the full N face and row-w/XS
interface. South outline457.92x691.2, aspect1.51, fill35.7%. Macro MX coordinates
have the archived0.024 track snap. Child pin-access/pocket WARNs remain in the
original gate. PVMD s5b density shows continuous N and W/E bands around one
SRAM, with several denser bins in the NE band. These observations grant no
native-PG, pin-budget, routing, or census approval.

## Opt-in G1 source capture

`OT_SMH_G1_CAPTURE` selects a new leaf G1 capture; it is off by default.
A first bank captures BDC/BF16 payloads and eight kept copies of BDC valid.
Each copy selects six output bits at the next edge. This adds one leaf result
edge and does not change row or beat paths. No kit enables it yet: compiler
pricing and gather/pass-through deskew must be completed before adoption.

A 5.050 bench checks4094 cycles including invalid payload junk, simultaneous
producers, faults without valid, and repeated reset reassertion. MUT1 returns
valid one edge early; MUT2 suppresses fault. Both have committed FAIL witnesses.
The initial synthesis omitted the production keep hook and merged copies to
one96-load flop; this failure is preserved. With the production ot_keep_regs
hook all eight copies survive:156 total flops, max driver<=32, stage depth50ps.
The primitive's reset_landing check is scoped out because its rst_n is the
already landed parent r_g; its reset drives four local gates, not an external
tile reset. Full-parent census PASS:7944 flops,7951 clock sinks, reset port1, no driver>32; depth50ps. This is mapped synthesis only, no physical reach proof.

Checklist for candidate (not a layout-gate admission):
1. Pins: primitive registers all producer inputs and result outputs; actual
   parent mapped reset port1 (same original landing tree).
2. Reach: primitive will sit beside the G1 result mux in the BDC/TCT channel;
   integrated <=405um planning/placement check pending.
3. Fanout: primitive kept-hook mapped census <=32 including reset; full-parent
   mapped census PASS7944 flops, no driver>32. No high-fanout waiver.
4. Depth: primitive mapped50ps, two logic levels; parent mapped50ps.
5. Storage: primitive156 flops is a two-edge pipeline, no runtime memory.
6. Floorplan: no new kit; preserve existing child lattice and shared band.
7. Clock: use leaf regional clock, no new root; actual spread not measured.
8. Schedule: +1 leaf result edge known; model price, compiler binding and
   through-lane deskew pending, so no gate or adoption claim.
