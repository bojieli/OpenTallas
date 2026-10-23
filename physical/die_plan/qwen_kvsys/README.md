# qwen_kvsys die plan (PLAN-KV, TOPDOWN-PLAN)

Inputs: `asbuilt_rtl6_e33504a6f.json.gz` = `extract_asbuilt.py` on the rtl6 GEN case (ep5 `codex-kvgen-2140/run_main_rtl6/case_kv`, source e33504a6f).
Rebuild (tools/die_plan from claude/plan-tool-1023):

    python3 build_plan.py --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out /tmp/stage1.json.gz
    python3 emit_plan.py --stage1 /tmp/stage1.json.gz --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out die_plan.json --report plan_report.json
    python3 tools/die_plan/gen.py latency die_plan.json --inplace
    python3 tools/die_plan/check.py die_plan.json --png
    python3 kv_params.py /tmp/stage1.json.gz > kv_params.json

## v2 (PLAN-KVv2, 10-23) -- die_plan.json is now v2 (v1 at 1bf4cda41)

Regular die-row lattice on PLAN-TOOL's 8.64-um grid: 16 rows x 1520.64 um (4 HBM PCs per row), 7 columns
PHY | PC | HG | PV | HG | PC | PHY; W/E quads are MY copies, the N half is MX about a 1.2-mm centre band (hroot x4 +
centre control hub: kvs_ctl, kvs_attn, host, ahub, pvfin, emb, seq, pvw ctl/RH, astk ctl/zn); sys row on top (sys_W
UCIe/d2d, sys_core pll, sys_E serdes). 120 partitions / 24 types, no channels or strips (the v1 hgrp|PV lane strips are
ft slots of hg/pv). PHY sliced per row (1520-um slices). astk ep/owner folded into the hg rows (owner chain follows the
physical slg order). S-quad hsl chains re-headed at hsl_31 (qkd_hslice_dn, the N-quad form) so pc rows share one type.

    python3 plan_v2.py --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out stage1_v2.json.gz
    python3 emit_v2.py --stage1 stage1_v2.json.gz --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out die_plan.json --report plan_report_v2.json
    T=<plan-tool>/tools/die_plan; python3 $T/gen.py latency die_plan.json --inplace --out gen; python3 $T/check.py die_plan.json --png
    python3 kv_params_v2.py stage1_v2.json.gz > kv_params_v2.json

Open: pv rows stay positional (9 types; vport vo all-gather keeps natural widths, a constant-width trunk costs ~3
cycles/row of RL); sys<->hub traffic shares the hg_WN pass corridor; bus leaf bindings not yet declared (G0 WARN).

## v3 (PLAN-KVv3, 10-23) -- die_plan.json is now v3 (v2 at 62a634aa3)

COORD 05:29 v3 items on the v2 lattice (scripts plan_v3.py / emit_v3.py / kv_params_v3.py / cells_v3.py):
- IO row = sys_c (UCIe x64 PHY + d2d + fwd/clk bumps + dcal, cols 3-5, N-edge centre) + sys_E (SerDes, N-E corner);
  d2d <-> hub in two straight corridors symmetric about the PV axis: hgi_WN column -> hub_Wi (host, kvs_emb, embgw),
  hgi_EN column -> hub_Ei -> hub_C (kvs_attn, kvs_ctl, pvfin, ahub, seq core). d2d->hub 21 -> 18/20 cycles.
  The N-W IO-row corner (cols 0-2, 3.18 x 1.73 mm, 5.5 mm2) has no partition (IO row height = SerDes macro).
- PLL in hub_C; clock spine root = die centre [5408.64, 13003.2] (v2: sys_core, reach 31 mm).
- hg split outer (ectl + astk segment + heads 0,1) / inner hgi (heads 2,3, PV side), 1278.72 um each; the 7-mm hub
  split into hub_Wo/Wi/C/Ei/Eo; seq fans/xs beside their quadrant's astk ctl (hub_Wo/Eo). Centre band 604.8 ->
  838.08 um per row (hub E/W faces carry the kvs_ctl/host band trunks at <= 4.8 pins/um). Die 10817.28 x 27734.4.
- Clock insertion budget per type = 140 ps + 0.2 ps/um x half-perimeter (PLAN-TOOL CP1: 650 ps on a 1.4 x 3.7 mm
  partition), min 250; neighbour differences <= 80 ps except at the IO row.
- F_DLY from the compiler law 1 + D(pvp) + D(fin) + face_land_fin = 2 (v2's 1 was a fallback, see kv_params_v3.py).
- L1 cells (cells_v3.py; measured Yosys counts where a fleet run exists, else outline x class density): flattened
  hg 4.97 M / hgi 4.63 M / pv 6.99 M are dominated by replicated datapath leaves (lane8 113.9 k cells measured x 64,
  pv_slice_t estimated); without them every partition is <= 0.84 M (hub_C). See plan_report_v3.json l1_cells_per_type.

    python3 plan_v3.py --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out /tmp/stage1_v3.json.gz
    python3 emit_v3.py --stage1 /tmp/stage1_v3.json.gz --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out die_plan.json --report plan_report_v3.json
    T=<plan-tool>/tools/die_plan; python3 $T/gen.py latency die_plan.json --inplace --out gen; python3 $T/check.py die_plan.json --png
    python3 kv_params_v3.py /tmp/stage1_v3.json.gz > kv_params_v3.json
- L1 amended + CAP MEASURED (COORD 06:01 / 400k cells per run): l1_cores_v3.py -> l1_cores_v3.json. Partition = glue
  (<= 400k) + planned hard cores (<= 400k): hg 16 head-eighth cores (<= 383k, eighth 0 carries the ktree) + ectlk
  core, glue 220k; hgi 16 head-eighth, glue 68k; pv 16 PV-pair cores (388k est.) + 2 join cores, glue 388k;
  pc kvs_pc cores (glue <= 373k); hub_C ahub + kvs_ctl cores, glue 253k; hub_Wi host_rt core 403k (> 400k, < 500k
  ceiling: flagged); 1451 cores on the die. pv_slice_t / kvs_pc / ahub / host_rt counts are density estimates.
- G2 (g2_v3_report.json): die probe overflow 0, clk/rst reach max 17.7 / p90 15.1 mm; FT probes on the worst 5 types
  (hub_Ei, hgi_v3 = W corridor, hub_Eo, hub_Wo, hgi_v4) all EXIT 0, overflow 0, no pin without access, max layer use 21%.
