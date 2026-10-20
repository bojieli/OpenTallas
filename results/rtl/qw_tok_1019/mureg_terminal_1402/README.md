# Current Qwen MU regression followup, 2026-10-19 14:03 PT

Artifact-only read-only followup to `74de31939` / `current_receipts_1332`. No jobs launched, cancelled, rebuilt or restarted; no source or production helpers changed. Earlier failed receipts and failure IDs remain intact in that parent packet.

**44 of 45 top-level legs are terminal.** Client logs record 43 exit-zero legs and the intentionally preserved old dv2f14bi fixture diagnostic exit one. The only live leg is `ctlm_nsl12`. Terminal wrappers alone do not establish correctness; actual DUT witnesses are classified below and the current 45-leg witness ledger is retained in `subcase_witnesses.json`.

H1 and H4 each report **bench2(h) MUT=0 PASS 12/12** on actual executable simulations. Each checks the status SID field of all 12 slices following SETID enumeration, at MU_NU=1 and 4 respectively. Their raw h.log shows every S0ST through S11ST SID. This is control/status coverage; it does not test full numerical layers or four independent numerical tokens. The source function, runner, raw output and executable hashes are included.

The live original CTLM leg has already recorded these actual verdicts:

| Subcase | Actual verdict |
|---|---|
| ABI MUT0 | PASS 256 vectors |
| ABI MUT4/5/6/7/8 | causal FAIL 255/112/255/127/69 errors |
| Calendar NSL0 MUT0 | PASS 62/62 |
| Calendar NSL0 MUT1/2/3 | causal FAIL 2/2/60 of 62 checks |
| Calendar NSL12 MUT0 | PASS 74/74 |
| Calendar NSL12 MUT3 | LIVE, no verdict yet |

At capture, original Verilator PID78983 is active at99.9% CPU, elapsed718s in the final MUT3/NSL12 build. Parent bench PID78977 remains live. Earlier completed objects and the newly finished NSL12 nominal executable remain untouched. Do not label this leg complete before its final actual `CTLM_CAL MUT=3 NSL=12: FAIL` witness and both aggregate summaries are present. Preserve any unexpected failure.

All140 scoped source hashes equal candidate `715e572ace085894f342b4dfda2d302cb93f1165` and the previous snapshot. All45 executables previously recorded remain present and byte-identical. The broader current named-executable scan records nine additional executables (six previously omitted CTLM equivalence binaries and the three newly completed H1/H4/NSL12 nominal binaries); these are additional inventory, not a claim that all nine were built since13:34. Source sampling scope is unchanged and does not prove every staged dependency.

Other current witnesses remain preserved: the MU collective positive passes61440 words and user0 reference22528 words with zero mismatches/faults; rank42288 and read-latency30720 mismatch controls fail with zero fault bits; overlap58376 mismatches asserts collective/issuer/die faults. Old-fixture61424/22512 mismatch diagnostic stays a FAIL. Existing AMIX, slice, DHUSER, host, KV, CTLM, opseg, head and smoke coverage remains scoped as in the parent packet. Source prerequisite and production ABI qualifications remain open. Neither component campaign is a production-shape full-token/four-user numerical qualification.

`receipt.json` carries actual capture UTC time, complete collected text/hashes, executable hashes and live process argv. `comparison.json` records source and prior-executable comparisons. `leg_status.json` and `client_logs/` preserve actual client exit receipts for all45. `raw/` retains current top-level outputs, h logs, CTLM progress and exact classifier source. `subcase_witnesses.json` extracts actual verdict lines without treating exceptions as expected behavioral failures. No QWLAYER claim is made; its independent staging repair has a separate active owner.

Next pickup: collect only the existing final CTLM MUT3/NSL12 job and its aggregate summaries, then reconcile the current campaign. Do not duplicate builds or infer success from shell exit zero.
