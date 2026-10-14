Controller4b replaces the measured negative controller3b indexed arithmetic with eight radix16 carry-save stages and three five-stage add pipelines. Each carry stage processes twelve bits. The unsigned product remains sixty bits and subtraction wraps at that width before the existing 37-bit address range check. The finite row queue now holds 32 rows; admission counts actual pipeline valid flops plus queued rows.

Independent 400-row arithmetic scoreboard covers full unsigned32×27, nonzero first IDs, rebase subtraction and underflow, destination order and bubbles. MUT3 dropping high ID bits yields 398 errors; MUT5 dropping rebase yields 200. Both terminate through actual fatal/nonzero exits.

The four-front component B2 test passes 2,921,984 bytes in 6,574 cycles, hash8432b11fbe800000. Wrong-stack and wrong-lane mutants terminate through actual fatal failures. This fixture preserves source-stack mapping but its any-QID global VM golden is not native VM acceptance.

Production 147 Qwen rank0 LOAD descriptors remain 12,499 cycles against immutable 15,674.320143998 cycles, ratio0.797418956. BF16 reversal reports609,364 errors; wrong epoch stalls/fatals. This remains a component service model; neither actual HBM first access nor native VM ownership/commit delay is measured. The 37,984-element head takes615cycles. No price/ledger qualification changes.

Yosys0.68 proc/flatten/memory_map/opt gives9,529 logical Q bits (NB32, NS1, NL8). Actual mapped roots, insertion, pin fit and setup require the new CTS gate. Controller3b's actual setup−327.656ps is retained. CLOSED lane2 remains untouched; its SS sensitivity−208.71ps does not qualify SS release.
