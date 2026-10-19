# P3 alignment SRAM sizing before build

The production pad carries 818 bits every clock for exactly three register edges.
Logical storage is 2,454 bits, exceeding the 2 kb flop-storage limit. Four existing
128x256 1R1W macros supply 1,024 bits/edge and 131,072 installed bits, with 15,566.31
um2 macro area. The final bank uses 50 bits; unused high bits write zero. The
addressed three-residue ring reads phase+1 and writes phase. Synchronous read
latency is included, so the alignment remains three edges and II remains one.
Reset restarts the phase; output becomes valid after three active edges, covered
by the existing delayed child reset. No numerical arithmetic changes.

This component is opt-in pending its exact gate. It requires physical placement
of four macros, registered boundary timing and a parent lockstep run before
production binding; component simulation alone does not close the parent.

Component bench on Verilator5.050: baseline984 checks/0 errors; MUT1
(wrong read residue) fails984/984. Witnesses mut0.log and mut1.log. The
P3 parent opt-in generator has been updated and its unchanged3-edge lockstep
is running on the fleet. Proposed outline630.72x2289.6um (leaf0 lifted86.4um)
places four macros at(43.2+129.6*b,1296), all on43.2um lattice. The
existing34 hardchildren plus SRAMs pass geometry/10.8um halo checks.
Macroarea706131um2 gives48.9% hardfill. This is a candidate footprint;
no parent gate or production binding has passed. The legacy landed
bin_l crossing itself still holds8276bits of flopbank storage; the safe
SRAM conversion of that dual-root crossing remains open.
