The native head uses `DENSE_IMAGE=1`. The shared calendar wrapper defaults to
profile 0 only to preserve historical streamed configuration benches. Production
SU must explicitly select profile 1 too.

An actual PW0 write clears calendar, copy-command and XPF staging. The receiver
then accepts the ascending 1024-word PW image followed by eight DW writes.
The actual instruction reservation is at most59 instructions (PW0..943).
The collective command calendar uses944..959 plus its CL seal960; its compiled
END row is mandatory even for a stage without collective commands. Each command
row accounts for the issuer launch edge, actual D_seq relay edges and the new
collective input pin register; none of these offsets may come from runtime readiness.
ME/SU calendar records occupy976..1003; four possible XPF188 records occupy
1004..1015; CAL1, CALS and CAL2 metadata occupy 1016..1018; the three CP56 payloads
occupy 1019..1021; XPFT occupies 1022. Unused record and copy slots contain zero.
Only the validated footer at 1023 seals staging. CALS at 1017 records metadata;
it does not seal this profile.

The footer is `{32'h58504631,19'd0,fused_capability,stage6,xpf_count4,2'b10}`.
The compiler derives the capability from the actual canonical native PC11 ISA
instruction, and the authenticated 1032-word image digest covers that footer.
It is not a configurable Boolean argument to the compiler. Missing records,
nonzero padding, invalid counts, duplicate records and reserved footer bits
prevent sealing. The control-store ready outputs are configuration facts;
normal issue timelines continue to use the fixed calendar and fault on status
mismatches.

The head's `program_obs[75:0]` is `{consumed_v,full_word,addr10,data64}`. A local
`qkd_program_pw_observer` observes the exact input pins consumed by the two real
64x512 program macros. The receipt is registered on that same macro edge and
is available for a ledger to consume on the next edge. It is not the launched
PW command. The physical parent forwards 76 receipt bits, not 2062 raw macro
pins. SU owns the one actual descriptor store. Its69-bit consumed-write receipt
is used directly by SU and through one actual observation register for TT,
matching TT's deeper program-bank input. No TT descriptor memory is invented.

`control_stores_ready` joins the actual ME, SU, XPF loader and XPF monitor seal
outputs. Installed capability additionally requires the independent actual
macro/DW ledgers and matching authorized epoch/digest; this control signal alone
is not byte attestation. The source compiler format fixture and component
calendar timings do not qualify a full native program or a physical route.

Checks: `python3 tools/qwen_split/check_dense_image.py` and
`python3 tools/qwen_split/check_static_internal.py`. The latter composes the real
head and production SRAM functional model, checks every receipt against the
actual committed macro array, seals all actual control stores from an ascending
image, and runs reserved-footer/nonzero-padding mutants as well as the existing
actual decoder, numeric-fold, CP, context and route gates.
