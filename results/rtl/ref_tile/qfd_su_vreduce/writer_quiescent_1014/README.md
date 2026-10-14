# Posted SU writer quiescence

The functional master now appends `writer_quiescent`, an observation output. It never gates a write strobe. Every asserted `sw_mask` lane and every `red_we` remains a posted write that the VM must capture; there is no producer ready input.

For the currently proved IS1 configuration, the certificate requires released producer reset; no external go, stationed go_q, prefetch go_s or embedding pending command; internal SU idle, inactive and zero inflight; no current VM lane/reducer/KV write; and no producer/prefetch fault. IS values other than1 conservatively return false because inspecting only the last input station cannot certify all intermediate stages empty.

A VM lease may use this certificate only after dispatch blocks new writer command admission and keeps go low throughout the lease. Parent queues must not introduce a new command after lease admission. The certificate describes this producer's lack of future posted write strobes; it does not acknowledge memory commit. Parent posted-write buffers and real VM write acknowledgments must separately drain before admitting a conflicting reader lease. Writes must never be suppressed to enforce a lease.

The new bench monitors future actual VM/reducer writes after certification, until a new go withdraws the certificate. SW8 actual120 accepted commands at VL7/CRX2/ML15/ALIGN1 have5738 certified samples and zero future-write hazards, with exact operand/output/RAW/final-memory traces unchanged. Replacing the certificate with external idle alone produces513 future-write hazards while the arithmetic and final-memory comparison still passes, proving the additional command-station fence matters.

This is a functional observation interface and scoped SW8 certificate proof. Existing fullSW64 proof remains source-bound to its earlier commit. Regional pending-tail coverage comes from that separate fullSW64/RED_ENTRIES proof; the new certificate does not adopt VM pilot staging, physical clock phases, SRAM views, parent area or timing. A physical implementation needs its own port/pair/clock and lease composition proof.
