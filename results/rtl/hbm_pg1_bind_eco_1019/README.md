# Exact HBM pg1 closed-view native PG binding ECO

These three timing-CLOSED pg1 views were built before standard-mode bind-before-protection fix `67cb1acc7` (2026-10-19 21:28:41 PT). The L2H-IDX native audit ran afterward at 21:40–21:41 PT against those existing ODBs; its failures do not establish a failure of the corrected source flow.

| Exact job | Source | CLOSED record | TT setup ps | FF hold ps | DRC |
|---|---|---|---:|---:|---:|
| hbm_argmax_swvm_r2_g2c_1019-pg1-c456d3869 | c456d3869 | 39abebe4a | 31.42 | 23.52 | 0 |
| hidx_op_n12_g2c_1019-pg1b-f7377a019 | f7377a019 | 38404fd99 | 16.77 | 11.77 | 0 |
| hdie_col_idx256_1019-pg1-59616a483 | 59616a483 | 69989cb5a | 109.02 | 27.03 | 0 |

The existing ROOT4 receipts at `results/rtl/hbm_pg_bind_eco_1019` cover older argmax/n12 `g2c-c11f3bb33` views and pretree. They do not cover these exact newer pg1 views; no idx256 ECO receipt existed there.

Method: the unchanged S81/ROOT4 `pg_bind_eco.tcl`, with `native_pg_binding.tcl` from main `c5c712178`. It uses the ODB's own global-connect rules, binds only unbound native POWER/GROUND ITerms, restores original dont_touch flags and refuses unexpected or wrong-net terms. The full native census runs before and after. Signal-net topology/wire length, instance placement/orientation and dont_touch flags are fingerprinted before and after and compared byte-for-byte. This is a database connectivity fingerprint, not a logic-equivalence simulation. VDD/VSS grid checks run after writing a new ODB. No routing, clock, RTL, timing constraint or original ODB changes.

Outputs are isolated in `/srv/opentallas-scratch/claude/codex-hbm-pg1-eco-1019/<exact-job>/pg_bind_eco_native/6_final_pgbound.odb` on ot-epyc7. Each source.txt identifies the exact input and output. Original inputs are mounted read-only and SHA256 checked before/after. Unpinned `ot-run --mem 32 --threads 1 --dir <own-root>` admitted on the data-local host. Original immutable failed audit reports remain at their recorded remote paths; committed summaries preserve their hashes and failure class counts.

All three runs completed with native audit PASS, VDD/VSS grid checks PASS, identical signal/placement/dont_touch fingerprints and unchanged original input SHA256. All ot-run clients report RAN exit 0.

| Exact view | Terminals bound | Native terminals checked | Output ODB SHA256 |
|---|---:|---:|---|
| argmax pg1 | 772 | 191340 | cee81daf9c19e905093205227b03ab794237a72bb8807ea01cc4d54877ecc6c6 |
| n12 pg1b | 1491028 | 1643664 | 91ce83e70a2d1ca527eae23541291dd1b70631860ca6f8e6cac7f146c02ca924 |
| idx256 pg1 | 636 | 192670 | e8f3f54a866cada2e73c7d037ba34fcdcef512d34f55feba074e9fc4844e9fe5 |

The original failed ODBs and verdicts are preserved. These receipts qualify only the exact new pgbound ODB paths. Consumers must explicitly select those ODBs and run their native die PG-binding check; this evidence does not change a consumer manifest or attest that downstream integration already happened. Timing values above remain the original timing-CLOSED records, with signal wiring unchanged by this PG-only ECO.
