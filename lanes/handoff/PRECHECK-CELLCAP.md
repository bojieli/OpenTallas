# PRECHECK-CELLCAP handoff (Opus 5.5, COORD 11-23 22:2x PST; one job: static per-soft-type cell projection incl. slot overhead)
## LANDED main 4047dc8142f
- tools/die_plan/adv_cell_budget.py (plan_advisory check CELL-BUDGET, WARN only) + test_adv_cell_budget.py (8 pass) + cell_budget_modules.json (measured content: types{ot_s81sl_kv_leaf__t2 385,667 / kvx 244,686}, modules{qkd_astk_ex_s 77,471}).
- est = max(content + slot, kit synth <72 h from precheck cells cache, type.cells on core-free types). slot = 2 cells/stage bit (ft_slots width x stations, internal_stations bits x regs, relay_depth bits x D; 1.15 if dly_alt_pol / OT_DLY_CPL / OT_ST_QNALT) + landings 5.0 x padded - 500 (min 660; narrow-ring small bands 20/bit + 60). Flag > 350k synth; place ~x1.28.
- Calib (t2 whole3 stat): stations 86,208/86,374, landings 183,940/186,608, whole 655,815/658,649, kvx 514,834/517,668. Slot-only: hg v1p5 -4.6% vs kit; QC fw -21% (u_lpad lane pads + pstn logic unmodeled), KV pv_v3 -47% (pd* pad chains) -> kit floor covers.
- Known gaps: lane pads (latency.lanes pad) and RTL pad chains not modeled; kit plan overhead not retained (kit = floor, no delta). Add measured contents to cell_budget_modules.json to sharpen.
## Runs (epyc11 /srv/opentallas-scratch2/claude/precheck-cellcap/{plans,tmp}; clone epyc10 .../precheck-cellcap/repo has pytest)
- S81 c8 ba9b277a852b 7 flags (t2 653k; c8 t2 has 0 hard_cores!), QC C1d c2856018af83 35 (sle_ctl 377k structural; st_b/hc kits), KV A4b 01311e0c5cce 14 (all pv; v1n 653k structural), HEAD r18g 0. Posted to owners 22:5x.
