# S81 MU actual terminal pickup — 2026-10-19 17:43 PT

Source lineage `233a1b448` combines HSLOT8e9b03d6 with HWIN capture private package; no physical adoption is implied.

Original `seqhost_01` failed checker import (`check_mu` was absent). Its outer wrapper still returned 0 after a successful independent lint; `SEQ_RC=1` and `SEQHOST_MU_GATE FAIL` govern that run. Preserve the first failure.

Corrected staged-checker `seqhost_02` terminated on ot-epyc7 unit `oth-ubuntu-3062083-1792454043`: actual `SEQHOST_MU_GATE PASS`, `SEQ_RC=0`, ot-run exit0. AR92starts/46users and MTP22starts/11users preserve user0 and zero latency relative to plain. Allfive fault cases detected, mutants1/2/5 detected; host/HWIN local regression and lint pass. `actual_inputs.sha256` is the actual input directory read back after completion; initial compile-time historical hashes are not inferred from it.

This qualifies the source regression only. HWIN21c physical gate failed setup/hold; its next-address structural successor remains necessary. Full token exactness, native parent fit, clock/boundary and PG qualification remain open.
