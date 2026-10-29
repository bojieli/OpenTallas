# HBM token takeover 2026-10-29 13:55 PDT

Current decisions: DMA RR80 option(b) response SRAM padding, a122 VM option(B) finite compiler phases.
This follows the current defaults; the earlier grown-VM proposal is not selected here.
No inherited HBM token job remains live. Current bind is103 UNPLANNED/84076bits+EMIT HBM-035;
SPB V3 now GRT0/pin-access PASS. There is no current full-source token vehicle.

## Finite VM phase compiler preparation

`tools/hbm_next/vm_phase_split.py` constructs the actual SU1470 six-row operation as three two-row
records. Every HGI-1R row expansion preserves arithmetic/template/immediates and slot identity;
only the explicit input and scalar carry bases change. All three fragments pass the existing ISA
legality/row-independence checks. Bounds and input/carry-alias controls are rejected.

The fragments use explicit candidate work base178224 and scalar carry260144. These are a preparation
example, not a grant to overwrite other currently live values. The tool deliberately leaves
`full_programme_fits=null` and emits NO executable image. Producer source grouping/spills, reload
addresses, complete phase live sets, later scalar-consumer rebasing and actual timing remain required.
The emitted hex lives in a nonexecutable JSON preparation record only.

The important failure in the DIE-HBM-18 estimate is now concrete: splitting the consumer alone
cannot remove the already resident six-row producer values. This particular policy must publish
245760 source A/B words and reload those245760 words: **1966080 transferred bytes**, six stores+six
loads=**12 DMA records**, plus scalar retirement/phase drain dates. Earlier0.36-0.72% estimates used
an unrelated fixed per-record latency probe and do not price these transfers. No revised tok/s claim
is made without actual native DMA descriptors, scratch authority, source publication and scheduling.
Tail/H/carried operands also stay live and must be included in the full fit.

The original399360-word live-set witness still rules out a fixed address rebase of the unchanged
programme. Finite phases are feasible only when actual producers and transfers are transformed too.
No SRAM growth, clock change or mirror reinterpretation is introduced by this packet.

Source image: retained immutable a1228bb5771a604f53aad9de3366f460fd9d7c0c59b9a04fa2856405b5726933,
record1470 offset199776. Decoder is the pinned P3 tools42d0caba4. Reproduce:

```
PYTHONPATH=MAIN/tools python3 tools/hbm_next/vm_phase_split.py \
 --image candidate_mtp_N6_a122.hgi1r --compiler-tools PINNED_P3/tools \
 --workspace 178224 --carry 260144 --out phase_1470.json
```

Next: split the actual producing SM/COLL/SU rows before capacity overflows, assign disjoint HBM scratch,
emit real source spills/reloads, then retime scalar consumers and price bytes/drains. Do not install the
prepared consumer fragments alone. No owner question is needed for continuing the selected(B) work.
