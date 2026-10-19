# S81 GEN mu3: strict die_port_bind (main checker) reduction, 10-19 (S81-DIECHAIN)

Branch claude/s81-diechain-mu3-1019. It builds on codex/s81-mu3-1019 293b25c2f, which is mu2 6050bfac9 plus the po2 562/512 RL2 views and endpoint_fault. The plan is p4l_lkcol_mu_pf, the same plan as mu2. Both checks below ran on the fleet (ot-epyc7, /srv/opentallas-scratch/claude/s81-diechain/mu3{b,c,d}).

| check | instances | unread bits | open output ports | verdict |
|---|---|---|---|---|
| main checker, baseline (Codex 9130-instance dieplace bind, 853546a13) | 9130 | 161,694 | 49 | FAIL |
| binder-of-record checker, mu3 1ab88c593 | 9009 | (not counted) | (not counted) | **PASS**, every counter 0, landing_reset 0, unresolved children 0 |
| main checker, mu3 1ab88c593 | 9009 | **1,182** | **29** | FAIL; 210,500 declared spare-out bits |

The t_mf top pins were added after the mu3d check. They remove 1 more open port, which leaves 28.

## What changed: real wiring
- `block_fault[15:0]` is a new die status output. It carries the sticky `fault` of the 12 plain slices, bk_col, bk_sel, the G-unit and the 2 svc_rs ENTRY slices. Each of these was an OUTPUT_OPEN fault port. The vector sits beside `endpoint_fault` and `land_fault`. Physically, the status collection network is still owed, just as it is for endpoint_fault.
- seq_host_mux `t_mf[3:0]` (the hslot+hwin MU table faults) now leaves as die status pins (`u_seqhost_t_mf`).

## What changed: declared spare outputs (tools/s81_dv/dv_spare_out.py)
Each class carries its own proof, and anything outside the classes stays a failure:
- **A, 191,940 bits.** These are svc_rs faces that the role ROM never drives (tree.json children/parent, embed.json go/so). Proof: every role-active face is wired, with 0 gaps.
- **B, 2,808 bits.** These are landing output bits that carry the lane-quantisation zero pads tied at hop-0 `st_*_0.i`.
- **C/C', 296 bits.** These are forwarded-clock taps (ck_line, ck_v, ctrl ck_o) of lanes the plan does not build. Each slice's `ck_rt = {8{clk}}` is also covered: the rt lanes are inbound and forwarded by their frames.
- **D, 15,456 bits.** This is `bo` of the 14 C1 slices. The RTL drives `assign bo = 1104'd0` at HB 0, including the u_sl of every lep wrapper.

## Remaining FAIL, by owner (real gaps, not declared)
| item | instances | class | owner |
|---|---|---|---|
| svc_rs / entry SM face w_v/w_a/w_m/w_d/w_st (the SM write rows have no die consumer) | 16 | functional die wiring gap: where SE/SO rows go | S81.STA.PAR.2 svc_rs (S81-CODEX) + S81U-2 |
| col_h9_l4 / col_h10_l4 xo/xok (x-chain forward out, relay of x) | 90 | either a chain end or a missing successor link: needs the frame plan | S81.STA.OWN.1 frames |
| ot_hbm3e_phy model outputs k_oor, refreshes, w_oor, w_rdy, w_reads, w_room, wr_* | 1 | PHY model observability and write-side ports | PHY owner (licensed-PHY model) |
| lep tf (TX forwarded lane clocks, PHY-side) | 4 | removed by COLL safe2 TXSAFE1 (Codex 938f12902) | S81-COLL-SAFE2 |
| s_3S/s_4S (HB 1) bo bits 1..51 and 565..1103 (1,182 bits) | 2 | xr3 band word bits outside the q lane | slice/xr3 owner (S81-SAFE-FIX/XR1) |
