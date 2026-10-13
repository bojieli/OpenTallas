# S81 SU: views re-exported at the routed verdict session (2026-10-13)

Same routed ODB + SPEF as each closed verdict; the export session slack must equal the verdict.

| tile / job | verdict TT / FF / SS (ps) | export session TT max / FF min / SS max (ps) | tool | child_lint |
|---|---|---|---|---|
| smt hb1 (odb d14528c2) | +11.51 / +3.66 / -285.32 | +11.505 / +3.656 / -285.317 | pre-landing `--post-sdc` prototype (same sequence) | not run |
| smt hb2 | +38.24 / +10.51 / -279.92 | +38.243 / +10.513 / -279.916 | main abc334b14 view_export | PASS |
| qnt cb32 (VT-swap ECO odb) | +55.05 / +4.97 / -247.94 | +55.051 / +4.974 / -247.942 | main abc334b14 view_export | PASS |
| swe gfix | +145.41 / +2.26 / (-173.92) | +145.415 / +2.262 / -173.923 | pre-landing prototype; main-tool rerun queued on ot-epyc4 `/srv/opentallas-scratch2/claude/s81su-vseq/swe_gfix_main` | PASS |

Before: smt hb1 exported FF -90.65 (-19.69 after the SPEF-order fix); qnt cb32 record ae9b5d603 exported FF -113.77.
The .lib contents change with the session (qnt cb32 ff/ss/tt libs differ from ae9b5d603), so the old views must not be used.
The adopted qnt cb32 view is physical/ref_tile/s81su_qnt_cb32_ref/views/dsfd_su_t_qnt (this commit).
