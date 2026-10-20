# BW safe portable transaction qualification — 2026-10-19

This packet records a **failing qualification**, not a closure PASS.

The benchmark gives released H9b and BW safe the same 6,000 mixed requests and the same consumer readiness. Both consume responses using readiness from the preceding edge. It checks every read tag/beat/data and write bank/column/strobe/data in order, complete read/write conservation, no controller faults, and candidate completion within baseline + 10% + 64 edges.

Original AQ policy: all 12,944 read beats and 759 write columns/completions match. H9b finishes at edge 88,783; BW safe at 166,919. The rate criterion fails. `random_rate_fail.json` pins every source byte by SHA-256, with base revision `a9604c68e`.

The default-off `BW_MUT_ID_TAG` changes only pending-identity SRAM write tag bit zero. `txn_mutant_fail.log` witnesses `BW_SAFE_TXN_BEAT_MISMATCH`; `mutant.json` records successful detection of that nonzero DUT run. It also retains the independent rate failure.

The rejected open-page experiment adds `need` to the precharge candidate mask, preserving unused open rows. Source commit `dbab74e0d` is preserved on `codex/hbm-bw-openpage-experiment-1019`. It stalls the mixed transaction stream by the 400,000-edge diagnostic bound and regresses production DS seeds to 14,788 / 14,778 / 14,800 cycles, versus 9,492 / 9,385 / 9,366. Packed increases from 17,549 to 29,658 cycles. Its logs and source hashes remain in `openpage_rejected/`; the variant is not adopted.

Fleet: `ot-agidock128:/srv/opentallas-scratch/claude/hbm-bw-txn-1019`, Verilator 5.050. No local compilation.

Run the original policy from the source root:

```
python3 tools/hbm_layer_vehicle/hbm_pc_bw_safe_txn.py --work /absolute/scratch
python3 tools/hbm_layer_vehicle/hbm_pc_bw_safe_txn.py --work /absolute/scratch --mutant
```

The first command currently fails its rate gate; the second succeeds only if the mutant run fails with the required beat-mismatch witness. Production throughput and JEDEC timing qualification remain separate controller bench obligations.
