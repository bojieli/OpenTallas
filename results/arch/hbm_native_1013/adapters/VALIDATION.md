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
