# Explicit MU slot/event maps in entry-page encoding

The entry-page adapter previously fixed the boot map to two slots, counted
three CSR0x15 and32 CSR0x16 words, and published only a35-word initialization
prefix. The native MU encoder already supported47 slots. The adapter now accepts
an optional caller-owned `mu_config` (`--mu-config` JSON on the CLI), derives
the prefix/counts from the actual complete map, and independently decodes the
map bytes back against the caller's values. The existing two-slot default
preserves every one of its35 bytes/words exactly.

The caller supplies the full native configuration, including all eight events
and each slot's copy/replay attributes. No production map is inferred. The
configuration must preserve the shared KIT/return book and use uniform gaps
that satisfy the actual page reload lifetime and phase. Nonuniform calendars
remain rejected because they need their own explicit reload schedule. The
existing selected-source/manifest/inventory/phase guards remain unchanged.

The finite native encoder/decoder exercise passes47-slot roundtrips with a
single gap (394 words) and47 explicit equal gaps (440 words). It rejects the
obsolete35-word prefix, missing attributes, invalid copy values, a changed
return age, nonuniform gaps, duplicate encoded slots, and a valid but different
copy map. Its maps are explicitly nonproduction codec fixtures. The timing
input and launch fixture are retained historical component receipts; this test
does not requalify those sources or execute any HWIN RTL.

Run `python3 tools/s81_dv/layer_prog/test_entry_mu_map_1107.py`.
There is no DUT/RTL change, whole-die simulation or new token-rate claim.

The local HOST reservation is still charged at five edges per encoded word.
Against the35-word default,394 words add1795 initial HOST edges (1.495235us at
833ps);440 add2025 edges (1.686825us). These are one-time boot reservations
per resource, not a per-record penalty. Reload pages still omit MU setup and
cannot reconfigure an armed tracker. Actual global first HOST/KS/reset dates,
production47-slot resource/event ownership, all-eight-HWIN qualification and
consumer retirement remain open.
