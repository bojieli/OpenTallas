# Native B2 adapter component evidence

Four exact boundary tests and all four matching mutants passed their expected
gates on ot-epyc4 under ot-heavy2GiB. The minimum actual-memory vehicle contains
one shared-client mux, one native hub and one native bank, all1024rows/8192words,
and the real1024x256 SRAM simulation model with OT_MEM_NO_INIT. Two issuers
write/read4096sectors: all tags, echoes and golden read words match; four-credit
peak is4, measured20484cycles (0.199961sectors/edge,6.39875bytes/edge).
The issuer-owner mutant fails on the first misrouted response. This is an actual
memory port rate measurement; no immutable simulator price was supplied for
the new adapter, so production price qualification remains OPEN.

Boundary packet mock:4096sectors/22532cycles. Native SM sink:128fragments,
1664beats/4992cycles, every actual SM sampling edge precedes matching owner ACK.
Read and write translations each check32768mappings, every lane, slice and
mirror field; mirror boundary overflow is refused; credit/done stay distinct.
Receipt r2 source SHA and full run/build logs/rc files are in
results/rtl/hbm_native_b2_adapters_1013/r2. Tests establish mechanisms, not a
complete VM8/SM/quant/router integration or physical closure.

Pulse-only native peer bridge (four ingress seats/issuer) also passed against
the same full1024row actual-memory vehicle:4096sectors/20485cycles, peak8
retained producer permissions while the hub remains bounded at4. A fifth
request/producer before return faults; the owner mutant fails. Native receipts
are under results/rtl/hbm_native_b2_adapters_1013/native_r2.

The retained command seat passed a nativeP4/K7168 mirror command, global to
local rebasing, stalled loader command, identity mutation on live input pins,
x_done before traffic drain, and P8/K7168 mirror overflow refusal. The missing
rebasing mutant fails. Receipts command_r2 preserve source SHA, rc and logs.
The real dispatcher must reserve the actual publication/lane resources before
installed/command acceptance; the seat serializes leases and has not been
priced against pipelined production commands.

VM8 producer gap is still mandatory: actual xload xw_en is an unstalled pulse
stream; VM8 staging has serialized wr_ready and only2562063-bit row seats.
The largest native fragment stream has1664beats. No direct producer binding
may discard pulses or pretend256seats buffer1664beats. A held emitter or
measured bounded FIFO needs source-specific throughput/physical qualification.

Opt-in PIPE1 sink accepted1664consecutive beats, observed1664native SM input
sampling edges and1664matching owner192/ticket16 ACKs; accepted-to-root-ACK
latency2edges. Every beat uses one identical lease owner and a distinct
generation11/bank1/slot4 ticket, with alternating banks. Data, ticket and
early-ACK mutants all fail on the first affected edge. PIPE0 default still
passes its1664beat/4992cycle exact case and its data mutant fails. Source SHA,
all rc/build/run records are in sink_pipe_r2. PIPE1 remains default-off and
physically/production unqualified. It establishes boundary acceptance only;
selected SM internal x-write wl/wm/w0/branch paths still need source-specific
commit/drain safety before engine launch. Root allocator must hold and match
both owner192 and ticket16 until all4receiver ACKs; no owner-only release.

The first inline-shell launch failed to produce separately named case files
and is preserved under sink_pipe_initial_shell_failure (not qualification
evidence). The successful run used the source-pinned run_sinkpipe.sh file.
