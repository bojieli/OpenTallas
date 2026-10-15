# Static S81 VM core + die-name master (claude S81 VM owner r8, 2026-10-14)

Component evidence for real RTL; NOT physical, full-layer or full-token qualification. Owner rules 2026-10-14T18:59
(static cycle schedule, no credits/backpressure) and 19:12 (all on-chip execution real hardware) apply.

RTL (rtl/dsrom_sys/s81_ph/vm/): dsfd_vm_static_rsched (fixed slots, free-running group, release = the request vector
delayed 10 edges: E0 FSR .. E10 release), dsfd_vm_static_wsched (48 write sources, lane = same-bank prefix count,
storage slot = lane, fixed drain of lane c into the scatter at source pin + 4 + c), dsfd_vm_static_landing (static
LARM), ot_s81_vm_x34 (fixed-phase 3:4 serial -> stream), dsfd_vm_static_core (stream composition over the existing
dsfd_vm_static512_suhc: 128 real ot_sram_1r1w_512x128 banks, relays, FSR, return store, native map; engine 12
dsfd_vm_seq_static), dsfd_sp_vm_static.sv = module dsfd_sp_vm (static revision s1, die name).

Fixed latencies (stream edges, die pin sample -> output register): SU/HC/PQ/collective/MIX4 reads 12; engine done 5
edges = DLAT 6 presented cycles; write commit observed on the real bank port K = 11 edges after the source pin
(lane 0; lane c adds c) -- measured constant over every commit of the run.

core/ (tools/s81_vm/static_core_gate.sh, Verilator 5.050, ot-run EPYC4 unit oth-ubuntu-644055-1792043214):
base seeds 1/2: 16384 rows written once + lanes 1/2 + static LARM + 2000 MIX4 writes; 73696 slice commits all at
K = 11 (+lane); 39528 / 39496 native SU/HC reads, ~1000 PQ 4-row reads, ~7900 MIX4 reads (20 lanes, fixed slots),
collective row reads; 51533 rows compared word by word at the exact cycle; engine ARM/CHECK verified (t_inp_su),
4 dones exact; bad 0. Fault witnesses (each raises ITS source): 1 four writes on one bank, 2 drain collision, 3 PQ
misaligned, 4 P2RD in the static ABI, 5 duplicate read bank (FSR), 6 MIX and SU on one logical port.
Mutants FAIL: mlane (bad 21), mdrain (100), mslot (620), mstride (3865), mmix (37).

x34/ (tools/s81_vm/x34_gate.sh): aligned 1380 words exact on every stream edge; stream or serial released one cycle
late -> alignment fault; phase mutant (bank 0 read one edge early) FAIL.

OPEN: f_capture static row assembly, WFC kit static form, t_gather/f_xgo function, qSW/qSWs, die port-bind, CTS /
phi-R / cut / timing of the composition, the compiler emitting these fixed latencies.
