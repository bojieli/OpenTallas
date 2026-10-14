# Actual native service and physical memory composition candidate

`composed.cpp` joins four independently compiled RTL models: native frontend,
native attention arithmetic, the production KV sector mapper, and 128 instances
of the actual HBM PC controller. It uses one shared Verilator context and one
runtime/DPI implementation. Core edges are 833,334 fs apart and HBM edges are
1,024,000 fs apart with a 137,000 fs relative phase. Cross-model interfaces settle
with clocks low before any accepted transactions are sampled.

The initial gate is a **component composition**, not an executed layer. Q and
current K/V are checkpoint-derived source vectors. Current K/V enters as accepted
SU-shaped issue/write transactions, then passes through actual formatter, row
assembly, native sector mapping, controller ECC, PHY writes and WDONE ACKs. No
current KV is preloaded into physical memory. All 255 prior K/V rows also enter
through actual controller writes; their completion ownership is separate from
the current-token sector queue.

Q reader requests read mutable VM. The receiver commits each actual attention
write into that VM and only subsequently returns its tagged commit ACK. Expected
attention vectors are used exclusively for final comparison. The arithmetic is
the actual production attention service; host exponent/reciprocal substitutes
are absent.

The first arithmetic library is startup-fixed commit `593c88424`. Its known
multi-frame defect remains open; this gate uses a single attention frame and
does not reset between artificial frames to hide that defect. Layer completion,
eight-rank collective integration, layer transitions, physical VM timing and
full-die throughput remain separate requirements.

Copied transport helpers originate in native dispatch (services VM adapter
commit `31b7c1b4b` and the parent's kernel/sector helper snapshot). Physical PC
headers originate in `674847d6f` / `25244646a`. Every admitted execution records
the exact helper, archive and vector hashes in `out/inputs.sha256`.
