# LANDING-WRAP-TOOL handoff (started 11-23 21:00 PST by COORD)
Job: writer START side of tools/die_plan/clock_landings.py wraps a port-driving raw reset relay like the reader side (FLOW-6), instead of raising (QC C1b sle_su_c rr_t85 EMIT refusal).
- Code: epyc10 /srv/opentallas-scratch2/claude/LANDING-WRAP-TOOL/wt (base c40acd92e63, uncommitted until probes pass). Helper _private_raw_copy shared by reader+writer; relay lookup regexes accept the pair; verify RAW_HOP_PORTS; adv_raw_reset_port writer hits -> INFO.
- Unit tests: test_writer_start_depth (2 new + 1 changed), test_clock_landing_verify (1 new). Pass.
- Probes: C1b epyc7 LANDING-WRAP-TOOL/c1b (private fork of QC-ALLFIX/cC/tree + plan_c1_fix1 62ce8aba0292, c1b.sh orig|wrap, --types sle_su_c);
  S81 epyc10 LANDING-WRAP-TOOL/s81 (j8_cut_tree, cmp.sh), KV epyc9 LANDING-WRAP-TOOL/kv (fable-unc-kv/fork_d28_aff, cmp.sh).
- Next: push via ot-push-main, sha -> FLOW-OPS, report COORD.

- 22:21 PST PUSHED main 9f95aa48604. Sha sent to FLOW-OPS (aa86b9b) and PRECHECK (a1433c0). C1b: the rr_t85 refusal is gone; next independent error is rr_t168 with no driver, handed to QC-ALLFIX-SU. S81/KV byte-identical. Lane job done; private dirs stay until ot-delete cleanup.
