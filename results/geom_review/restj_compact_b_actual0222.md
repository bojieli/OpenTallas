# RESTJ compact B exact candidate pin review

Actually viewed this pin model for E4 ot_hgi_sfu_split3_ctl_rest_1c_vB_0222.181.44x267.84um, actualM5 clock90.744,133.824, previousactualclock216.024,224.64 preserved with embedding125.28,90.816. All edge pins use legal M3/M5 vertical or M4/M6 horizontal tracks; no coordinate collisions/boundary overflow. Sliding20um windows remain below50% on every face/layer. M5PDN remains unchanged and needs actual physical access review.

New source differs from A4 by full32-bit prefixrounding and bounded input-control/reset-chain copies. Same joined +1semantics,0additionalpin cycles. Component SAT/strictgraph/mutants PASS. Native B LEC must pass fresh. One first compact B PLACE may run after nativeEQ; actual density/dataflow/sink reach and reset port loads must be read beforeCTS. No parentPOR adoption or route release.

Class DEPTH+SPARSE; changes address A4 1281.70ps serialround path and790.4um resetspread. New source area, clock insertion, real fanoutspread and congestion are not yet measured. All B synthesis/LEC and subsequent stage receipts remain separate from A4.
