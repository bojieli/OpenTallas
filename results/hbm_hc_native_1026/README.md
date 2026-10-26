# HC source library update

This packet is based directly on main `51fe3d1f83`. It contains six HC providers, the two multiplier DRST connections, a reusable component check, and existing component receipts. It carries no die plan, physical view, cut adapter, source-list selection, or prior development-branch ancestry.

W defaults to64 throughout the bank/qcen/qeng/qhub/root providers; root NQ defaults to4. W128 and root NQ2 require explicit parameter selection. Existing public ports keep their default widths. The new terminal-bank helper depends on `ot_hbm_hc_bankq_core` from `ot_hbm_hc_bankq_static.sv`; it must not be compiled alongside the historical scoped terminal duplicate.

Both multiplier sites now pass `.DRST(ADRST)`, matching their adders. ADRST1 retains multiplier data reset. ADRST0 resets validity/control while allowing invalid data state to remain unknown. Observable arithmetic comparisons are therefore valid-masked; no latency changes are introduced.

The existing current-source four-state regression passes3000cycles, including a three-cycle active reset pulse halfway through. It compares2012valid multiplier outputs and1964valid eight-lane leaf outputs with0failures. Missing-reset and data-flip mutants are caught (9 and803failures respectively). This is finite simulation rather than unbounded proof. Run the same check with:

```
python3 tools/hbm_b2/hc128_drst_check.py --out /ABS/SCRATCH/DRST_CHECK
```

The checker stages canonical dependency sources from this checkout (git HEAD fallback for sparse paths) and extracts the old leaf from the main base. Existing reset censuses record260reset-controlled bits per pair after the fix, compared with8388before; subtree217valid reset bits are unchanged. Receipts retain their original source snapshot identifiers. The candidate RTL bytes match the tested source; adopting those receipts does not adopt any physical plan or timing result.
