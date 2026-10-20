# LEP hierarchy v1 matrix -- terminal collection (S81-MUBUF4, 2026-10-20)

Source: ot-epyc4:/srv/opentallas-scratch/claude/codex-s81-lep-hierarchy-1019 (unit oth-ubuntu-4160557-1792456854, scope inactive;
all matrix logs last written 10-19 17:41-17:46, tested source = results/rtl/s81_lep_hierarchy_1019/tested_v1_source.sv.gz on
codex/s81-lep-hierarchy-1019 d7cb08cb2). Copied read-only; remote objects preserved.

| case | verdict |
|---|---|
| lepmu none seed5, lepmuh none seed1/5, legacy (HIER_LANES=0 lep_muh) | BENCH_PASS |
| lepmu TAGDROP / LANDCUT / STALEHD / VSKEW | BENCH_FAIL (caught) |
| lepmuh HSTAMP / KSOFF / VSKEW | BENCH_FAIL (caught) |

The two logs missing from Codex's v1_receipts (matrix-lepmuh-VSKEW-1: TX regional-state assertion lane1 group17;
matrix-legacy: default-disabled lep_muh PASS) close the v1 matrix: every positive passes, every causal mutant is rejected.
v1 is complete. v2 (d7cb08cb2, legacy core preserved byte-for-byte) is still UNRUN and is based on bb66563eb, i.e. BEFORE
the native32 / LOCAL_WA lepmu source (codex/s81-lepmu-native32-1020 aad61c82c / 6cb5f3eff). Running v2 as-is would qualify a
superseded core; a hierarchy successor must be rebased onto the LOCAL_WA source first (see lanes/S81-MUBUF4.md).
