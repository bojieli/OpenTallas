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

## v3.1 (KV-P2, 10-23) -- die_plan.json is now v3.1 (v3 at 9292db97f)

COORD 06:33 open items + census coverage (scripts plan_v31.py / emit_v31.py / coverage_v31.py / l1_cores_v31.py):
- IO row 1728 -> 1036.8 um, one clock tap per IO partition (each <= 1900.8 um wide): sys_SW | io_W2 | io_W3 | sys_c |
  io_E5 | io_E6 | sys_SE.  The x12 host SerDes is MIRRORED as two x6 halves (0.30 mm2/lane kept, 1.81 mm2 each, same
  223-cycle latency; flit striped 522 W / 521 E, tx_v broadcast, tx_up / rx_v AND-joined): the empty N-W corner is gone,
  die 27734.4 -> 27043.2 um tall (-7.5 mm2).  sys_c (col 4) = UCIe + d2d + fwd/clk bumps + dcal; io_W3 / io_E5 = the
  corridor heads (d2d/SerDes <-> hub_Wi, d2d <-> hub_Ei/hub_C); io_W2 / io_E6 = SerDes-half feedthrough cells.
- Host core: qkd_host_rt was a 403k density estimate; the HOST root is MEASURED 784k hier / 571k flat and already splits
  exactly into the qkd_hr_cluster children (gen_cluster.py, lockstep-proven) -> 22 planned cores in hub_Wi, max 97k
  (l1_cores_v31.json; no core or glue over the 400k cap on the die).
- Census coverage (coverage_v31.json, COORD G1 rule): as-built inter-partition bits 412,179; planned 379,407 tree +
  32,772 gather-chain; DROPPED 0.  Spine-replaced, listed by source: reset host.die_rst_n 5,760 b (the reset spine
  root must be driven by host.die_rst_n); clock pll core taps 9,126 b + NON-CORE clocks pll_hbm_{WS,WN,ES,EN} 168 b,
  pll_phy/host/ingest/fwd 21 b (OPEN: the plan has one clk_core spine; the HBM and host-family clocks need their own
  spines/taps).  Fixed vs v3: (1) extract_asbuilt counted the mixed-direction FDI bundles host.fdi (2,089 b) and
  d2d_kv.fdi (1,169 b) as 1-2 bits (+4,878 b now carried); (2) v3 dropped 512 b of narrow port families (phy fh#/rh#:
  family offset keyed on destination count, members to one partition collided); (3) the host's sequenced functional
  resets hbm_rst_n / host_rst_n / link_rst_n (432 b) are control lanes, not the reset spine; (4) pll.locked is data.
- Pins: windows sized for the plan-tool PG-band exclusion (5c83c4b9a/2bb9e12ba); an odd-count layer gets an odd usable
  track count and a tie-free centre, so replicas share one pin table (tools/die_plan/schema.spread now exact arithmetic).

    python3 plan_v31.py --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out /tmp/stage1_v31.json.gz
    python3 emit_v31.py --stage1 /tmp/stage1_v31.json.gz --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out die_plan.json --report plan_report_v31.json
    T=<plan-tool>/tools/die_plan; python3 $T/gen.py latency die_plan.json --inplace --out gen; python3 $T/check.py die_plan.json --png
    python3 coverage_v31.py /tmp/stage1_v31.json.gz asbuilt_rtl6_e33504a6f.json.gz die_plan.json > coverage_v31.json
    python3 kv_params_v3.py /tmp/stage1_v31.json.gz > kv_params_v31.json
    python3 l1_cores_v31.py /tmp/stage1_v31.json.gz asbuilt_rtl6_e33504a6f.json.gz plan_report_v31.json > l1_cores_v31.json
- Generated-die blockers (bind/bitcon.py = bit-level as-built die.v connectivity with LSB-first port directions;
  bind/blockers.py -> bind/blockers_v31.json): the plan declares no leaf bindings yet; as built, 13,082 leaf-input bits
  (41 ports: lane8 bsel, astk ep zi/xi, owner prev_*, frontq hid, kvs_pc pc__pc/cfg_stack, hslice chain ends ...) are
  undriven straps that the GEN tie-cell pass turns into TIEHI/TIELO -> leaf parameters first; 356 fault-OR inputs come
  from landing cells the plan removes; 128 qkd_rlyi_258s MUX relays (the PV result T-chain behind the 8 RH gathers) were
  collapsed as pass cells by extract_asbuilt (so the census above counts the gathers as wires, not as select stages);
  8 non-core clocks and the reset root (host.die_rst_n) have no plan spine.
- 10-23 tip re-emit (plan-tool @5dd34afa0, uniform spreader + PG-band windows + mandatory census): die_plan.json is
  unchanged except the new `census` key (census_rows_v31.py -> census/; 2,849 rows, gathers as qkd_rlyi_258s T-chain
  hops). G0 on the tip checker: 0 pin/abutment errors; census_cov reports 51,031 b "dropped" over 264 pairs, ALL of
  them tap-tree destinations reached through forwarding partitions (hub_Eo -> hg_EN_7 -> ... -> hg_EN_0): census_cov
  credits only lane END pairs and a tap tree is a chain of per-hop lanes (census/census_taptree_v31.json: 0 b not
  carried by a tree). Needs a census_cov rule for forwarded lanes (PLAN-TOOL), not a plan change.
- G2 (g2_v31_report.json): die probe + FT probes of the 5 worst types and all IO types: every probe EXIT 0, GRT overflow 0
  (max layer use 21 %, hub_Ei M2).
- F_DLY: the plan law gives 2, but the bit-exact bench (kv_params_v31.json F_DLY_bench) fails at T8191/T8192 with 2;
  the schedule keeps F_DLY 3 until new root/stack RTL.

## v3.7s (KV-P6-SPINE, 10-23) -- north spine balance (COORD DIE-PLAN VISUAL REVIEW)

`post_v37s.py` (appended to run_v37c.sh; lanes / ports / ft_slots only, never hard_cores): serdes_E.rx_flit (L2045,
522 b) leaves the IO row at io_E5 and runs down the E corridor (hgi_EN_0..7), W along the pv_N_7 bottom band and into
hub_Wi through hgi_WN_7, instead of W along the IO row (sys_c, io_W3) and down the W corridor. Same 12 crossings, 36
stages (R8 phy_rx_flit alignment with L2048 kept), latency table unchanged, route 18.3 -> 16.9 mm. North W corridor
65 % -> 57 % of the IO-row <-> hub bits, E 33 % -> 42 % (g2_columns_v37s_report.json). No other move is cycle-neutral.

## v3.8u (KVG3-WI, 10-24) -- hub_Wi host-root core pins (G0C 'no pins listed' x22)

`run_v38u.sh V38S_PLAN OUT RTL KIT_RTL_F` = `core_pins_hr.py` + `post_v38u.py`; touches only
`partition_types.kv3_hub_Wi.hard_cores[].{pins_file, orient, note}` and `core_conns.json[kv3_hub_Wi]` (die_plan.json
regenerated in place: a pure superset, 22 pins_file + 22 notes + 5 orients; no lane / latency change).
- The 22 cores (15 modules) are children of the host-root cluster plan
  (`results/arch/qwen_split_1014/host_root_cluster/partition_plan.json`) INSIDE the hub_Wi leaf `host` = bound `u_host`
  (`qkd_host_root_admission_obsx`, binder kv41, RTL e33504a6f).  core_pins_v37p logic one level deeper: the leaf is
  elaborated hierarchically with yosys (kit filelist, -DSYNTHESIS, the u_host parameters, proc, no flatten; a scratch
  copy of the obsx file hoists its forward-used g_mu net declarations, a reading aid only), member paths are mapped onto
  the obsx hierarchy (`g_mu.` scopes), boundary bits = member port bits whose net leaves the core; partners = other cores,
  host-leaf ports -> their partition partners (bus windows; glue leaf / ot_dp_st / ot_dp_dly one hop), glue cells up to
  3 deep (<= 8 targets).  Faces / orients / spread = v37p choose() / balance() / plan tracks.
- **Glue rule**: a core = ONLY its real instance members.  The `glue:*` members (qm_core / qm_host / qm_ingest /
  fence_core / fence_host / fence_sync = the A1/A2 re-cut of native_qm and visibility_fence own logic) do not exist in the
  bound RTL and stay hub_Wi partition glue, as do the instances no child lists (`u_rank/u_fence`, the `u_qm` reset syncs
  and own logic, obsx-only `u_control/u_obs`, `u_control/u_hc`).  Every core stays derivable from the bound RTL and
  hardenable without an RTL re-cut; no child is empty (host_qm = u_bridge/u_pacer only, 10 pins).  All 38 real member instances
  (8 adapter slices included) exist (0 missing); `core_pins_hr_report.json` lists the mapping.
- Pins: ingest_eng 1399, core_order 2286, cdc_ch 1208, cdc_pc 2168, core_peer 3849, core_tx 3772, core_rx 2137,
  core_guard 1176, core_queue 1472, core_prompt 5131, cdc_hi 1177, cdc_ci 1106, phy_pad 1577, phy_adp 560 (x8, MX/MY
  per instance), host_qm 10.  core_faces: 567 new groups, 0 away, 0 side-WARN, per-core mean cos +0.73..+1.00 (v38u_Wi.png).
  Ports whose partners are only the native_qm / fence glue (cdc_hi 659, cdc_ci 812, cdc_ch 584 bits) have no positioned
  partner and face the type centre.
- G0 PASS 0 err / 1788 warn (v3.8s 0 / 1811); G0C PASS 0 err (v3.8s FAIL 22), 49/49 types clean (g0_summary_v38u.json).
