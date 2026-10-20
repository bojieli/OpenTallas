# Current Qwen MU regression: final existing-job receipt

Read-only terminal pickup of the original 45-leg campaign at candidate `715e572ace085894f342b4dfda2d302cb93f1165`, following `b83d7515f`. No jobs, source, fixtures, executables, build settings or timing assumptions were changed. Capture UTC is in `receipt.json`.

All **45 top-level legs are terminal**: **44 client exits zero and one preserved old-fixture diagnostic exit one**. This is a terminal count, not 45 passing functional tests. `leg_classification.json` maps every leg to actual nested behavioral witnesses, preserves positives and controls separately, and retains the old dv2f14bi fixture failure. Some runners return zero after an expected behavioral FAIL; those FAIL witnesses remain visible.

The last original leg, `ctlm_nsl12`, finished at **2026-10-19 14:33:11 PT**. Its actual final witness is **`CTLM_CAL MUT=3 NSL=12: FAIL 61/74`**. Nominal NSL12 is PASS 74/74. The original command/event log and classifier source are preserved, including the mutant's twelve SID observations all equal to zero. Both QCTLM and MU_CTLM aggregate summaries report PASS because the mutant fails as intended.

| Existing CTLM subcase | Actual result |
|---|---|
| ABI MUT0 | PASS 256 vectors |
| ABI MUT4/5/6/7/8 | FAIL 255/112/255/127/69 errors |
| Calendar NSL0 MUT0 | PASS 62/62 |
| Calendar NSL0 MUT1/2/3 | FAIL 2/2/60 of 62 checks |
| Calendar NSL12 MUT0 | PASS 74/74 |
| Calendar NSL12 MUT3 | FAIL 61/74 |

Other component coverage remains scoped: AMIX nine-bench face/NU positives, four-user m/n controls, two twelve-slice status enumerations, slice gap positives and behavioral negatives, DHUSER, host/hroot/KV addressing, collective, CTLM, opseg, head and synthetic token smoke. Existing current collective positives pass 61,440 words and the user0 reference passes 22,528 words. Rank/read-latency controls fail with 42,288/30,720 mismatches; overlap fails with 58,376 and actual fault bits. The old-fixture diagnostic retains 61,424/22,512 mismatches and its rc1. Hroot's named mutants, KV assertion stops and other causal controls remain actual failures in the ledger rather than being erased by wrapper exits.

All **140 scoped source hashes match the preceding source-verified snapshot**, which compared them to candidate 715e572ac. All **54 previously inventoried executables remain byte-identical**. Exactly one additional inventoried executable is the completed original MUT3/NSL12 binary: SHA256 `0bcb053c42a1d07b42304a8dcb4ec8828f68d7202d0b224e7eb2b7ac0393e4b8`, 198,060,888 bytes. This inventory is not a claim that every staged source or generated executable has been checked. The staged SOURCE_COMMIT is preserved. No matching original compiler/simulation/CTLM runner was active at final capture.

`receipt.json` contains full copied raw text and SHA256 values, source hashes, executable hashes and capture time. `raw/` preserves final top-level logs, actual AMIX/slice/DHUSER logs, complete six calendar logs plus the final stimulus, and relevant original runner/classifier sources. `client_logs/` preserves all 45 client completion receipts. `comparison.json`, `leg_status.json`, `leg_classification.json` and `final_ctlm_witnesses.json` state the explicit comparison and actual classifications. `collect.py`/`remote_collect.py` record the read-only collection method. SHA256SUMS covers this packet; earlier partial/live and failed receipts remain unchanged in ancestry.

This campaign does **not** establish four independent numerical requests, a production-shape full token, native per-k matrix-stream timing, canonical gold completion, or physical closure. Those release dependencies remain open. No simulation or build remains pending for this particular 45-leg campaign; no rerun is proposed by this receipt.
