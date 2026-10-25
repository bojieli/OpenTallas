# PROTO (virtual prototyping sweep, 2026-10-24 evening; rtx-pro coordinator lane agent)
Branch claude/proto-1024r (worktree rtx-pro:/home/ubuntu/wt/proto-1024r, base origin/main a11334b98). Fleet data: <host>:/srv/opentallas-scratch2/claude/proto/ (ot-run --dir, spills).
Goal: prove every partition type without a SIGNED view is routable / roughly meets timing BEFORE detailed route (no DRT).
Method (tools/die_plan/proto_sweep.py + proto_render.py, on the branch): the G2 partition probe (g2.part_probe: exact
outline + plan pins, one boundary flop per pin bit, ft station flops at regs_um / along the route, hard cores + leaves as
placement blockages + M1..obs_max OBS) + one ideal clock on every flop + plan IO budget 0.2 T + 60/25 ps uncertainty +
repair_design + GRT M2..top with the partition's own logic as capacity adjust 0.5 + STA on GRT RC (TT setup / FF hold).
SKELETON prototype: partition logic not synthesised (B2m and the KV v4 bind have no bound RTL; hard-core views mostly
unrouted), so STA covers the plan wires only (pin->reg, ft hops, repeater pitch). Classes: CLEAN / HOTSPOT / STRUCTURAL.
## Log
2026-10-24 21:48 PDT PROTO: started. Pilot (4 probes: B2m q_b000/q_su00, KV kv3_hg, QC sle_hc0) running via ot-run; then batches HBM B2m -> KV -> QC -> head -> S81.
2026-10-24 22:14 PDT PROTO: tool db96f4053 + fixes (all hard cores blocked, platform RC, repeaters -max_wire_length 450, GRT 3 congestion rounds). Two restarts: g2 left KV/QC/S81 cores unblocked; tech LEF has no RC (zero wire C). sweep3 LIVE: 281 partition probes (B2m 44, KV 44, QC 51, head 15, S81 127) via launcher epyc1:/srv/opentallas-scratch2/claude/proto/launch.sh pid 982359 (ot-run --dir, MAXJ 70), dirs <host>:/srv/opentallas-scratch2/claude/proto/sweep3/<die>/part_<type>. SKIPPED (lane live / geom FAIL): KV hub_Ei, io_cor_v1, io_ft_v1; QC coll_ftc, tt_ctlm; head hd_tile; S81 col_* x12 (g3k5 FAIL), slice_station x34 (ELEM-S81); hard types (q_sm*, PHY_N, kv3_phy*, phy_serdes*, phy_ucie_kv, phy__t1).
2026-10-24 22:14 PDT PROTO: HBM idle hard cores (placed by ELEM-HBM, never routed, no lane live) -> GRT + placement-RC STA TT/FF on copies <host>:/srv/opentallas-scratch2/claude/proto-cores/<kit>: group_rel_id, wb_kport_q, pdie_serdes (epyc3), idx_qctl, cxport_ij_q, qw_dec (intel1). Already known: dma_back_static_vp4_banks_cp MPL-0065 (cells do not fit beside the macros), su_programme_pslice_c5 DPL crash, vms_glue_nw_t GPL exit 245. idx_qctl: CTS RSZ-0060 max buffer count.
