# FABLE-FIX-QC-N handoff (QC plan event N: N1 then N2; took over from QC-PLAN-R3 11-17 11:24)

Work dirs: E2 /srv/opentallas-scratch3/claude/qc-plan-r3-n-1117 (handed over; my files in fx/), E2 /srv/opentallas-scratch3/claude/fable-fix-qc-n (N2 tree), intel2 ~/fable-fix-qc-n (client logs).

## 11:2x-12:1x PST
- QC-PLAN-R3 keeps: M5 publish_gate fix branch claude/pubgate-g0-timeout-1117 (G0 takes 48 min, gate cap 1800 s), fleet/flow items. M5 (E8 kw45/src_qc_pin_eb1e73448bd0_s4q9m5, 4a6fbfa3a817) is PUBLISHED, NOT applied.
- Old N1 (8446d84fecda, bound without r572) is superseded. I stopped its CB16 (PIDs 3787306, 4061197).
- **N1B** plan POR/zz_s29_qc103_s4q9n1b.json cefb89af5f81 = M5 cf3ee3ca + lockup rows on qfd_tile_nk_rp2_romleaf_rr + NB slot delta d99a1840f308 (cbn_q00__cldbcda913 cl_nb_i00 x -43.2 um, was 38.9 um outside the core). 11 changed paths (fx/N1B_AUDIT.json). Sidecar compose/nb_m5_sidecar.json 9e8c68575051.
- event_tree_N tools: r572 overlay installed by copy+mv (bind.py 32fa3543, gen_phys.py eeaf298e, 2 tests); r573 files added from rt 24c7347cc887 (hold_eco_internal*.py, 4 tests, post_route_drv/hold_eco_internal_*.tcl). Pre-r572 copies in fx/*.pre572.
- N1B chain: fx/chain_s4q9n1b_1117.sh, E2 unit oth-ubuntu-4137957-1794943691 (--priority plan), started 11:28; log intel2 ~/fable-fix-qc-n/n1b_chain.client.log; gates in gates/*S4Q9N1B*. Accept: bind 0 errors, RTL 68 u_hdly_lk / 68 W(507) / 0 W(508), LATCHECK 1921/1921, hcparam 0, G0 0 errors, CB16 S2-S6.
- Publish plan for N1B: Codex M pipeline (E2 tools-converge/qc/m_closure_1116: capture_m_bind -> prepare_portable --revalidate; E8 qc-plan-r3-m5pub-1117: publish_m.py + relocate_m_bind.py) with old_tree = the published M5 tree, tool_files = r572/r573, delta-apply --link (r562), replicate --link-from to epyc9/epyc7, then candidate -> publish_gate -> apply_reviewed_tree_marker --keep-gen-hosts. One gate and one apply cover M5 + N1B. Needs the publish_gate G0 budget fix merged (QC-PLAN-R3).

## N2 root cause (measured on bind_s29q103S4Q9NBR/param_regen.json vs N1BR)
- N START moves lane sl_*_hc2__cws2 by +1 in all 12 slices. qc_fabric_transport then pads S head columns [1,1,0,1]; S roots +1, N roots unchanged, so HI_PAD = S far - N far rises by 1 on every station (r0-3 = the 44 hard st_a rows, r4-7 st_b too). The 30 R8_STALE bits are the same +1 on c16_E0_1 x_2_0.b_d (table 28, bound 29).
- Fix (no new master): bind hook holds HI_PAD of a plan hard core: uniform +k pad on the four N head columns of the slice (fx/patch_qft.py -> physical/die_plan/qwen_compute/bind/qc_fabric_transport.py). Cost 516 b x 4 x 12 flops. R8 table: derived from the NBR bus_groups, first bind should be final.
- st_a core edge: census = 2 types only (slw_st_a_v1__clfc5867a6__pvdf8e5ca4 / __pvf82a6c28). cl_b_hw_ctl_hc0_i x 570.24 -> 561.6 (8.64 lattice), SRAM g_btb[0] x 475.2 -> 457.92 (it sat 0.216 um from the cland). 12 changed paths per type, lane latency equal on 1921 lanes, census after = 0.
- N2 plan POR/zz_s29_qc103_s4q9n2.json 2c0208a4609f (base N 175b9337 + lockup re-key + st_a move); sidecar fx/n2_sidecar_b.json d080395ee5df; receipt fx/N2_COMPOSE.json. N2 tree copy: E2 fable-fix-qc-n/event_tree_N2 (unit oth-ubuntu-56236-1794944302).
