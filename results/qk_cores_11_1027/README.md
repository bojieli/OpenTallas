# QK-CORES-11 (2026-10-27) kv3_pv_pair in-core clock tree (METHODOLOGY 12.8b)

GEOM-REVIEW-37: R0 bc3bfb5cb5c0 clock reach 276.05 > 220 (single centre entry; 285 um centre-to-corner).
KV master clock slice (KV-CORE-SLICE-1, kv-cores-r6/slice24 kv3_pv_pair core_tree) = [2,1] islands (95.04,95.04)/(285.12,95.04),
but (95.04,95.04) lies ON the W SRAM stack of the static macro sites (x 15.55-129.38, y 76.35-128.95), and a single
half island cannot reach 220 once moved off the SRAM. Re-sited with the plan tool tools/die_plan/core_islands.py
(SRAM-aware maze, equal-load, k=4 --sym, die island_ft rects as keep-outs) on the pass-1 placement census (dump_clk.py,
29,716 FF + 8 SRAM clk on s1__clk[0]):
islands (95.04,69.12) (125.28,146.88) (289.44,64.8) (267.84,133.92), entry maze 116.6-129.6 um, leaf maze max 158.8 um.
Tree (build_pv_tree.py -> shared core_infra.install, PRE_GLOBAL_PLACE after face_flops.tcl): s1__clk[0] -> 4 BUFx12f branch
buffers in the entry island -> 4 FIRM BUFx12f island nodes -> CTS-open leaves 7429 regs + 2 SRAM clk each; kit_cts_hook
makes CTS build only the leaves. No RTL / cycle / pin change.
Note: this is a kit-level re-site of the slice islands; the KV plan owner should carry these 4 sites in the next KV slice.
