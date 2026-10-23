# PEER p36 structural timing replacement

PEER p36: same-edge RX metadata capture with rd removes the measured 448-bit zero-test into SRAM wd[512]; exact distributed lifecycle user selection removes the late head index/bypass cascade into hc_tag. Zero additional external edges; retain p34 coordinator RX predecode +1 and reset/head-gap contracts.

Source proof: existing lifecycle witness passes 2,957,102 compared edges with real terminal/cancel/POST traffic and resets; stale-head negative rejects cycle197. Existing RX witness passes100,000 edges/69,460 consumed heads and accepted metadata negative rejects. Native generated0fc3015d has88,230 primitive correspondences and actual max32 census PASS. Existing independent initial-state cold-copy comparison and D/clock negatives remain required before physical gate launch.

Safety checklist: exact macro role IDs regenerated from current source; unchanged separated 3-SRAM geometry; retained full-face pin balance and clock distribution; no new clock or timing exception; no SRAM storage replacement; new RX flags are DATA qualified by unchanged rv/reset validity; queue head refresh/gap/reset edges retained. Exact source packet and geometry still require actual MAIN/fallback CTS results and ROOT PNG review before normal submission. No prior view or timing result transfers.

QDIE5-HC 10-22 (p36b): clock item 7 changed: OT_SPINE replaced by the full-domain ck_core tree in clock_tree.tcl (n38 C7 method); everything else as p35b.
