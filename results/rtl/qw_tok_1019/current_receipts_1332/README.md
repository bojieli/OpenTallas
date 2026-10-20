# Current Qwen token receipts, 2026-10-19 13:32–13:34 PT

Artifact-only read-only snapshot. No jobs launched, restarted, cancelled or changed. This packet is distinct from the historical 44-leg 0e6795834 campaign.

The current QWREG source is **715e572ace085894f342b4dfda2d302cb93f1165**. All 140 sampled qwen_split, qwen_dv and MU test/helper files match that exact Git commit (source_compare.json); this is a scoped source comparison, not a claim that every staged file was verified. launch.sh contains a stale historical comment naming 0e6795834; stage.sh, remote SOURCE_COMMIT and per-case headers identify 715e572ac. Actual Verilator is 5.050.

**42 of 45 top-level legs are terminal:** 41 wrapper exits zero; the intentionally preserved dv2f14bi old-fixture diagnostic exits one. H1, H4 and ctlm_nsl12 are compiling at the snapshot. Wrapper exit alone is not accepted as a causal verdict. Raw nested outputs and hashes are retained below.

- AMIX: six face/NU combinations each pass nine a–g/i/j benches; all six 4-user m seeds and three legal/mixed n cases pass. Three AM_MUT7 controls fail 1/2 because the mixed root scalar fault is absent. H1/H4 have no verdict.
- Slice: four gap16/20/24/30 positives pass8/8. Ten NEG cases have explicit behavioral FAIL (counts and detailed mismatches retained), not build failures. FACES11/12 each FAIL1 even though the simulation returns zero; FACES0 at NU1/4 pass.
- DHUSER: two nominal seeds and slip detection pass; mutants produce3494/349 mismatches or fail slip detection. Their zero simulator exits do not erase the failure witnesses.
- Collective: actual current MU positive61440 output words and user0 reference22528 words pass with zero mismatches/faults. Rank42288 and read-latency30720 mismatches are causal data controls with zero fault bits. Overlap58376 mismatches asserts collective/issuer/die faults. Old-fixture diagnostic61424/22512 mismatches with collective/die faults is retained as diagnostic FAIL, not a current positive pass.
- Host, hroot, KV, CTLM, opseg, head and token-smoke wrapper summaries and causal failures are preserved. These component/synthetic tests do not constitute a full numerical token at production shape.

**QWLAYER NU1/4:** no bench.out exists. Both builds remain active (11/10 cc1plus at this capture). Existing plan is ten cases per NU: seven vector positives and three mutants. Source recipe remains0d4c9808f with missing lowerer files from416cd1a11. No layer numerical verdict is inferred. Matrix qkv/gu/od compiler STN kc port remains owed.

**Canonical TP4 CPU oracle:** PID1583528 lives at100833 elapsed seconds (~28h),3984% CPU, last position6976/8191. Its original source marker is8a01e4a5a; exact oracle script SHA is in canonical.txt. No completed full-gold verification, L35/head numerical completion or four-independent-user numerical result exists. Original L3/L3negative mismatches are retained in canonical.txt. Shared-prefix driver361d9985c remains source-ready only; canonical full verification precedes any new independent request golds.

The next pickup should collect only the three current regression legs and both existing layer builds, then verify their actual nested outcomes. Preserve the progressing canonical oracle and perform its existing manifest/verification steps only after gold rc0. Never duplicate these jobs.

Files: ep7.json includes snapshot time, per-output hashes/witnesses, scoped source hashes, actual build PIDs/CPU/RSS and the layer run recipe. raw/ retains complete copied nested and top-level logs, including original failure IDs. executables.json hashes45 existing named simulation executables; it does not claim every compiler-generated executable is inventoried. SHA256SUMS pins the local packet files as collected at slightly different times; active logs can grow remotely.

| Top-level leg | Captured status |
|---|---|
| amix_F0 | wrapper rc0 |
| amix_F1 | wrapper rc0 |
| amix_F2 | wrapper rc0 |
| amix_FACES1 | wrapper rc0 |
| amix_FACES4 | wrapper rc0 |
| amix_G0 | wrapper rc0 |
| amix_G1 | wrapper rc0 |
| amix_G2 | wrapper rc0 |
| amix_H1 | LIVE / no terminal marker |
| amix_H4 | LIVE / no terminal marker |
| amix_N0 | wrapper rc0 |
| amix_N1 | wrapper rc0 |
| amix_N2 | wrapper rc0 |
| coll_mu_bi | terminal expected summary |
| coll_mu_bi_dv2f14bi_diagnostic | terminal preserved old-fixture diagnostic FAIL |
| coll_mu_bi_mut_rank | terminal expected summary |
| coll_mu_bi_mut_rlat | terminal expected summary |
| coll_mu_bi_neg_overlap | terminal expected summary |
| ctlm_mu | wrapper rc0 |
| ctlm_nsl12 | LIVE / no terminal marker |
| ctlm_rest | wrapper rc0 |
| head | terminal expected summary |
| host | wrapper rc0 |
| hroot | wrapper rc0 |
| kv | wrapper rc0 |
| opseg_mut | wrapper rc0 |
| opseg_pass | wrapper rc0 |
| sl_DHUSER | wrapper rc0 |
| sl_F0_nu4_m_gap16 | wrapper rc0 |
| sl_F0_nu4_m_gap20 | wrapper rc0 |
| sl_F0_nu4_m_gap24 | wrapper rc0 |
| sl_F0_nu4_m_gap30 | wrapper rc0 |
| sl_FACES_mut11_nu4 | wrapper rc0 |
| sl_FACES_mut12_nu4 | wrapper rc0 |
| sl_NEG_i_mut11_nu4 | wrapper rc0 |
| sl_NEG_j_mut12_nu4 | wrapper rc0 |
| sl_NEG_m_am1 | wrapper rc0 |
| sl_NEG_m_am2 | wrapper rc0 |
| sl_NEG_m_am2_e | wrapper rc0 |
| sl_NEG_m_am3 | wrapper rc0 |
| sl_NEG_m_am4 | wrapper rc0 |
| sl_NEG_m_am6_rootnoclr | wrapper rc0 |
| sl_NEG_m_gap12_stnpend | wrapper rc0 |
| sl_NEG_m_nu1_w | wrapper rc0 |
| tok | wrapper rc0 |
