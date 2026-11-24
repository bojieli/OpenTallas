# SEAT-MATCH-AUDIT handoff (updated 2026-11-24 01:4x PST)

## On main
- b68b5d03: kit_istations RELAY-SEG (QC cb g_seg slices / cnt,run copies), RELAY-CNT (ot_dp_dly_cnt q[b] -> last kept stage; sle_ctl su_l0 444), same-site '/' vs '.' twin no miss; seat_match.py static check (DEAD-INST / DEAD-REG / CONFLICT, strap-bank hint, `prune` with ledger); kit_gen_lint `GEN_LINT WARN SEAT-MISS`; plan_gate_pre `WARN SEATMATCH` (report only, FLOW-OPS-R3 00:40 handed the PRE half back); strap_bank_seats.py.
- aa4d9142: strap_bank_seats macro capture point taken toward the register sinks.
- Not mine: S81 col opt_merge (S81-ALLFIX-COL; already fixed by wave env OT_KEEP_WIRES=ot_dp_dly:r, dff49826); FAIL conversion only after re-keys read 0.

## Files
- SEAT-MATCH-AUDIT-census-signed.tsv: 110 types, cause, owner, signed (signed-store any-plan), rows seated by b68b5d03, stale verdict counts, kit read.
- SEAT-MATCH-AUDIT-stale-keys.tsv: every still-unmatched key: die|type, key, site, verdict+action, current register (strap bank / bound instance+params / nearest name), owner.
- SEAT-MATCH-AUDIT-sle_ctl-rekey-row.json: sle_ctl row on C1g 96cce77c1e2f -> 0391dcd3b846 (drop / add lists, per-bank reach).
- SEAT-MATCH-AUDIT-col-unmatched.txt: S81 col 52-key lists (pre-env gens).

## sle_ctl re-key (C1g 96cce77c1e2f base; seats from compose-A placed dump; bind RTL C1g cF/bind/rtl)
Static seat_match on C1g bind RTL: before 15,996 DEAD-INST (u_pd11 x_fw_i 5,896, u_pd12 x_st_a_i 3,216, u_pd4 b_tw_data_i 4,204, u_pd5 x_fw_p1_i 2,680) + 444 OK-CNT (su_l0, seated by RELAY-CNT); after 0 dead, 28,466 bank seats OK. bind.py reads relay_sites only for u_bin_ keys, so the bound RTL is unchanged by this row.

| bank | bits | f stages | cnt stages | seats | worst hop new (um) | worst hop placed now (um) |
|---|---|---|---|---|---|---|
| u_r8b_strap_r8pad_u_ctl_l9o_v | 1 | 17 | 14 | 31 | 17.3 | 578.5 |
| u_r8b_strap_r8pad_u_ctl_r_d | 256 | 17 | 14 | 7936 | 45.4 | 139.5 |
| u_r8b_strap_r8pad_u_ctl_r_idx | 8 | 17 | 14 | 248 | 22.4 | 97.9 |
| u_r8b_strap_r8pad_u_ctl_r_last | 1 | 17 | 14 | 31 | 16.9 | 514.8 |
| u_r8b_strap_r8pad_u_ctl_r_v | 1 | 17 | 14 | 31 | 18.1 | 508.1 |
| u_r8b_strap_r8pad_u_ctl_stn_fault | 1 | 17 | 14 | 31 | 19.2 | 509.2 |
| u_r8b_strap_r8pad_u_rp_chd_q | 502 | 3 | 3 | 3012 | 54.0 | 480.1 |
| u_r8b_strap_r8pad_u_rp_chd_q_1 | 536 | 6 | 6 | 6432 | 222.0 | 813.2 |
| u_r8b_strap_r8pad_u_rp_cmd_q | 34 | 3 | 3 | 204 | 207.8 | 346.9 |
| u_r8b_strap_r8pad_u_rp_tw_addr | 24 | 9 | 1 | 240 | 64.4 | 261.1 |
| u_r8b_strap_r8pad_u_rp_tw_data | 1024 | 9 | 1 | 10240 | 96.8 | 428.2 |
| u_r8b_strap_r8pad_u_rp_tw_kind | 2 | 9 | 1 | 20 | 77.5 | 721.6 |
| u_r8b_strap_r8pad_u_rp_tw_we | 1 | 9 | 1 | 10 | 106.0 | 220.8 |

Dropped rows and their replacement reach:

| bus | dead rows dropped | replacement banks | worst hop new | worst hop placed now |
|---|---|---|---|---|
| x_fw_i | 5896 | u_r8b_strap_r8pad_u_rp_chd_q_1 | 222.0 | 813.2 |
| x_st_a_i | 3216 | u_r8b_strap_r8pad_u_ctl_l9o_v, u_r8b_strap_r8pad_u_ctl_r_d, u_r8b_strap_r8pad_u_ctl_r_idx, u_r8b_strap_r8pad_u_ctl_r_last, u_r8b_strap_r8pad_u_ctl_r_v, u_r8b_strap_r8pad_u_ctl_stn_fault | 45.4 | 578.5 |
| b_tw_data_i | 4204 | u_r8b_strap_r8pad_u_rp_tw_addr, u_r8b_strap_r8pad_u_rp_tw_data, u_r8b_strap_r8pad_u_rp_tw_kind, u_r8b_strap_r8pad_u_rp_tw_we | 106.0 | 721.6 |
| x_fw_p1_i | 2680 | u_r8b_strap_r8pad_u_rp_chd_q, u_r8b_strap_r8pad_u_rp_cmd_q | 207.8 | 480.1 |

Caveats: hops are planned L1 on the compose-A placement (u_rp at x865-1045 y316-502); a hard-macro capture (u_ctl) is taken at its edge point nearest the register sinks, not its LEF pin. Count stages sit at the capture end (any strap tap one short hop from the sink). Next: PRE on C1g tree (queued epyc7, load-held), then probe by QC-SLECTL-RESYN A/B.

## Signed types among the 110
12 have an any-plan SIGNED record in signed-store: kv3_hub_C, slw_st_a_v2__clf4365a62, cbn_q00__cl622f65d2, bk_sel__t2, col_h10_r1__t1__cld01bb4ae, col_h10_r2__t1__clac068e56, col_h10_r2__t1__cl8b686b3e, col_h9_r2__t1__clce45cab5__pv7a260fc0, col_h9_r2__t1__cl774acf45__pv11b6518d, col_h9_r0_p3__t1__cl31d0dc4b, ot_s81sl_leaf__t40__cl86ea32b3__sid5S, ot_s81sl_leaf__t74. The other 98 have no SIGNED record. Do not re-open a signed type for a placement-quality count alone.
