# Native die-e2e runs of IDX.INDEX and COLL.ARGMAX_MERGE (hgi-1010/g3, 2026-10-11)

Harness: rtl/hbm_accel/generic/e2e/tb_hgi_e2e.sv (tools/hgi_e2e/run.py). Every unit not named here is the labelled replay stub.

## COLL.ARGMAX_MERGE

- **Qwen family (DFlash tiny, TP4).** `--real coll`, source 1113269a1, vector dfl_tiny (hgi-1010/e export).
  - Verdict: HGI_E2E PASS, 1,551/1,551 records, final VM and HBM exact.
  - ARGMAX_MERGE: 31 records, all real and exact, 592 cycles each from dispatch to retire (price 586).
  - Mutant `+define+OT_COLL_AMX_MUT_MIN` (the smaller value wins in ot_hgi_coll_amerge): 31 of 31 records mismatch. It FAILS, as required.
- **DS (head vehicle, G 96).** The `export ds --head` run is pending.

## IDX.INDEX

`--real idxn` (the unit at NGLOB 1 / IKS 1, plus hgi_e2e_idxn: the die's selector, 4 stack scorers, 4 svc IKS stripes and the DRAM model). DS L2 / L20 / L24 runs are pending.
