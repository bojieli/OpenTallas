# HBM d44v_final4_1109: the one final HBM switch (HBM-PLAN-1, COORD ruling 11-09 02:33)

Plan `die_plan.json.gz` = sha256 77bbddd873546ac3 (uncompressed). It is built on plan_final3 e34eae889e17 (+ d44v_gqi), and the events below are applied in this order:

| step | event file | what |
|---|---|---|
| E1/E2 | e1e2_1109_event.json | q_hub_ne: u_sfus_Q__q0 and u_pgp_Q__q0__c1..c9 move +4.32 in y (taps follow). root kit_core_margins_um [4.32,0,4.32,4.32]. GQI drop: 4 gqi_issue instances -> cores/..d44v_gqi8 |
| E3 | i8w8_1109_event.json | ot_hbm_sm_i8w_front: command[191:184] face-shell pins dropped (table 14896 -> 14888) |
| E11 | e11e12_1109_event.json | q_spu0(+pv1): die NS band [380.16,1071.36] M5 share 1.0 -> 0.5 (M7 stays 1.0) |
| E12 | e11e12_1109_event.json, e12b_resite_1109_event.json | q_spb2pv1 L40_o N window [782.4,960] -> [1080,1316.16]; partner q_spu1pv1 L40x1 in-window follows; ft_s0_resite: k 7 -> 7, 0 cycles |
| E6 | istareach_1109_event.json + ledger | add_reach_istations (178842a72a) on the bind_F3d bound RTL: 87 entries, 451 stations, 451 PIN CYCLES on 76 lanes, 12 native types |
| E5 | relay_1109_event.json | ts_relay_event (run LAST): 6 types, 20 buses, 19 lanes, +132 PIN CYCLES. Hubs skipped (TS3 default). L8007 70 / L8008 69 -> RXLAT 145 |

Bind of record: `bind/bindF5b.sh` with `bind/asbuilt_p37su5_sm_lat_vK5b.json`. This is strict, with n_errors 0 and LATENCY_CONSUMERS PASS (23 REGEN). Its output is at intel1 scratch2/claude/hbm-plan-1/bind/bind_F5b, see `bind/F5b_SHA256`.
- vK5b = DIE-HBM-96 vK3, plus internal_stations_types (istareach 12 + relay native-OUT 6), plus internal_stations_buses (each relay type realizes only its relay OUT buses natively; tools/die_plan/native_istations.selected_buses), plus the q_sm sources of HBM-SM-KIDS-2 (claude/hbm-sm-kids-1109@420729df6d, `bind/sm1109_MANIFEST.json`), plus the R8 table re-derived for this plan (`bind/hbm_arch_B2o_r8_landing.json.gz`, from hbm_lat_pads.py with contract hbm_lat_1108). land_r8_extra is dropped.
- `bind/landed_delta_vB_to_F5a.tsv`: per R8 member, the landed-depth change against the wave table r8_vB. This is the compiler-visible delta: 1889 members, plus the loop RT changes SFU_VM_NW 110 -> 119, NE 110 -> 123, HC_Q_NW 132 -> 137, NE 129 -> 150.
- `bind/relay_miter_F4e_F4f.json`: ts_relay_miter with `--r8 bind/r8_extra_F4d_F5a.json`, bound RTL of p5_ista vs p6_relay (same tool, each with its own table). All 19 lanes equal their declared pin cycles. The 812 R8 pad bits change exactly by the re-derived table. The 4 remaining lines are param_regen consumer parameters in root (rootctl CR_RT 12 -> 15, hc_root XRU 2 -> 11).
- `bind/switch_table_F5b.tsv`: per type, the wave key against this plan and bind; rows marked SUPERSEDED are to be rebuilt.

Co-changes that ride this switch:
- RTL: claude/hbm-hard-9-rxlat145-1109@637d0f1a404 (ot_hbm_host_cp_rxs.sv md5 af40fc9c): RXLAT 101 -> 145 = 6 + L8008 69 + L8007 70, RSTLAT 70 unchanged. The host_cp_rxs view is rebuilt as R6.
- Host frame gap: HGAP >= 15 + L8008 + L8007 = 154 edges (hard minimum 148), from HBM-TRANSPORT-1's 11-09 04:06 bench. A gap of 110 FAILS on this plan.
- Compiler: VMLG SU-face shift, SEL_ADV = D_CAL - D_CMD and OWN_LAG = D_CMD + 2 + D_REQ per su_N tap, read from bind_F5b/bind_latency.json (HBM-TRANSPORT-1 11-09 03:02). This is a token-build obligation.

Not in this plan, each with its blocker: E4 q_b010(+pv1) split, E7 rx_bm3_rest M6, E8 programme_store_r10, E9 Q2NF outline, and the VMLG SU-face compiler shift (HBM-TRANSPORT-1 11-09 03:02).
