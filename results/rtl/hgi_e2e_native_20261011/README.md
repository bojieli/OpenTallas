# Native die-e2e runs of IDX.INDEX and COLL.ARGMAX_MERGE (hgi-1010/g3, 2026-10-11)

Harness: rtl/hbm_accel/generic/e2e/tb_hgi_e2e.sv (tools/hgi_e2e/run.py). Every unit not named here is the labelled replay stub.

## COLL.ARGMAX_MERGE

- **Qwen family (DFlash tiny, TP4).** `--real coll`, source 1113269a1, vector dfl_tiny (hgi-1010/e export).
  - Verdict: HGI_E2E PASS, 1,551/1,551 records, final VM and HBM exact.
  - ARGMAX_MERGE: 31 records, all real and exact, 592 cycles each from dispatch to retire (price 586).
  - Mutant `+define+OT_COLL_AMX_MUT_MIN` (the smaller value wins in ot_hgi_coll_amerge): 31 of 31 records mismatch. It FAILS, as required.
- **DS (head vehicle, G 96, rank 0 of 96).** `--real coll`, source 1113269a1, vector ds_head (hgi-1010/g3 `export ds --layer 39 --head`),
  the LM-head vehicle: FUSED HC_PRE_NORM -> SM MATVEC LM head -> ARGMAX.LOCAL -> COLL.ARGMAX_MERGE, 4 records.
  - Native run (`ds_head_coll/`): HGI_E2E PASS, 4/4 records dispatched, final VM and HBM exact; the COLL record byte-exact
    (1 real, 1 exact, 0 mismatch), 614 RTL busy cycles vs the 765.4-cycle sim cost charged to the op.
  - Mutant `+define+OT_COLL_AMX_MUT_MIN` (`ds_head_coll/report_mutant.json`): the real record mismatches 1/1 -> FAIL, as required.

## IDX.INDEX

`--real idxn` (the unit at NGLOB 1 / IKS 1, plus hgi_e2e_idxn: the die's selector, 4 stack scorers, 4 svc IKS stripes and the DRAM model). DS L2 / L20 / L24 runs are pending.
