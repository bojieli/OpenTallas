# HOST6 prompt ps1: source candidate, not closure

Microarchitecture sizing before build: original completion FIFO depth16, EVW=68+3*NW (116 bits for NW16,122 for NW18), at most one accepted write/read per cycle. One32x546 p192 SRAM stores the complete payload. Existing count/write/read admission stays byte-for-byte; read address prefetches the post-edge head. Registered collision bypass reproduces write/read same-address behavior. Added latency0, throughput1 event/cycle, ports1R1W, boundary width unchanged. SRAM gross17,472 bits, allocated payload1,856/1,952 bits. This intentionally trades SRAM area for removal of wide runtime mux and load-enable cones. No rate claim yet.

V5.050 primitive positive PASS20,000 cycles; bypass and address mutants FAIL causal cycles1/7. Logs here. Full production MU host bench and full mapped native census are next qualification steps.

SAFE checklist: pins unchanged inherited registered boundaries; reach UNQUALIFIED pending plan/placed audit; fanout UNQUALIFIED pending mapped census; depth UNQUALIFIED; storage event payload fixed in SRAM; floorplan diagnostic388.8x475.2 on43.2 lattice with no overlaps, utilization pending synthesis; clock inherited boundary branch, measurement pending; schedule+0. NO layout/adoption until all native requirements pass. Existing failed p8 evidence retained.
