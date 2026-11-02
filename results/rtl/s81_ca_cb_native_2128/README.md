The native ca/cb residual is a cross-stream slot constraint, not a split of one
packet's data and valid bits. Actual selected LEP g_irx emits independent276-bit
packets: pairB→ca (lane2), pairA→cb (lane3), with the same two-edge source
pipeline. The actual selected bk_sel consumer is dsdv_idx_vmux6(V276,MUT0),
which merges six valid-masked packets and flags simultaneous valid inputs.

All three original selected source files match the actual bind_ev2 readset:
portfix178 ot_s81sl_slice_lep.sv, dsdv_idx_l20s.sv and dsdv_idx_tree.sv.
The test extracts the unchanged RX demux/idx_sel and vmux6/vm_bit mechanisms.
Synthetic type5 frames carry valid lane2/3 payloads through the actual demux;
tm is idle. This is a steady-state source/consumer diagnostic with counted
native lane depths, not a full RX FIFO, PHY, clock-landing or routed path test.
It does not qualify boot/warm-reset clock availability or a production mission.

Intel1 unit oth-ubuntu-3941088-1793595894, normal ot-run4GB/2CPU, exit0:

| case | source release gap | ca/cb counted depths | fault | outputs |
|---|---:|---|---:|---:|
| independent packets | 2 | 59/58 | 0 | 2 exact |
| adjacent independent packets | 1 | 59/58 | 1 | 1 merged |
| equal-depth reference | 1 | 59/59 | 0 | 2 exact |
| wrong-date control, B one edge early | intended2→1 | 59/58 | 1 | 1 merged |

All four cases met their expected result with zero checker errors. Packet
identity, valid, output counts and sticky collision fault are checked. The
consumer-only predecessor is retained separately as a scoped diagnostic.
Current relative arrival gap is source gap−1. Consecutive source pairB thenA
releases can therefore meet at vmux6; blindly waiving59/58 or padding every
native group would both be unjustified. Actual production issuer/release dates
still need a witness before declaring a released mission failure or success.

Read-only plan localization: both lanes traverse the same nine FT partitions,
with two boundary and15 clock-landing edges. Their first eight FT station
counts match. The only difference is s_4N_x06 / slice_station__t48:
ca uses ft0=7, cb uses ft1=6. A possible scoped fix is ft1 6→7, adding one
whole276-bit+epoch station and one CB cycle. This is UNAPPLIED and needs the
die owner's batched plan/clock-count impact, GEN/LOOK, re-kit and model price.
No plan, RTL, clock, source default or active kit was changed here.

The other99 within-lane metadata relations and13 replica relations remain
unqualified; this single witness does not transfer to them.
