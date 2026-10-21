# r15 functional binding successor

Base ec3b4e25c, isolated branch codex/hbm-r15-binding-1021. r14 remains immutable.

Before initial pin-view synthesis, l28 sets four collective parents AR_ITER=1, ROWS=256 using the measured main_rows256 source manifest. Six RTL source blobs differ from the base, including the 8-bit PC/issuer_m256/v7 selection. The DS_RS144 bench published and checked 144 vectors at 862/872 cycles without faults; the compiler initial programme needs 218 rows (final programme 215). This is component evidence; changed parent synthesis, native views and die physical results are outstanding. ROWS128 CLOSED issuer views cannot stand in for ROWS256.

Per-bank x-load RD_LAT RTL is taken byte-for-byte from dcd8f08b4. The reset-carrier manifest contains all 32 CLOSED exact-source forms, including the previously missing 1136 EW/WE rfc views. QDQ split_r3 latency lookup is prepared; the actual QDQ/share2 remaster and other new closed children remain separate integration work.

The chain is prepared, not launched. It must not use r14-bound current-primary synthesis for changed collective parameters. The chain refuses R14_REUSE_PRIMARY: changed ROWS256/source requires matching synthesis. All 204 declared source paths were materialised from this branch and inventoried with SHA256 (missing 0); the committed compressed contract has SHA256 99756f7ec3fe40e1dab45ae3da313ee27df40b941ddb173e620b5e1b19a70dd9 after decompression. Fleet source staging and physical view materialisation remain required before launch. SU calendar grants require token-lane fix f265064a5 in the functional vehicle; that fix does not establish a production unified calendar. No native or die closure is claimed.
