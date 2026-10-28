# Optional KV R8 position ABI v2
The current native full-hull ledger requires token delays up to 9 and epoch delays up to 2. V1 supports only token 2/epoch 1. The explicit new fixed-decode ABI uses the existing stack/group IDs, with zero new wrapper pins and no software-controlled delay selector. V1 source and its guard remain unchanged.

| Master profile | Instances | Token max | Epoch max | Kept FF per instance | Total FF |
|---|---:|---:|---:|---:|---:|
| Ordinary PC | 24 | 9 | 2 | 194 | 4,656 |
| Head PC | 4 | 4 | 0 | 72 | 288 |
| V2 total | 28 | | | | 4,944 |
| V1 total | 28 | 2 | 1 | 52 | 1,456 |
| Increase | | | | | 3,488 |

Every selected count is derived from one complete 18-bit token or 16-bit epoch member in ledger.json. The generator rejects incomplete positions, duplicate words, partial words, unsupported pads, or a physical-profile/position mismatch. All instances of each master retain its maximum pipeline capacity. The existing ID inputs remain the only selection inputs; unsupported profile positions bypass, as a defined function, and the parent census permits only the 28 declared positions.

Fresh generic RTL LEC passed all 28 used constant-ID variants, including the full kept maximum-capacity pipelines. A wrong-tap mutant left 36 unproved equivalences. The independent full-width word model passed 300 observed edges at all 28 positions; the same mutant failed at position 5. Receipt and reproducible runner are adjacent; live full logs remain intel2:codex-kv-r8-v2-1028. First formal setup required removing keep_hierarchy only in the miter harness; no source guard was removed.

This is a COPY component, disabled in production source selection. No area/timing/clock-load/route result is claimed. The ledger is the current pre-RT20 full-hull native source; regenerate the decode in the eventual source/plan event after ECTL K alignment. Existing token/epoch bus identity and unreset data-pipeline semantics are preserved. No production START date is supplied.

The component solves the 56 PC token/epoch word sites. It does not solve remaining per-source fault-OR legs or header boot-go alignment. Those require a separate maximum-capacity static-count bank at each actual pre-OR landing site; delaying the already-ORed scalar is not equivalent. Whole-die R8, native source bind, physical views, and final token schedule remain open.
