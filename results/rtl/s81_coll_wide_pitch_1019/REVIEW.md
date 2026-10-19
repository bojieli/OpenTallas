# S81 COLL wider-pitch native SRAM model

MODEL ONLY. ROOT selected the native wider-pitch compiler direction; this is
its bounded pre-build review packet. No new macro views, RTL, gate, placement,
CTS, route or adoption. Existing families and calibration remain untouched.
Source client model eb8141cf8 is authoritative for producer and collision
ownership, with all 37 nonreset and 2 reset fanout failures still open.

The distinct proposed master is
`ot_sram_1r1w_512x128_m4_r2c2_p192_rc2`. The finite model script emits only
`model.json`. That file hashes exact original aligned-v2 LEF, functional V,
blackbox, JSON and TT/FF/SS libraries, exact bb61ae67c credit family, and exact
e26d92503 dual-clock gearbox family. Compiler, behavior, bitcell, technology
and frozen Liberty calibration sources are separately hashed. No calibration
rerun or undocumented numerical fit is proposed.

The unchanged core is 173.948 x 29.5631632605793 um, 128 main physical rows plus
2 spare rows, 520 physical columns (128 data plus 2 spare IO, mux4). Keep its
512 logical words x 128 bits, 9-bit address, 7-bit row repair addresses, 7-bit
IO repair selectors, both spare rows and both spare columns. Preserve all437
signal/clock contacts and VDD/VSS. No new ECC or loss of existing repair/fault
semantics. A single `clk` captures read and write; read is registered and holds
when disabled. The exact source explicitly reads BEFORE writing: same-address
same-edge returns OLD data. The new macro must preserve that contract, masked
writes, repair mappings and fault injection. The dual-clock gearbox macro is
different: same-address simultaneous access is excluded and must be suppressed
by its actual current/previous forwarding. Do not transplant OLD semantics to
that primitive or rely on dual-clock simulator ordering.

The proposed native terminal pitch is 0.192um (four real M4 tracks). Compiler
outline retains 0.768um end keepouts then site/row/track snapping. Result:
174.120 x 43.752 um, 7618.09824 um2. H/W are24mod48nm so original24nm contacts
stay on 12mod48 track centers in R0/MX/MY/R180 at43.2-lattice origins; drop R90.
219W/218E contacts give5.0055/4.9826 per full um. Usable face42.216um exceeds
219/6=36.5um. First/last centers are0.780/42.636W and0.780/42.444E um. Original
W/E active span is not reused. Ten payload macros pay76180.9824um2 versus
51776.3232um2, an increase24404.6592um2 before channels, control, clock or PG.

This is an analytical pin-access architecture, not a superficial LEF resize:
the prospective generator must regenerate complete LEF, all TT/FF/SS NLDM,
behavior and blackbox from the unchanged compiler core plus explicit lead
geometry. Signal terminal area, PG, obstruction and orientation inventories
must be independently reconstructed from generated views before use. The
access region has no new storage/compute; core array dimensions remain fixed.
Conservative longest added access lead is H-coreH=14.1888367394um, assuming
core anchored against one edge. This is an analytical upper bound for the
extra vertical jog, not measured extracted internal interconnect. Existing
core horizontal wiring is already priced by the compiler model.

For each corner, M4 R=0.0180365kohm/um, C=0.178475fF/um gives added capacitance
2.5323526371fF per terminal and delay d=0.38*r*c*L^2 +
max(calibrated INV4 R, output R)*C. We deliberately charge BOTH independently
adverse clock and data leads: CQ/setup/hold/minperiod add2d, output intrinsic
slew addsd, minimum pulse adds2d. This is more conservative than bb61ae67c's
one-lead CQ/setup and unchanged hold rule. TT/FF d=2.5571/1.8530ps; proposed
CQ420.3095/349.7497ps, setup33.3703/28.4008ps, hold26.7144/23.3783ps,
minperiod386.0000/321.7392ps. SS remains reported sensitivity, CQ531.7402ps;
acceptance remains TT setup and FF hold. No scalar analytical number proves
parent timing, clock insertion or native closure. Native FF capture/TT launch,
clock waveform and actual IO-load tables must be rechecked on generated views.

Every nonclock contact is charged one full-swing access capacitance for read
and write energy; this intentionally upper-bounds activity, including repair
and unused inputs. Clock terminal adds the same capacitance; no energy saving
is claimed. Ten payload clock pins contribute TT118.781526fF before any CTS;
original ten pins were93.458fF. The existing five credit pins and twenty gearbox
clock contacts stay separately sourced; no clock contacts disappear because
the two gearbox clocks tie to one source. Input-slew-dependent internal lead
behavior and leakage change with the paid outline are explicit model assumptions.

## Escape and physical proof plan

Keep all PG straps and M1/M2/M3/M4 body OBS regenerated from actual dimensions;
never delete OBS to manufacture access. Preserve source PG terminal widths and
pitches and check every new stripe through R180. Real M4 tracks are48nm pitch,
centers12mod48. M3/M5 track coordinates, via enclosures, min area and PG keepouts
must come from the pinned ASAP7 technology, not a synthetic routing grid. A
43.2-lattice origin preserves48nm phase; rotated parents still need exact
orientation checks. Candidate channel budget is at least10.8um on each signal
face, with a separate actual PG-via obstruction census. This is an allocation,
not evidence of escape capacity. A24x24nm signal terminal has576nm2 and is NOT
itself a2000nm2 wire patch. Connected same-net M4 extension of total96nm length
would provide2304nm2; actual legal width, spacing, via enclosure and adjacent
PG must be checked on native technology and final routed metal. No min-area
PASS is inferred merely from that arithmetic.

Bounded next physical experiment is one real wide primitive with all437 signal
contacts and its complete PG mesh, then opposed real faces with parent buses.
It must audit every contact, same-net connected union, other-net intersection,
all transformed OBS, real M3/M4/M5 crossings and final DRC/PG connectivity.
Primitive or array access remains NULL. The earlier32x64 coupon is evidence
only for its exact primitive, not for this family or these25 macros. Do not
invent a fabricated-GDS requirement for the research analytical artifact.

## Complete storage and client consequences

Model inventory: ten native payload macros; five exact calibrated
32x128_p192_rc credit macros (51.408x39.960,2054.26368um2 each); ten exact dual-
clock32x64 gearbox macros (31.992x17.304,553.589568um2 each). Total25 macros,
35 clock contacts and91988.19648um2, with696320 logical physical capacity bits
versus573076 useful client bits. Including native payload repair rows/columns,
total actual cell capacity is716960 bits. Payload useful566272=2*553*512;
credit4424=553*8; gearbox2380=595*4. Unused data tails/rows and repair cells are
paid; spare cells are not useful application capacity. Credit capacity includes
all32 rows although only8 are logically reachable. Gearbox needs ten64-bit
banks: nine lose19 real frame bits; bank9 has19 useful and45 unused columns.

No external edge change is proposed by the macro alone. 833ps does not violate
the analytical macro period, but this says nothing about actual parent
launch/capture, lead load, hold repair, clock slew or full-cycle read timing.
Current COLL source needs separate actual595-bit gearbox proof, ready-cone
repair, finite producer-copy graph and exact reset ownership. Registered bank
address/enable/forwarding must retain their existing edges or price changes.
The proposed payload height43.752 exceeds one43.2 pitch: successive vertical
origins must be at least86.4 apart; local geometry cannot overlap at43.2 steps.
Horizontal174.12 width needs at least216 spacing plus actual face channels.
A single band center cannot serve every bank within405um without a real full
pin-to-producer reach model. Parent fit remains NULL; even old561.6 COLL plus
475.2 endpoint and43.2 channel required1080um versus950um reservation. This
larger family cannot inherit that old stand-in slot. Full row utilization,
clock position, channel tracks, PG and complete parent repack remain open.

Before generation: ROOT reviews electrical assumptions (including conservative
2-lead hold/pulse), actual plan and source provenance. Then isolated distinct
family generation plus function/repair/masked-write/OLD collision/disabled-read
miter and causal wrong-address/mask/read-age/repair mutants on fleet. Existing
views remain byte-identical. Only after these pass should native access and
client array work begin; no full COLL RTL change, gate or adoption is requested.
