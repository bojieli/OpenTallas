# FUSED.QDQ on the VM lane group (tput-gate-1010, 2026-10-10)

`ot_hgi_quant_unit` WIDE=1 sends fast-path records to `ot_hgi_quant_wide`:
- A fast-path record is a legal QDQ header with A and O both VM FP32 words: inner stride 1, 8-word-aligned bases and strides, inside VM, and either disjoint or identical.
- The engine reads 4 sectors a cycle on 4 lanes, landing each in its lane's 4-deep response FIFO (lane b only ever holds sectors ≡ b mod 32, so assembly is a registered 4 × 32:1 select with no slot muxing), and runs `ot_hgi_quant_decode` at II 1. It writes 4 sectors a cycle on the W2 lanes.
- Every other record goes to the packet transport unchanged.

## Gate

The gate is `tools/hgi_unit_tput/run_qdq_wide.sh` (Verilator 5.050, ot-epyc3), run on the 8 DS-shape vectors from `qdq_vectors.py`. It passed (`gate`).

| run | what | result |
|---|---|---|
| m0 | wide | PASS: 8 records, 3,328 words exact, 503 cycles |
| w3 | the same records forced to the packet path (control) | PASS: 2,319 cycles, the previous unit |
| m1 | header A-bit mutant | FAIL, as required |
| w1 | lane-to-sector mutant | FAIL, as required |

## Rate

| shape | cycles per record |
|---|---:|
| n 512 | 65 |
| n 128 | 53 |

**Ratio against the price of record (owner 2026-10-11).** The token path charges ceil(n/32) + 8. Prices are not adjusted to fit measurements, so the measured ratios stand against that price:

| op | measured / price |
|---|---:|
| QDQ_FP8 | 2.74 |
| QDQ_FP4_E8M0 | 4.50 |
| QDQ_FP4_E4M3 | 2.75 |

The excess is the decode's fixed 23-edge latency and the VM round trip, on a unit that already moves 32 elements a cycle. It stays UNQUALIFIED until the unit owner or P&R resolves it. The packet unit was 14.6×; the wide unit is 5.4× faster on the same records.

`m0_repriced.log` (an earlier repricing, withdrawn) is kept as history. `report.json` reads `m0.log` at the price of record.

## Open

- **Physical:** the route is hgi_quant_wide-68fe4bf34-tc-cl. The hb_quant die view needs FUSED and quant to share lgE slot 2 through a local 2:1 mux.
