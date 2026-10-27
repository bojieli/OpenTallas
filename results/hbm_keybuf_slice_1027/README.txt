HBM keybuf: eight parallel line slices, 2026-10-27.

The source preserves the original keybuf's sampled-edge behavior. Each of eight
identical slices holds one 1088-bit data line in five real 256x256 SRAMs (only
64 bits of the last macro are consumed). It regenerates the same 10-bit tag from
one declared three-bit quasi-static lane strap. Control validity/epoch checks
are replicated; the composition ORs their identical sticky fault outputs.
No data cycle is added, and the key cadence remains one beat per edge.
Boundary face flops and the die transport are not supplied by this pure cut.

Lockstep vehicle: actual original 34-macro implementation versus the new
40-macro composition, full 8792-bit interface, generated SRAM repair/read model.
Three records cover 171 consecutive live beats, three replay rows per record,
PRE timing/address faults, live/replay collision and reset/clear. The positive
run passed 2088 comparisons with zero mismatches and exercised six fault edges.
A +1 tag mutant is run on the same vehicle. Receipt paths and final result are
recorded in status.json once collected. Use bash run.sh SCRATCH_OUTPUT through
ot-run. The original module and SRAM model under this result directory are
reference sources copied from results/hbm_mu_quad_4/keybuf on QUAD5 e91031b844.

Physical root cause: the original declared 324x324 lot is 104976 um2, but its
34 real SRAM macros already occupy 241292.721024 um2. The previous 115x115
estimate for a five-macro slice is likewise impossible. The selected real SRAM
LEF physical/asap7_memory_macros_v2/...256x256...lef is 172.824x41.064 um.
lot_model.py sizes a 241.92x293.76 analytic slice lot: five macros, 49.93%
macro fill, approximately 30.2-um side channels AFTER 4.32-um macro halos, and
a 30.2-um centre gap containing the snapped M5 clock entry. Eight such lots
cost 0.568531 mm2 per old keybuf (+0.463555 mm2); macro count rises 34->40.
The depicted macro floorplan was viewed: no macro overlaps; side and middle
channels are continuous; the stack leaves a control/face-flop band at the top.
Verdict PASS-COND for analytic capacity ONLY. It is not a build authorization.

Remaining integration is material: QUAD5 planU5e_r has four unpinned keybuf
instances, no corresponding native entry in core_conns.json, and only 256-bit
proxy .kin/.kout station-model links. Those do not bind the actual 8792-bit
interface. Packing the larger lots in remaining white holes puts most several
millimetres from the indexer. That candidate is GEOM FAIL for affinity and is
not adopted. Repack the indexer and key slices as one district, create native
pin mappings, and regenerate clock/reset/PG/transport. Price any transport
cycles before submitting a kit. No physical route, token pass or sign-off is
claimed here.
