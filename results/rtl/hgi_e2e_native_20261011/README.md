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

`--real idxn` (the unit at NGLOB 1 / IKS 1 / IKS_EVEN 1, plus hgi_e2e_idxn: the die's selector, 4 stack scorers, 4 svc IKS
stripes and the DRAM model), source 9d5abe71a (claude/hrl-idxn2-1011 = tput-hbm-1011's 4959a3820 IKS_I seq fix + the two
fixes below), vectors `export ds --iks` of rank 0 (G 96, 1M context).

| layer (record type) | verdict | IDX.INDEX record | RTL dispatch->retire | price |
|---|---|---|---|---|
| L2 (n 524,288, no C/D) | HGI_E2E PASS 105/105, final VM/HBM exact | rec 26 exact | 2,536 | 658.9 |
| L20 (cand_en, D 1366x2) | HGI_E2E PASS 106/106, final VM/HBM exact | rec 21 exact (3,756 words) | 3,823 | 1,212.0 |
| L24 (keep_en, C 2048x2) | HGI_E2E PASS 103/103, final VM/HBM exact | rec 19 exact (1,024 words) | 9,291 | 1,080.0 |

- Mutant `IDX_MUT=2` (R from the wrong lane), L24: 136 IDX words mismatch, HGI_E2E FAIL, as required (`idxn_ds_L24_mut2/`).
- Fix 1, L2 hang: hfd_idx_score consumes 2 blocks a beat; rank 0's L2 quarter 1 holds 341 blocks and the IKS issuer
  streamed exactly 341, so the last beat never filled. `ot_hgi_idx_iks_issue` EVEN (unit `IKS_EVEN`, default 0)
  rounds B_q up to even (cap 342); the pad keys are masked by the scorer's nq; the exporter's key image pads to match.
- Fix 2, L20 mismatch (order only): the simulator wrote D value-sorted, the native selector emits the owned blocks in
  ascending id. D's only consumer, COLL.TOPK_MERGE (candidate merge), is order-invariant (sim lexsort over all
  contributions; ot_hgi_coll_tkm strict total order), so the sim now writes D in ascending block id and faults unless
  D.n == the owned block count. The re-exported L20 layer is sim-PASS against the golden; no RTL change.
- Throughput (not qualified): the record cycles above are 3.85x / 3.15x / 8.60x the price; the scorer restructure to the
  priced key rate is a separate stream.
