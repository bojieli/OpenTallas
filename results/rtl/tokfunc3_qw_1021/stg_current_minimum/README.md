# Retained SU_LT=1 STG4 minimum component replay

Scope correction, 2026-10-21 22:40 PT: the retained binary was compiled with `-GSU_LT=1`, MU4, ARF1 and RP1. It selects the older ML1 hard lane. It does not qualify the current die's `SU_LT=0` flat lane or its issue-to-output ages. Exact matches of all 28 input files establish source-byte identity only; the earlier claim of identical current parameters was incorrect. Token/S81 owns the separate current `SU_LT=0` single-lane proof. No duplicate replay was launched here.

All five expected outcomes on binary `6df53648fb792b3ce0d88be40356e5679eb33d29810575807035685dd0e77866` remain valid for its actual compiled parameter tuple: L0 QK/RoPE, OD/ARF, LM and EMB pass, and the RoPE-late causal negative fails as expected. Unit 3963631 on EP7 exits zero only after checking each explicit verdict. Original outputs and source hashes are preserved. The full STG4 build flags remain in `../stg4_receipt/qualified_stg_result.json` under `build_receipt.pos.flags`.

The initial portable attempt lacked compiler model JSON files and failed before replay. The exact dependencies were staged before this successful retry. No progressing compile was cancelled. LM and EMB use component operands. Physical S8 parent/tail timing, actual HP13 crossings, the final shared programme and complete current-die token remain separate obligations.
