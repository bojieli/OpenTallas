# G0C-REGRESS-1 CODEX takeover

## CODEX notes
2026-11-01 20:38 PST: Diagnosis905a97b1e (codex/g0c-regress-1101, source-only results) pushed; original failing reports preserved in own scratch results/g0c_regress_1101/{head,hbm}/g0_report.json. HEAD l48x3911 =3910 raw producer/unused-output failures + old1native reset refusal. All154 typed raw exports match old5f93tools;43/154 match current a0f8tools;111 changed producers replicate1955uses. Root cause: density tap PG-safe/per-bit site changes0ddc1ccd8/1d753c326 change derived reset topology while stored export metadata stays old. Frozen wave703c07481 predates both; HEAD collector checking original cohort before dispatch. Current-tools paired plan+sidecar reset/raw export refresh is required, not renaming or gate suppression.

HBM d44c250 =old14 +236 newly exposed actual input-S0→S1 reach failures from54687a1ee (63hops,117stations,56reach).128merged clock rows PENDING-VIEW, never PASS, separate from error count. HBM owner working currentd44r paired source-event repairs (su00 entry/stations corrected). No clock/cycle/contract relaxation.

Next: HEAD exact-frozen cohort collection/paired current-source refresh; HBM current-event geometry repair. No new P&R/STA jobs launched by regression diagnosis. OWNER? none.
