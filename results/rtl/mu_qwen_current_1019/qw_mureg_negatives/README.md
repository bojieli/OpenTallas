# QW-MUREG: MU collective negatives on the current fixture (10-19)

Source = codex/qwen-mu-current-1019 e6b9c55f2 + recipe commit 3ac055daa (tools/xdie_qtp8/cases.py only; the other 43 staged inputs
are byte-identical to ../source_manifest.json). Verilator 5.050, unpinned ot-run 48 GB / 16 threads, ot-epyc7,
remote /srv/opentallas-scratch/claude/qw-mureg-cur-1019. Runner: run.py <case>. Client receipts: client/.

Why: in the 0e6795834 regression the MU positive (old dv2f14bi fixture) FAILS with coll_fault=die_fault=11111111, and the three
negatives on that same fixture "failed" with the same all-die fault signature -> those witnesses were hollow. The negatives now
use the positive's fixture (_MUC: dv2f18dh2 real lanes + SAFE hard faces + compiled LS 378), so each fails by its own mechanism.

| case | result | signature (fail regex `FAIL \(expected FAIL\)` + `NEGATIVE-CONTROL PASS cases=1`) |
|---|---|---|
| mu_bi (positive, e6b9c55f2) | PASS 2/2 | 61440 + 22528 words, 0 mismatch, all faults 0 |
| mu_bi_mut_rank | expected FAIL | 42288 mismatches, coll/issuer/die faults 0 (pure fold-rank data error) |
| mu_bi_mut_rlat | expected FAIL | 30720 mismatches, faults 0 (R ring read one cycle early) |
| mu_bi_neg_overlap | expected FAIL | issuer_fault=11111111 (calendar overlap caught), 58376 mismatches |
| mu_bi_dv2f14bi_diagnostic (old fixture, current source) | FAIL (diagnostic) | 61424 / 22512 mismatches, coll+die faults 11111111 = bit-identical to the 0e6795834 failure |

Classification of the 0e6795834 coll_mu_bi FAIL: stale recipe/fixture. The old dv2f14bi lane table (a non-release die; old dies are
diagnostic only) fails identically on current source; the release-die dv2f18dh2 fixture passes positive + all three negatives.
Not shown: K-only causality, phase1 / mesochronous / native physical closure, full-token.
