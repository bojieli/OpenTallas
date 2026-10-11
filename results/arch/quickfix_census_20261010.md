# Quick-fix census of open elements, 2026-10-10 (quickfix-1010)

The owner asked for this census at about 22:30 on 2026-10-10, with the rule to use the easiest deterministic fix instead of iterating. Sources: the element registry (`127.0.0.1:8765/api/elements`, via `gaps/registry_gaps.py`: 70 open, 7 idle), the closure-loop job state, `results/arch/hardcore_fallbacks_20261010/feasibility_all.md`, and the stream logs as of 21:45 PT.

Each open element is in exactly one class:

| class | meaning |
|---|---|
| Q1 | hold-only miss with setup room: a hold ECO or a delay stage at the failing inputs |
| Q2 | small setup miss on a few path classes: pin flops, one added register, or LVT on at most 2% of cells |
| Q3 | flow, spec or lint failure: pins, PDN, benches, pin regions |
| S-live | structural redesign in progress with a live owner |
| S-none | structural problem with no redesign started |
| in flight | first trial, no routed verdict yet |

## Counts

| class | elements |
|---|---:|
| Q1 | 7 |
| Q2 | 11 |
| Q3 | 6 |
| S-live | 37 |
| S-none | 1 |
| in flight | 8 |
| **total** | **70** |

## Part A: attention banks (H1 hold IO)

`ot_attn_bank_{ew136,sn136,ew544,sn544}` (jobs `hbm_attn_bank_*-8c71cbcf7-tc-iotime-h1-cl`) **CLOSED** before a delay stage was needed. The post-route hold ECO at `max_buffer_percent` 100 (the 30% cap had hit RSZ-0060) closed all four between 21:27 and 21:33, with the H1 hold IO unchanged (input min = sender clk->q, 30 ps):

| bank | TT setup (ps) | FF hold (ps) | DRC | cells added (ew136) | record |
|---|---:|---:|---:|---|---|
| ew136 | +430.30 | +34.14 | 0 | 372 | main 8f630f612 |
| sn136 | +430.14 | +34.88 | 0 | | main 9131e3c08 |
| ew544 | +408.06 | +32.74 | 0 | | main e0e1ba560 |
| sn544 | +410.58 | +32.44 | 0 | | main 578b2f20a |

The ECO inserted hold buffers on the `d` -> pin-flop paths: 136 of 136 endpoints were classed fixable, with a setup window of +590 ps. No constraint was changed. A dont-touch delay-cell stage in the RTL was not built, because the ECO won the race.

## Fixes submitted by this census

| element | class | defect | fix | jobs (branch `claude/quickfix-1010`) |
|---|---|---|---|---|
| dsfd_coll_p2_lane_ba | Q2 | `mtpl-*-0ddaf548b`: TT -140.46 / FF +7.75. All 1,712 failing endpoints are one input class: `r_r` -> `o_free` -> `li_ready` -> the link receiver's OREG plus the 604-b output-register enables, 13 to 15 levels. Reg-to-reg is +168. | The DIRECT output stage becomes an `ot_s81ph_skid2` (registered ready; `r_v`/`r_d` still come from flops). It is opt-in `RSKID=1` on the `_ba` wrapper only. 0 added cycles, transaction-exact; `pa` and the generic default are unchanged. Gate `tools/mtp_p2lane_gate.py` PASS on d9fbc9948: p2l_s1 and p2l_s5 exact (27,007 cycles against 27,020 at base); the neg_seg, neg_cred, neg_hol and neg_lat1 mutants FAIL as required. | `qf-p2lba-rskid-d9fbc9948-tc-{hm0-a,hm10-b}` (branch `claude/quickfix-1010-p2`, on 0ddaf548b) |
| dsfd_coll_mtp_lane | Q3 | Both `mtpl-*-0ddaf548b` routes crash at 6_report with PSM-0069: the two `g_m2` SRAM macros have VDD unconnected. | Add `ot_sram_1r1w_128x256_m1_r2c2` to the `pdn_coll.tcl` macro grid (M4 PG, the same as the listed macros). RTL, benches and constraints are unchanged. bench_exact_hol_mtpl PASS. | `qf-mtpl-pdn-0cd3d2b9c-tc-{hm0-a,hm10-b}` (branch `claude/quickfix-1010`) |

**Main drift found:** `tools/mtp_p2lane_gate.py` p2l_s1 FAILS on origin/main (tb_mtp_p2_lanes.sv:130, metadata row 11, word 13) and PASSES at 0ddaf548b with the same tool. Of the gate-source commits in between, b69100081 (dsfd_coll_p2_ep core ports on ltx_rc, mtp-fixlat-1011) is the functional suspect. It was reported to mtp-fixlat-1011 and mtp-colllane-1011. The p2_lane_ba fix is therefore based on 0ddaf548b.

**Skipped by rule:** `ot_hgi_su_ctlw` is Q3 (a bench gap: MUT_DIRTY is equivalent on the production vectors). The fix was named in hgi-1010.log at 21:29, less than 30 minutes earlier: add an unaligned-sink case to `su_prod_vec.py`, then re-route. It stays with hgi-1010/b.

## S-none: structural problems with no redesign started

- **ot_hbm_tu_retry_phy_port** (HBM accelerator; 12 fails; no live job):
  - Defect: f63e6e650-a reaches TT -112.3 / FF -3.87. Two classes fail:
    - the output-port class: `pclk` reaches the boundary flops through a 22-level CTS chain, with 660-703 ps of insertion;
    - reg2reg -34 on the `credits`/`available[]` compare, 25 levels.
  - Proposed fix:
    - drive the output pins from pin flops on a short, ungated `pclk` branch (or their own boundary root), so that the boundary insertion matches the IO reference;
    - register the `available` bit: +1 cycle on the credit loop, absorbed by one extra credit of depth and priced in the model.

## Per-element table

Best TT/FF/DRC is the registry's best routed verdict. Under "Live line", "owner applied" means the owner is already running the simple fix for that class.

| target | element | class | best TT / FF / DRC | failing class / evidence | live line (owner) |
|---|---|---|---|---|---|
| DeepSeek ROM | ot_dsrom_window_source_ctl | Q1 | +79.27 / -7.63 / +0.00 | TT +79.27 / FF -7.63 hold-only; pin-root + reset-tree fixes live | owner applied: s81b-wsrc-pinroot-36250138e / rsttree-814548a2d (ds-1010) |
| DeepSeek ROM | ot_mtp_p2_prefix_path | Q1 | +9.66 / -25.69 / +0.00 | TT +9.66 / FF -25.69, R2O output hold vs H1 | owner applied: IOREF_VCLK root fix rb4v-a978bdba9-hm{10,20} + KEEPWIRES hold ECO (fe-push-ds / mtp-fixlat) |
| DeepSeek ROM | ot_s81_bf_front | Q1 | +97.56 / - / +0.00 | TT +83..+95 / FF -1.7..-14.3 | owner applied: hold ECOs on bfh_compact{199,220} (bf-hier-1011) |
| HBM accelerator | hfd_vm_ne_w | Q1 | +41.45 / -4.70 / +0.00 | TT +41.45 / FF -4.70 | owner applied: hold ECO on vm8bfq_new lvt-ttfix (hbm-phys-vm8) |
| Qwen ROM | qfd_coll_xfifo_l8 | Q1 | +0.74 / -2.90 / +0.00 | TT +0.74 / FF -2.90 | owner applied: hold ECO l8q_a-a3ede03cb-f9a |
| Qwen ROM | qfd_coll_xfifo_l8_b | Q1 | +22.38 / -12.37 / +0.00 | TT +22.38 / FF -12.37 | owner applied: hold ECO l8q_b-a3ede03cb-f9a |
| Qwen ROM | qfd_sp_band_lanes | Q1 | +61.55 / -7.23 / +0.00 | TT +61.55 / FF -7.23 | owner applied: hold ECO on 331227e92 lvt-ttfix |
| DeepSeek ROM | dsfd_coll_ct | Q2 | -46.70 / -13.24 / +0.00 | relay pointer fanout; fix live | owner applied: RSL relay-pointer replication coll_ct-fe-34c4ded32-rsl (rslps -56.65/-6.17), split3crpd |
| DeepSeek ROM | dsfd_coll_p2_ep | Q2 | -64.76 / +1.58 / +0.00 | TT -64.76 / FF +1.58 | mtp-fixlat-1011: fixlat-collp2-b69100081 running |
| DeepSeek ROM | dsfd_coll_p2_lane_ba | Q2 | -140.46 / +7.75 / +0.00 | single input class r_r -> li_ready -> 604-b enables (13-15 lv, 1,712 ep); reg2reg +168 -> registered-ready output skid, 0 cyc | quickfix-1010 SUBMITTED qf-p2lba-rskid-d9fbc9948-tc-{hm0-a,hm10-b} (gate PASS) |
| DeepSeek ROM | dsfd_selt_q2 | Q2 | -11.32 / -7.33 / +0.00 | TT -11.32 / FF -7.33 | owner applied: combo ECO (VT<=2% + hold) frprck4a, frprck4b route (ds-1010) |
| HBM accelerator | ot_gpu_rf_visibility_fence_p | Q2 | -44.39 / -4.10 / +0.00 | TT -44.39 / FF -4.10 | owner applied: combo ECO mtp-fence-fb-93f2ee279-lvt (hgi-1010) |
| HBM accelerator | ot_ha2_truecredit_rx_s_phys | Q2 | -25.81 / +2.48 / +0.00 | TT -34.23 / FF -10.12 (best -25.81 / +2.48) | owner applied: combo ECO ha2_rxs_cplr-5887a9663-hm10 (hbm-phys-1010) |
| HBM accelerator | ot_hcoll_port | Q2 | -25.67 / -13.58 / +0.00 | TT -25.67 / FF -13.58 | owner applied: hcoll-port-rfetch-c26cc6a77-f9{a,b} (hgi-1010) |
| Qwen ROM | ot_qkvd_rom_end | Q2 | +1.85 / -2.36 / +0.00 | best TT +1.85 / FF -2.36; hold ECO on 76k ep stalled | owner applied: combo ECO qfd_d2d_rom_b-4b7c66f54 + route df9afb422 (qwen-1010) |
| Qwen ROM | ot_qwen_nearhbm_attn_hub_p | Q2 | -1.67 / -25.11 / +0.00 | TT -1.67 / FF -25.11, 3,857 hold pins on adder cut hops | owner applied: combo ECO ahub_b + ANR adder fe lines qkd_ahub-fe{a,b}-5736e945a |
| Qwen ROM | qfd_io_collective | Q2 | -32.89 / -9.49 / +0.00 | TT -32.89 / FF -9.49 (VT pass TT +10.15) | owner applied: hold ECO on VT-swap pass + pr2q/pr2_pf-7f5522d03 |
| Qwen ROM | qfd_tile_e | Q2 | -37.31 / -24.04 / +0.00 | TT -37.31 / FF -24.04 | owner applied: rpxd-4ac3b982f (+2 cyc), fba-0ef4d7781 |
| DeepSeek ROM | dsfd_coll_mtp_lane | Q3 | - / - / - | PSM-0069: 128x256_m1 SRAM missing from pdn_coll.tcl macro grid (VDD open); owner retries re-crash | quickfix-1010 SUBMITTED qf-mtpl-pdn-0cd3d2b9c-tc-{hm0-a,hm10-b} |
| DeepSeek ROM | ot_hdc_v41x_idx_chunk_el | Q3 | - / - / - | bench lockstep expectation mismatch on 31bb503d2 | owner applied: hgi-idx-chunk-{a,b}-9473077de (hgi-1010) |
| HBM accelerator | hfd_sfu_tile | Q3 | - / - / - | 5,534/5,535 IO pins off-track on 18d5bc494 | owner applied: hbm_sfu_tile-238dfb802-tc-hm{0,10} (on-grid pins) |
| HBM accelerator | ot_hgi_cp_mtp_pinreg | Q3 | - / - / - | bench_P_system_positive rc=1 | owner applied: hgi_cp_mtp_pinreg-a-7d9c1b45e-r2 (fe-push-hgi) |
| HBM accelerator | ot_hgi_su_ctlw | Q3 | - / - / - | bench gap: MUT_DIRTY equivalent on the production vectors | NOT applied; SKIPPED by rule (fix named in hgi-1010.log 21:29 by idle-sweep -> b): add unaligned-sink case to su_prod_vec.py, re-route with mut_dirty expected FAIL |
| Qwen ROM | qfd_sp_vector_memory | Q3 | - / - / - | bench_vm_mutant did not FAIL (bench gap) | owner applied: fp{a,b}-be0c13ba6 (qwen-1010) |
| DeepSeek ROM | dsfd_coll_cb | S-live | -232.21 / -11.50 / +0.00 | credit-relay pointer drives ~4k loads | ds-1010 + hardcore RSL (8 replicated relay pointers, 0 cyc): coll_cb-fe-34c4ded32-rsltrep, split3crpv |
| DeepSeek ROM | dsfd_coll_ce | S-live | - / - / - | PULL / reset-tree restructure | ds-1010: split3crpr-f1d9b22e2 (RSTR+PCOPY) + split3crplf |
| DeepSeek ROM | dsfd_p2_lnk | S-live | - / - / - | first fixed-latency route in flight | mtp-fixlat-1011: fixlat-p2lnk-ffbec0c86 (+9 cyc) |
| DeepSeek ROM | dsrom_mtp_head_full340_A | S-live | - / - / - | 700-um single-cycle wires, 6-um macro gaps | mtp-wfc-1010 / fe-push-ds: mkdrv-hbr / mkglue-bn-d781e7cb0 |
| DeepSeek ROM | ot_v41_bf_col | S-live | +34.26 / - / +0.00 | compact hierarchical full-rate BF | bf-hier-1011: bfh_compact{199,220,242}_col routes (revoked rows = evidence only) |
| DeepSeek ROM | ot_v41_pqc_spine_screen | S-live | - / -76.95 / +0.00 | FF -76.95; fixed-latency VM read across stations | ds-1010: s81fs-h1-{r128x550,r16u35}-f3fddfb0b |
| HBM accelerator | hfd_attn_half_hi | S-live | - / - / - | GRT congestion on port nets over bank OBS (v2g moves pin banks) | hbm-phys-1010 [att]: v2g-d4bae12ea-r2, cgvalid-d34009fe2 |
| HBM accelerator | hfd_attn_half_lo | S-live | - / - / - | as hi; first GRT > 3.5 h | hbm-phys-1010 [att]: v2g-d4bae12ea, cgvalid-d34009fe2 |
| HBM accelerator | hfd_coll | S-live | - / - / - | SRAM sliver 6 um, CTS segfault | hbm-phys-1010: hfd_coll_r25gq-aa1cd767a; re-cut (PHY packer -> hfd_lk_ep) |
| HBM accelerator | hfd_hc | S-live | -214.53 / -17.72 / +0.00 | TT -1,633 post-CTS: cloned ICGs (1.1 ns ENA wire), IO flops behind gated trees | hbm-phys-1010 [cg] lead 21:29/21:32 APPROVED one HC successor (IO flops on ungated root + lockups, ICG+ENREG no clone); NO job yet |
| HBM accelerator | hfd_idx_score | S-live | - / - / - | 512 FP32 adders flat; T4 bench timeouts | hgi-1010 g2: 8-head chunk harden; tap -r2 held until T4 bench passes |
| HBM accelerator | hfd_lk_ep | S-live | - / - / - | PREROUTE -4,178: serial 583-deep CRC loop | hbm-phys-1010 [link]: hfd_lk_ep-304cd8c93 (ot_crc_par balanced CRC-14) |
| HBM accelerator | hfd_sfu | S-live | - / - / - | flat quarter -2,117 post-place | hbm-phys-1010 [sfu]: superseded by 16 x hfd_sfu_tile; quarter waits on the tile view |
| HBM accelerator | hfd_su_tile | S-live | - / - / - | GRT-0116 in 100-um strip | hbm-phys-1010 [su]: hfd_su_tile_xl ongrid-pdnh-4f0925af4 + hardcore sw147 strip |
| HBM accelerator | hfd_vm_ne_e | S-live | -106.01 / -31.38 / +0.00 | rvt TT -61.8 / FF -29.8 DRC 1; I2O feedthrough hold stall (7 ep) + N-S face 13.9 b/um | hbm-phys-1010 [vm8]: hbm_vm8bfq_nee-lvt-cl-ttfix |
| HBM accelerator | hfd_vm_nw_e | S-live | +19.19 / -4.36 / +1.00 | TT +19.19 / FF -4.36 / DRC 1 | hbm-phys-vm8: vm8bfq_nwe lvt-cl-ttfix |
| HBM accelerator | hfd_vm_nw_w | S-live | - / - / - | no verdict on bfq yet | hbm-phys-1010 [vm8]: vm8bfq_nww rvt + lvt-ttfix |
| HBM accelerator | hfd_vm_se_e | S-live | -258.15 / -32.81 / +1.00 | rvt TT -258 / FF -50 DRC 1; I2O hold stall | hbm-phys-1010 [vm8]: vm8vt_see / vm8bfq_see lvt-ttfix |
| HBM accelerator | hfd_vm_se_w | S-live | - / - / - | slice macro gaps widened (328df2a09) | hbm-phys-1010 [vm8]: vm8bfq_sew rvt + lvt-ttfix |
| HBM accelerator | hfd_vm_sw_e | S-live | - / - / - | no verdict on bfq yet | hbm-phys-1010 [vm8]: vm8bfq_swe rvt + lvt-ttfix |
| HBM accelerator | hfd_vm_sw_w | S-live | - / - / - | W face 7.82 b/um | hbm-phys-1010 [vm8]: vm8bfq_sww rvt + lvt-r2-ttfix |
| HBM accelerator | hgi_idx_topk_full | S-live | - / - / - | 2048-way select -> heap | hgi-1010 g: hgi-idx-topk-heap-{a,b}-9473077de |
| HBM accelerator | ot_hbm_accel_smh_front_c | S-live | - / - / - | CTS hold flood -258 (IO reference) | hbm-phys-1010 [cg]: front_c_i8ob-eeadfce8f-iovclk2 |
| HBM accelerator | ot_hbm_accel_smh_tile_eg | S-live | - / - / - | 110k hold ep at SRAM pins (macro clock late) | fe-push-hphys / [cg]: enreg-xlk 4362cee96 / drst-rr c7ac635fa |
| HBM accelerator | ot_hbm_accel_smh_tile_wg | S-live | - / - / - | as eg | hbm-phys-1010 [cg]: enreg-xlk pd55/pd60 r2, drst-rr |
| HBM accelerator | ot_hbm_native_frame_station_rb_NO3 | S-live | - / -35.58 / +0.00 | FF -35.6; floorplan margin | hgi-1010: NO3 SAFE/HALF variants (latest stpin-w700 FLOORPLAN_MARGIN) |
| HBM accelerator | ot_hbm_native_frame_station_rb_NO3_split | S-live | - / -36.33 / +0.00 | fallback only | hardcore fallback (2 x NO2 SAFE in series) failed -297.7 / -36.3; main NO3 line above |
| HBM accelerator | ot_hbm_norm_engine_view | S-live | - / - / - | N-face 17 b/um, 1-stage capture > 504 um | fe-push-hgi-1010: rlyx-pm1400{a,b}-1fe23df7e (synth/place fail 21:34, owner active) + mem1-pm1400 f9a |
| HBM accelerator | ot_hgi_dma_front | S-live | - / - / - | ~200k flops (yosys OOM) -> SRAM | hgi-1010 c: hgi_dma_front_{a,b}-84a8d9171 |
| HBM accelerator | ot_hgi_hc_unit | S-live | - / - / - | only small flop version routed | hgi-1010: hgi_adp_hc_unit_b-df55694e8 + die-macro version |
| HBM accelerator | ot_hgi_quant_vm_transport_p | S-live | -97.75 / -17.99 / +0.00 | TT -97.75 / FF -17.99 | hgi-1010: hgi_quant_vm_pp55-f589c9afa (+3 cyc) |
| HBM accelerator | ot_hgi_sm_xload | S-live | -109.36 / +5.81 / +0.00 | TT -109 flop array | fe-push-hgi: hgi_xload_sram_{a,b}-60dab0b68 (+6 cyc, SRAM x tile) |
| HBM accelerator | ot_hgi_vm_unit | S-live | - / - / - | f050a31f9 / 93f2ee279 died at floorplan: --pin-regions-exhaustive 9,548 ports unmatched; e0a/b RTL_BOUNDARY REFUSED | hgi-1010/b: superseded by hgi_vm5 view on ot_hgi_vm_die (chain bench epyc1tb c17) |
| Qwen ROM | ot_qkvd_kv_end | S-live | -61.15 / -3.86 / +0.00 | TT -61.15 / FF -3.86 | qwen-1010: qkd_d2d_b-765c8c422-cl2, d2d_a lvt-hm25-ttfix |
| Qwen ROM | qfd_sp_su64_sfu | S-live | - / - / - | rowbuf flop array | redesign-qwen / fe-push-qwen: su64_sfu_bv_e{a,b}-50a21e381, fp{a,b}-097647146 |
| Qwen ROM | qfd_tile | S-live | -74.58 / -18.51 / +0.00 | TT -74.58 / FF -18.51 | qwen-1010: qfd_tile_rpx{c,d}-4ac3b982f, fb{a,b}-0ef4d7781 |
| Qwen ROM | qfd_tt_ctlm | S-live | - / - / - | 64 x 1,024 program store | qwen-1010: qfd_tt_ctlm_a-a639399be (+ fe-push PSRAM+HQ2 port) |
| HBM accelerator | ot_hbm_tu_retry_phy_port | S-none | -112.30 / -3.87 / +0.00 | TT -112.3 output-port class: pclk 22-level CTS chain, boundary insertion 660-703 ps; + reg2reg -34 credits/available[] 25 levels | none live (hardcore FB holder silent since 20:05; idle-sweep 21:29 found no owner) |
| DeepSeek ROM | dsfd_vm_wfc_ep | in flight | - / - / - | no routed verdict yet | mtp-wfc-1010: mtp-vm_wfc_ep-{4550cfabc,263f65ebf} |
| DeepSeek ROM | dsfd_wfc_crp | in flight | - / - / - | no routed verdict yet | fe-push-ds-1010: fe-wfccrp-* (SRAM landing) |
| HBM accelerator | hfd_idx_sel_native_qend | in flight | - / - / - | no routed verdict yet | hgi-1010: hbm_idx_qend_f9{a,b}-0bf2e922d |
| HBM accelerator | ot_hgi_coll_park | in flight | - / - / - | calibrating | fe-push-hgi-1010: hgi_coll_park_{a,b}-3bb774699 |
| HBM accelerator | ot_hgi_sm_pub | in flight | - / - / - | 256-way select | hgi-1010: hgi_adp_pub_a-8086a2e91 |
| Qwen ROM | ot_qwen_nearhbm_head_h | in flight | - / - / - | first trial | qwen-1010: qkd_rhead_{b,c} |
| Qwen ROM | qfd_io_host | in flight | - / - / - | first trial | qwen-1010/c: hing_qfd_{A,B}_qp-6640463e9 (QPIPE) |
| Qwen ROM | qfd_sp_tree_top_b | in flight | - / - / - | element pin spread | fe-push-qwen-1010: fp{a,b}-7525fae3d |
