# HBM-CORE-LAT-R5 multi-clock types (ruling R4 (6)): one centre entry per INDEPENDENT clock

Plan: planU2 (epyc2:/srv/opentallas-scratch2/claude/hbm-mu-quad-2-1026/planU2, die_plan sha 55ea5ec620f5, clock_entries sha 7b158771e53a). Source: RTL headers + kit SDC generator + planU2 clock_entries.json (CHECKED by reading; no build).

| module | inst | clock ports | independent | generated | class | entry xy (um) |
|---|---|---|---|---|---|---|
| ot_hbm_sm_vm_wr_q_t_lanes4 | 2 | 6: clk clk_cal clk_l0 clk_l1 clk_l2 clk_l3 | 1 | 0 | SAME-CLOCK + SRAM early branch | [69.12, 194.4] |
| ot_hbm_svc_vm_kshare_splitstrap | 8 | 2: hbm_clk stream_clk | 1 | 0 | SAME-CLOCK (nominal 2-domain RTL; release die drives both from the one core clock) | [177.12, 224.64] |
| ot_hgi_coll_inj_idx_join_rg | 2 | 2: clk_r0 clk_r1 | 1 | 0 | SAME-CLOCK regional roots | [103.68, 155.52] |
| ot_hgi_sm_xload_cl2_bfqg | 16 | 20: clk clk_ctrl clk_l0 clk_l1 clk_l2 clk_l3 clk_l4 clk_l5 clk_l6 clk_l7 clk_m0 clk_m1 clk_m2 clk_m3 clk_m4 clk_m5 clk_m6 clk_m7 clk_n clk_s | 1 | 0 | SAME-CLOCK regional roots | [151.2, 146.88] |
| ot_hgi_sm_xload_cl2_ctlx | 2 | 2: clk clk_cal | 1 | 0 | SAME-CLOCK + SRAM early branch | [194.4, 194.4] |
| ot_hgi_sm_xload_xq_pegress | 4 | 5: clk clk_c clk_e clk_s clk_w | 1 | 0 | SAME-CLOCK regional roots | [185.76, 185.76] |

All 6 types have ONE independent clock (the die core clock) -> ONE centre entry each; 0 generated clocks. planU2 clock_entries.json already merges every clock port into one entry (port None, merged_clock_ports) -> consistent with ruling (6); the kit RTL wrapper must expose a single clk pin at that entry.

Flags:
- cl2_bfqg '20 domains' (R4 wording) = 20 local roots of one clock, not 20 domains (AGENTS one-core-clock rule holds).
- kshare_splitstrap carries an async Gray FIFO between hbm_clk and stream_clk although both are the same core clock on the release die (AGENTS: separate clocks only inside off-die PHY macros). Functionally safe; latency cost of the same-clock CDC FIFO = RTL-owner question (keep, or a synchronous variant behind an opt-in parameter). Legacy ref_tile SDCs with hbm_clk 1024 ps are not the release contract.
- clk_cal (wr_q lanes4, ctlx) is an early-phase entry for the SRAM (die 'phi - R'): with one entry it becomes an earlier in-core branch; the core's tree generator must support one early macro branch.
