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

`full_layer.cpp` and `run_full_layer.sh` are an **unexecuted integration draft**
until a real fullshape core archive exists. They replace all fixture current
transactions with actual core instructions, QR writes and SU KV outputs, run
eight distinct kernel instances, and carry mutable VM across segments 0/14/22.
The two actual collective invocations consume the produced VM partials only.
Every actual VM write carries the previous accepted provider PC: SU/reducer
ownership changes only at an accepted, fully idle SU descriptor; ROM ownership
changes only after the previous instruction's exact output count drains. Writes
on an issue edge are sampled before owner replacement. Native writes carry PC11.

`verify_full_layer.py` is an observer. It compares every operation commit against
that instruction's independent source snapshot, exact addressed current KV
stores, all three quiescent END-boundary VM snapshots, final defined VM effects,
and both collectives' complete returned payloads. It rejects the historical
linear-eight-rank oracle. No verified output enters any DUT/provider input.
