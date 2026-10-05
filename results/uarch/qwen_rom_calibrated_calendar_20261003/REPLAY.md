Calibrated Qwen3-8B ROM KV-service calendar (model only, not adopted)

This is the successor to the qwen_rom_kv_* calendar records. Compute is recalibrated to the retained TP4 RTL terminal:
- each layer takes 4,668 cycles, including 2 x 991 exposed two-segment all-reduces;
- the non-layer cycles are 3,042 (head 2,998, 43 unattributed, and 1 L0 extra);
- me_lat_extra is 167 (112 wire stages plus 55).

The 8K attention adds 1,220 cycles per layer. This comes from the unified model and is UNMEASURED, so it is a sensitivity only.

The fill path is the credit17 composition with strict REFab (issued at its due edge) and QROM-KV-SECDED-B1 conservative latency (+3 return edges, +2 request edges, +2 assembly periods; +0.404 mm2/die). The SECDED applies to mutable SRAM/FF state only; there is no ROM ECC.

| record | token | tok/s | verdict |
|---|---|---|---|
| baseline-r1.json, position-0 measured | 357.99 us | 2,793 | calibrated baseline |
| baseline-r1.json, +1,220 8K attention (unmeasured) | 359.71 us | 2,780 | sensitivity |
| streaming-rejected-r1.json, position 0 | 347.06 us | 2,881 (+3.15%) | REJECTED |
| streaming-rejected-r1.json, 8K | 356.65 us | 2,804 (+0.857%) | REJECTED (<1%) |
| near-hbm-selected-r1.json, AR 991 | 190.97 us | 5,237 | SELECTED FOR BUILD (model entry) |
| near-hbm, one-segment AR 620 / 490 (unmeasured) | 168.71 / 160.91 us | 5,928 / 6,215 | sensitivity |

The streaming candidate was priced like for like on the baseline service. The reviewed numbers, priced on the 16-credit predecessor with lazy refresh and no protection, are preserved inside its record. Every record carries the 20 workload-identity fields. compare() refuses any undeclared mismatch, and summary-r1.json lists the refused comparisons.

Two cross-checks run inside the build, and the build refuses if either fails:
- The same edits under the uncalibrated compute reproduce the reviewed 357.1349667 us.
- The cross-layer loop in all_grants control mode reproduces the baseline calendar exactly.

The review inputs are committed under inputs/ and sha256-pinned in the tool. Repository sources and the credit17 production pins are hashed into every record.

Run from the repository root:

```bash
(cd tests && python3 -m unittest test_qwen_rom_calibrated_calendar -v)
(cd tools && python3 uarch_model_qwen_rom_calibrated_calendar.py --verify)
```

`--verify` regenerates all four records in a temporary directory, runs 7 calendars in parallel processes (about 4 minutes on a loaded 32-core host), and requires the output to be byte-identical. No RTL, P&R or numerical run is involved. PROPOSED_DOC_CHANGES.md lists doc corrections for the owner of main/docs, and none of them are applied here.
