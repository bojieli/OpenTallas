# d4f run3 over-reach: classification and the reset/config plan (H-DIE-R3, 2026-10-17)

Input: run3 GEN on EPYC4 `/srv/opentallas-scratch/claude/hdie-d4f/run3/case`. The GEN finished rc 0 in 47 min with a peak of 8.6 GB. It placed 1,414 instances and 826,998 nets with 0 placement problems. Contract 0a13e348c, plan r4, shared repeater step, `--hold-budget die`. manifest sha256 b8dca45d9d28afdc…, die.v 190a666fc7ed1ab3….
Tool: `tools/hbm_die_v15/d4f_overreach_plan.py CASE CONTRACT d4f_root_sites_r4.json`. Hop 405 um. A region is the nearest DIE-CLOCK r4 root site (36 sites). Data: `overreach_plan.json`.
The relay layer was not built. This is the plan only.

## Classification (net span = placed driver pin to farthest load pin, Manhattan, > 405 um)

| class | nets | what fixes it |
|---|---:|---|
| (a) relayed bus | 383,984 (382,731 bus + 1,253 status) | `die_relay_stations` registers them (p2p / equal_age_pad) |
| (b) reset | 7 nets (1,417 reset pins) | regional reset tree (below); the exporter skips `por_`/`rst` |
| (c) config/programme/control | 10,029 | registered copy / status chain (below) |
| (d) other | 54,813 | all are `hbfd_rly_*` outputs: existing contract relay hops > 405 um |
| **total** | **448,833** | longest: (a) 29.5 mm n90226, (b) 31.3 mm ckg_por_hbm, (c) 27.1 mm su_prog.command |

Top (a) drivers by bits: sm_group_id.sm_packet 17,584; xq_pegress.xw_data 16,384; vm_kshare.fill_data 16,384; wb_kport.w_k_wdata 16,384; sfu_lg_pair_leaf.lg_wq 14,050 / c_rr 11,154; vm_lg_static_bank.local_rr 10,020; vm_kshare.c_k_wdata 9,827; pc_ctrl_leaf_cfg_h9b.kr_data 9,441; hc_q_static.lg_wq 8,992; sfu_programme_store.compiler_control 6,968.

(d) has 236 of the 928 relay tiles. The worst are the 16 chain ends `rfr_<Q>_<Q'>_35` (48_WE/EW, 41 b), which reach `ot_hbm_su_static_qcore` 5.5 to 12.6 mm away. The rfr chains still end at the old q-core geometry, but r4 moved the core beside the hub. The chains must be re-planned to the r4 core site, not padded. The other 220 are `sfr_*` 624-bit and `rfr_*` interior hops of 0.4 to 2.3 mm, where a "planned relay home" landed far from its route point. die_case must re-legalise them on the station grid (the relay layer re-run handles these).

## (b) Regional reset tree: 7 driver nets, 1,417 pins

The rule is the die standard's regional reset: a registered reset per region, pipelined from the source, with the same release cycle in every region (static schedule). The reset is not distributed today. The manifest says `hb_ckgen/por_<domain> straight to every reset pin (false path)`.

| source (hb_ckgen at 19,620/18,332) | pins | regions (r4 sites) | release depth (hops) | trunk stages (tree / 405) | regional reset relays |
|---|---:|---:|---:|---:|---:|
| por_stream | 693 | 35 (all except 1) | 76 | ≤279 | 35 |
| por_serial | 602 | 19 (bands + sm_NW4/7, SW4-7, ecol_SE) | 65 | ≤178 | 19 |
| por_hbm | 102 | 6 (pc_NWa/b, pc_SWa/b, band_NW2, sm_SW6) | 77 | ≤130 | 6 |
| subr_NE.bridge_rst_n | 5 | 3 (band_NE0-2) | 19 | ≤37 | 3 |
| subr_NW.bridge_rst_n | 5 | 4 (band_NW0, sm_NW2/4/6) | 19 | ≤41 | 4 |
| subr_SE.bridge_rst_n | 5 | 3 (band_SE0-2) | 20 | ≤37 | 3 |
| subr_SW.bridge_rst_n | 5 | 4 (band_SW0/1, sm_SW4/6) | 22 | ≤46 | 4 |
| **total** | 1,417 | | | **≤748** | **74** |

Build (H-NETLIST cell, DIE-CLOCK placement):
1. One reset relay per (domain, region), 74 in all. Each is a 1-bit flop in that domain's regional clock. It sits inside the region root site's 60x60 keepout, beside the regional root buffer, so the reset and the clock leave from the same point. The local reset buffer tree runs from it to the pins in the region (repeaters, max wire 175 um).
2. The trunk runs from hb_ckgen to each region site along the DIE-CLOCK regional tree, with one registered 1-bit stage every 405 um in the source domain. The three por domains share the routing corridor. Use one 48-bit relay tile per stage, with 3 bits used, where all three domains share a stage point. A per-domain flop is not needed if the tile carries per-bit clocks; otherwise use three 1-bit stages.
   - The ≤748 above is the Prim-tree upper bound. Sharing the clock-tree corridor brings it to about 400.
3. Equal release: each region's relay is padded so that release lands at the domain's max depth: stream 76, serial 65, hbm 77, bridges 19 to 22 cycles. The compiler adds these as fixed reset-to-start cycles. Assertion may stay asynchronous (false path); deassertion is the registered, timed path.
4. bridge_rst_n: subr_<Q> is a generated 22 um home at the peer centroid. Instead, put one subr copy per band region (3 to 4 each, 14 in all). Each copy is a registered copy of the SU bridge release, fed from the band's SU programme slice. That removes the 4 trees.

## (c) Config, programme and control: 10,029 nets

| group | nets | now | plan |
|---|---:|---|---|
| su_prog.command (ot_hbm_su_programme to 24 pgslices, 16 regions) | 9,688 | monolithic su_prog in a generated 1,241 um home at 18,036/23,247; span 27 mm; the exporter skips it as "superseded" | **Contract switch to the partitioned SU programme** (H-SU b82db77f9, pslice slots 92282bfcb). There is one programme slice per pgslice region (16 band regions: band_NE0-2, NW0/2, SE0-2, SW0-2, and sm_NW2/4-6, SW6), which is the registered local copy. It is filled at load time over the host cfg chain. Relaying the monolithic store would cost about 9,688 x 141 stages, or about 1.37 M flops, so that is not an option. Owner: H-NETLIST + H-SU, contract after 0a13e348c. |
| host_cp_ingress cfg_data/addr/target/v + desc_base/limit/loops/v (to 60-67 sinks, 20 regions) | 319 | host_cp_ingress at 14,197/16,022 (generated home); depth 57 | Registered config chain, which is the exporter's `cfg_no_pad` class (addressed writes, no equal-age pads). One 624-bit stage carries all 319 bits. There is one stage every 405 um along the tree (≤205 stages) and one config copy register per region (20) that drives that region's sinks. This is load-time traffic, not on the hot path. |
| 1-bit program/status returns: su_prog.done/fault/valid/busy, hb_coll_<Q>.program_configured/fault, hc_<Q>/hc_eng/hb_quant_NW.program_active | 20 | spans 4.4 to 19.3 mm to the host status join (band_NE2) | Registered status chain into host_status: 1-bit flops every 405 um, 444 stages in all. These are quasi-static, so a 48-bit relay tile should carry several returns that share a corridor (the hc_<Q> and coll_<Q> pairs share the hub column). |
| sfup_<Q>.programme_active | 4 | 1.0 to 1.7 mm, caused by the sfup OVERFLOW misfit below | No relay. Fix the slot (r5 sfus programme-store slot). Expect ≤405 um after the refit. |

Totals for (c), excluding su_prog.command: 341 nets, about 205 config stages (624-bit), 20 regional config copies, and 444 1-bit status stages.

## GEN placement misfits and empty regions on link paths (run3 layout.png)

- **Region OVERFLOW (red):**
  - sfup_NW/NE/SE/SW: the programme store is 602x603, but the r4 sfus_<Q> slot does not hold it. r5 grants a 447x1024 slot, but run3 ran r4.
  - wbk_NW/SW: hb_dbk_<Q> is full. wbk_NW sits at 15,633/22,237, and its 1,148-bit buses to vmks_NW2-7 in the PC band run 9 to 15 mm.
  - hb_argmax: OWNER-BLOCK MISFIT, 107x107 fits no IDX block.
- **Generated homes (purple) on link paths:**
  - su_prog: 1,241 sq at 18,036/23,247, E of sm_NW7. It disappears with the partitioned programme.
  - host_cp_ingress, host_status and epcal_<Q>: cluster at about 14,200/16,000, the hub centre.
  - xl_<Q>_ctl and aq_tree13 x4: at sm row edges, y 8,748 and 23,200.
  - subr_<Q>, cic_<Q>, col_*.
- **Pitch misfit:** svg_<Q>0-7 (sm_group_id) sit in the PC band at a 1,137 um pitch, but the SMs are at a 2,040 um pitch. sm_packet (1,182 b each) therefore runs 2 to 5.7 mm laterally: svg_SW0 at x 5,774 to sm_SW0 at x 42, and svg_SW7 to sm_SW7 at x 16,080. That is the largest (a) driver, 17,584 nets. Re-pitch the svg boxes under their SMs, or put svg at the SM front.
- **Excluded:** vmb_NE0-7, vmb_SE0-7 (hfd_vms_bank_native_q1_core_pr view not built) and tkm_SW (tkm_m_tp192 not built). 2,518 b each, plus 2,913 b, are dropped edges, so the E-half bank traffic is missing from this census.
- **Empty regions with over-reach traffic** (1 mm grid, <5% covered):
  - E hub channel x 14-18 mm, y 9-23 mm (29 mm², 231 k bit-crossings): wb_kport/q0_faces at 14/9 and 14/22, cxport/lg_pair at 14-15/13 and /18, host ingress at 15/16.
  - NE corner x 14-23, y 23-33 (52 mm², 130 k) and SE corner x 14-23, y 0-9 (52 mm², 228 k): vm_kshare.fill_data to vmdel_lane (17,920 bit-pairs) and smh_attn.rdata to sm_vm_wr_q_t (4,336) run vertically along x 18 between the PC bands and the hub, and sm_group_id runs along y 1.
  - The corners are where the excluded vmb_NE/SE plus spare area sit. The relay stations for the x 18 and y 1 trunks should be homed there. Moving vm_kshare's consumer next to its producer is preferable (placement-quality item, as in run1).
