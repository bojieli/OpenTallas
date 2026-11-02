# Selected native GO/TAG producer failure and disabled four-FF repair

The actual selected0L01/e0 native wiring silently delivers the next operation's
tag. CFG7 emits GO with tags0,1, then its tag output advances on the following
edge. GO traverses the actual two-register qbank_S while tag connects directly
to the Q input. The GB capture consequently sees tags1,2. All existing fault
signals remain0. This result uses actual dates and an independent reset-zero,
per-GO counter oracle; a shared-reference miter alone would hide the defect.

The executable cut is actual XRT target2 CTL decoding, actual XS4/calendar and
real current CAP-safe field0L01 phase0 replayed twice, current41-stage1104-bit
bound input, CRS4(E2/LFACE0/LGATE0), actual station/relays, actual CFG7 with real
C0 mask images, actual qbank_S, and the unchanged extracted GB/RSTP GO/tag
capture logic. No direct is_v/is_d oracle drives XS4. The real producer matches
all booked issuer words/dates with its measured3-edge XRT stage. The calendar
selects the native one-edge-early Q launch; no under_TEST guard is invoked.

At833ps, native advance1 produces sequencer GO at760/1272 with tags0/1,
qbank GO at762/1274 with direct tags1/2, and GB capture at763/1275 with wrong
tags1/2. The proposed parallel two-edge tag pipe captures correct0/1 at the
same763/1275. A GB0/old-calendar reference has the same intended dates/tags.
The old-calendar+GB1 control arrives one edge late764/1276; the tag mutation
produces1/0. Both are rejected independently. All50 CFG words and160 XS stream
words, including their dates, are identical across the five runs. XR, XS,
CFIFO and CFG7 faults are0 in every run, including the original silent failure.

Intel/Epyc admission and build identity are retained in native_run_receipt.json;
passing Epyc2 unit3270885-1793604621 exited0. Two source-intake build failures
(wrapper port mismatch; incomplete readset) are preserved and diagnosed.
There is no native rerun or duplicate whole build in this packet.

The primary DISABLED source delta is exactly two2-bit pipeline registers,
parallel to the actual two-stage GO path:4 reset-free FF,4 clock pin loads,
0 reset pin loads. Only the selected consumer's tag connection changes. Tag
availability moves2 edges (+1666ps) to meet its already-delayed GO; no GO, CFG,
XS, issuer or data cycle is added. The tag pipe follows all clock samples, so
it needs no inter-GO holding-spacing premise. The alternative two-FF GO-latched
hold remains a separate conditional512-spacing experiment and is not the
primary repair or a claim about legal native Q-bank spacing.

`disabled_native_e0_align2.diff` is an exact, unapplied emitted-source witness.
The actual type has five replicas. The candidate specializes only fW0_p1_b0;
the other four remain unchanged. Applying the change to the shared type would
cost20 FF, not4. A hypothetical uniform864-pair extension would cost3456 FF,
but each other native path still requires its own identity/depth/source join.
The authoritative frame/source generator and four actual FF placement sites
must be prepared before source-cohort or physical adoption. No canonical
source, plan, active cohort, provider flag or capture-fold flag is changed.

This is one producer/GO-tag capture boundary cut. Q arithmetic and its real
walking/bank_free/sh_free feedback are not instantiated; EF is controlled
idle/free. The selected source calendar spacing is512. Reset is asserted for
15 initial cycles, all commands occur after reset settles, and forwarded
clocks use the controlled L3 startup profile in the bench. The real die's
regional phases, general reset/restart contract, legal minimum Q-bank cadence,
whole frame/token, capture folds and source epochs are unqualified. The
measured dates are experiment dates, not production epoch assignments.

Full untouched logs, input images and compiled binary remain at
`epyc2:/srv/opentallas-scratch2/claude/codex-ds-native-go-2310/retry3`.
Full disabled specialized source is private at
`intel1:/srv/opentallas-scratch2/claude/codex-ds-native-go-2310/candidate_part_DISABLED.sv`.
ROOT authorized this selected-instance disabled+4FF event for review, with
coherent source/clock/model preparation required before a cohort flip.
