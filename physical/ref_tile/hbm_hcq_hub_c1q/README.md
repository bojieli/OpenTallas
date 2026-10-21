# hbm_hcq_hub_c1q: fallback twin of hbm_hcq_hub_c1p -- HBM-COLLECT10/HCQB 10-21, H.STA.BLK.17.2

Spec physical/hbm_hc_hub/specs/hbm_hcq_hub_c1q.json = hbm_hcq_hub_c1p (same RTL, children, pins, outline, benches,
native_untouch + band PRE_GLOBAL_PLACE hook) + GPL_TIMING_DRIVEN=0: global placement runs no resizer buffering; repair_design /
repair_timing run after placement on the untouched native graph.  Port-identical to c1p, 0 added cycles.  See
physical/ref_tile/hbm_hcq_hub_c1p/README.md for the crash classification and the SAFE-DESIGN checklist (identical).
