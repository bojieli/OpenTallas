# SEGCAL whole-head default-OFF equivalence (collected by QW-ORPHANS 10-20 05:30)

Codex jobs (QW-SEGCAL hand-back 02:12), both TERMINAL on ot-epyc7:
- namespace r2 (session 57222, unit oth-ubuntu-3642439-1792486399, exit 0): gold = closed head ae6b0c59a STAGE_ME1,
  gate = 6e943b668 SEG_CAL0 (default OFF), names-only normalisation (genblk1.g_dense -> g_dense, 101 names, ledger
  namespace_ledger.json), macro cut certificate (2 paired 64x512 macros, 2146 macro input bits statically identical,
  assumption: same macro state). Yosys equiv_simple -seq 4 + equiv_induct -seq 8 + equiv_status -assert:
  **16903 proven / 0 unproven -- "Equivalence successfully proven!"** (namespace_r2_tail.txt; miter sha
  7491ab9f... matches the certificate). => WHOLE-HEAD default-OFF proof PASS.
- macro direct (session 22455, exit 1): same pair without the namespace normalisation: 18117 proven, 64 unproven, no
  counterexample (induction depth on name-mismatched generate scopes; list in macro_direct_unproven64.txt). Superseded by
  the namespace proof; kept as history.
Full logs stay on ep7 /srv/opentallas-scratch/claude/codex-qw-segcal-1019/src/results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv
(sha256 in namespace_r2_tail.txt head).
