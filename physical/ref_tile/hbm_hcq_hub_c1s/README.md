# hbm_hcq_hub_c1s -- c1s (HBM-COLLECT10/COL-HC 10-21): successor of hbm_hcq_hub_c1q

HBM-COLLECT10/COL-HC 10-21 c1s: hbm_hcq_hub_c1q re-gate (10-21 08:30, ot-gold1) REFUSED by the in-gate mapped native census (PRE_GATE_NATIVE_CENSUS, limit 32): 75 drivers, max 217 -- gathered reader rs_c[] QN 139..217 (ABC folded the rk==b one-hot decode into the 32-b AND-OR selects), qcal programme captured[23..25] QN 76..80 (npos-1 folded into the 3 x 19-b gb masks), 3 decode nets 33/34. Fix: the decode / n1 on KEPT wires (ABC boundaries): decode bit -> 32 select loads, rs_c bit -> one 3->8 decoder, n1 bit -> one 19-b mask. Same function, same edges (0 added), port-identical. Prior: HBM-HCBANK6 10-20 (H.STA.BLK.17.2) structural successor of hbm_hcq_hub_s1/s1b/s2/s2b (all --cts gates FAILED: GATE_STALL rc137 in post-CTS repair_timing -hold, 28,269 hold endpoints at margin 30 with ONE 51,334-sink root whose arrival spread 566..849 ps; mapped native32 census 1,057 / 960 drivers > 32). (1) REGISTER MASS OUT OF THE GLUE: levels 1..4 of the quarter subtree (60 of 63 LAT-7 adders, ~37k flops) are 4 hard children ot_hbm_hc_qtree16_static (one master x4, kit hbm_hcq_tree16_c1) beside the W-face s_i pins, each with its own clock entry clk_t[c] (hybrid_entries: the die delivers phi 

SAFE-DESIGN checklist: as hbm_hcq_hub_c1q (below) with item 3 Fanout fixed: the mapped in-gate census (limit 32) refused rs_c / captured / 3 decode nets; decode / n1 now on kept wires (32 / 19 loads). 0 added edges.

# hbm_hcq_hub_c1q: fallback twin of hbm_hcq_hub_c1p -- HBM-COLLECT10/HCQB 10-21, H.STA.BLK.17.2

Spec physical/hbm_hc_hub/specs/hbm_hcq_hub_c1q.json = hbm_hcq_hub_c1p (same RTL, children, pins, outline, benches,
native_untouch + band PRE_GLOBAL_PLACE hook) + GPL_TIMING_DRIVEN=0: global placement runs no resizer buffering; repair_design /
repair_timing run after placement on the untouched native graph.  Port-identical to c1p, 0 added cycles.  See
physical/ref_tile/hbm_hcq_hub_c1p/README.md for the crash classification and the SAFE-DESIGN checklist (identical).
