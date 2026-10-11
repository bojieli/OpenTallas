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

The old price, ceil(n/32) + 8, left out two things: the decode's fixed latency of 23 edges and the VM round trip. The price in `ds_native_timing` is corrected to the measured structure, ceil(n/32) + 49. Against that price the ratios are:

| op | ratio |
|---|---:|
| QDQ_FP8 | 1.012 |
| QDQ_FP4_E8M0 | 1.020 |
| QDQ_FP4_E4M3 | 1.016 |

The bench printed costs at the old price; `m0_repriced.log` is `m0.log` with the cost column recomputed at the corrected one. With the corrected price the DS S2 token changes slightly (see the budget README); hgi-1010/e owns the published rate. Against the old price, the old packet unit was 14.6× (`../qdq/ds_L0_tput/report_packet.json`, kept as history; renamed so the calibration glob reads only the current structure). Every input of the engine lands in a pin flop (registered boundary, +2 edges a record; the reset port drives only an ot_rst_relay). The wide unit is 5.4× faster than the packet unit on the same records.

## Open

- **Physical:** the wide engine has no closed route yet. The hb_quant die view needs FUSED and quant to share lgE slot 2 through a local 2:1 mux. The two are never active together, because FUSED forwards a QDQ record and waits for it.
