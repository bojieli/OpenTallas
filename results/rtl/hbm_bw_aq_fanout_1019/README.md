# HBM BW AQ same-edge fanout surgery

Source base: 18bd3c0ef. This helper owns only AQ head, ACT, row command and refresh selectors. CFG metadata, K/KR rings and global reset remain with the BW parent.

The analytical model estimates 188 additional flops after unused original head-row captures are removed. SRAM count, payload widths, port bandwidth, operation schedule and pipeline latency do not change. OP_GAP384 remains the production contract; its 66-operation/154-GO proof must be rerun on the combined parent source before adoption.

Head words are captured on the existing head update edge in four local copies serving eight banks each. Two local ACT-row copies and registered onehot selected-bank identity remove the shared ACT bank mux selector. Group-valid copies serve eight-bit ACT row mux slices. Two command row copies and decoded validity flags serve sixteen banks each. The local row payload has no reset, because its ACT flag controls every consumer. Four copies of the final refresh selection are captured on the exact original final tournament edge; each drives one live-bank lookup.

The comparison bench instantiates the exact 18bd3c0ef AQ source under a different module name and compares every output each active edge. It covers mixed read/write requests, sequential bank blocks, ring wrap, and eight resets. Three negative controls corrupt only the new head, ACT onehot or refresh selection mechanism and must fail with AQ_EQ_MISMATCH.

This is component equivalence, not token simulation, production throughput qualification, physical closure, or release adoption. A mapped synthesis census must verify retained unique copies, actual buffer-collapsed critical loads <=32, reset ownership/load, area and clock census before any gate. No shared physical tools changed; no CTS or routing launched by this helper.
