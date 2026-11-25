# QC-ALLFIX-TSV tools: ledger-vs-plan gate

Every QC cut runs `lvp_gate.sh PLAN LAUNCH_TREE` before launch, and the launch proceeds only on rc 0.
The rule is COORD 11-25 06:2x item 3, added after STB ring row 44a145a65013 and RRL-RAWTAPHOLD 06248f276e80 were found missing from the plan.

- `ledger_vs_plan.py`: for every ALLFIX-QC.tsv row whose status claims the plan (IN / STAGED / PENDING / READY / BOUND / KIT / COMPOSED), the script tests that row's own keys and values in the PLAN CONTENT, as listed in `manifest_current.json`.
  - Verdicts: PRESENT, PARTIAL n/m, ABSENT, NOTPLAN, NO-SOURCE, ERROR.
  - DEFERRED rows that have a source are judged and printed as DEFERRED/<verdict>, but they never fail the gate.
  - `--drop-list` files in guard format mark removals already declared at a gate as DROP-DECLARED.
- Exit codes: rc 1 on ABSENT or PARTIAL (not DEFERRED), NO-SOURCE or ERROR; rc 2 when a manifest source file is missing.
- `manifest_current.json`: maps each row to its source.
  - Kinds: `file` (plan pair), `step`, `rowchk`, `set`, `seatset`, `jsonpatch`, `prune`, `keys`, `visrow`, `files` (RTL overlay by sha under --tree), `notplan`.
  - Paths point to the lane dir on epyc12, `/srv/opentallas-scratch2/claude/QC-ALLFIX-TSV`.
- `visqc/*.json`: row files for VISQC rows whose original json is gone, holding keys transcribed from the originating posts, or NO-SOURCE with an owner.
- Run it on a build host, never on localhost: `ot-run --priority die --crit --mem 64 --threads 1 --dir <lane dir> -- bash lvp_gate.sh PLAN TREE`.
