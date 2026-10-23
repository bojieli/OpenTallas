PV r18 full same-slice replay with the opt-in SVG ATT_MARK fix (TOKd-HBM 10-22).
Result: SLICE_PASS, 181/181 checks, 0 fails, 64 SM rows = 512 FP32 values exact (first 85215, last 85278), no nonzero fault output, 86000 stream edges (19.6 min, 0.28 GB).
Binary: original r18 PV slice objects (pv_r18_probe) with only the svg hier block Vot_hbm_svc_sm_group_rel_id_hw0 re-verilated from the
patched m78 master (patch_m78.py; bench copy sets ATT_MARK=1, source default 0); wrapper port-identical, protect-lib hash pinned to the original.
Programme: v2 (Codex 5b61e0207) + SVG word bit119 on exactly the 64 attention issue words v3 touched; bit25 kept (compare_v4.json).
Raw logs: ot-gold1 /srv/opentallas-scratch/claude/tokd-hbm-pv-attmark/{v4.log,v4.time}. v3 failure kept: /srv/opentallas-scratch/codex/hbm-pv-calendar-1022/preserved_v3.
