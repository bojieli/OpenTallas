# HBM 12:00 cut plan event d46a_cut1111 (DIE-HBM-100, 2026-11-11) DO_NOT_COUNT

Overlay on base plan 29333b2b19c9 (p11t_taps_cyc). Composed plan sha256 e6bb764f1f229d28d70cbebbc68977ce68a68207640f30fa5bd5dd72a1729f91
(die_plan.json.gz here; gunzip == composed t10). Only files that differ from the base dir are present; every other sidecar is the base's.

Deltas, in apply order (compose.py, log compose.log): d0_base_sync; d1_channels (CHANNELS rev3 1a1647f7) + d1c ccd; d2 ftres spu1; d2b mneed;
d2c postcut; d4 NW_io form h; d4b stationfix_1111; d4 cpl2 q_su10/pv1, q_su21/pv1, q_spt0/pv1 (lift); d4 cplb1 q_b101, q_b101_nw; d5_phy_cores (u_phy_Q hard core on PHY_NC/NE/NW).

Gates (stage S3): G0 639 -> 624 errors, 0 new (g0cmp.txt); stscan q_b101/_nw phantom 1370 -> 0, miss>405 0 (stscan.tsv);
route_supply per type in route_supply_cmp.tsv (WORSE: NE_io, q_hub_ne, q_spt0 +pv1, root; all flagged in the READY).
PHY_NC gen dry run: rc 0, one advisory OT_MACRO_GRID_SNAP (u_phy_Q 7022 pins off track at [0,0], unresolved).

Strict bind (src kw43/src_hbm_tc1111p_por36, asbuilt kw43-canon vK5d_c12), two passes (bin/bind_cut.sh, bin/bind_cut_pass2.sh):
 pass 1: 30 R8_STALE and nothing else (landing table made on the base bind; channels rev3 pin cycles changed 20 members).
 pass 2: hbm_lat_pads.py on t10 + pass-1 bus_groups -> hbm_arch_B2o_r8_landing_cut1111.json.gz (asbuilt_cut1111_t10.json land_r8 points at it):
   n_errors 0, stale 0, uncovered 0, 90 partitions, 420 crossings, 378992 bits. 20 of 9467 members differ from the F5a table;
   loop round trips unchanged (SFU_VM NW 119 / NE 123, HC_Q NW 137 / NE 150), pad flops 1977957 -> 1979489, max pad 110.
 bind digest: SHA256SUMS 78ea88152b234ab97b0c97828cbd9ddf1c59c058c4b367cd7934303d6101d48c, bind_report.json b3f11972f85fe235cf022361172b9c2e001f1512ea878826fa72f0900de3efc9
 (bind_p2_SHA256SUMS.txt lists the 401 files); table sha256 ec8cd87c664fc95d350f57640c98b15eb84cd959609552a22ff813a0d860ef0b (uncompressed); asbuilt 2b78c7f3488f97d43c5e8a562b2b92cde8bf3fef0923c47417615d2d8f59d2a9.
 Bind dir: epyc8:/srv/opentallas-scratch2/claude/hbm-cut-1111/bind/bind_cut1111_t10_p2 (unit oth-ubuntu-3706158-1794403246).

S2 launch list: HOLD (never launched at this cut) q_su01*, q_su11* (+pv1), q_b100/q_b102/q_b103 (+pv1), q_b001*, q_b113*, q_b011*, q_b002* (PDN-0179 class: b011, b002).
IN with written reason: q_b101, q_b101_nw (S2 evidence = real-net Steiner bound 0.42 / 0.52 <= 0.8; route_supply 3.13 counts each broadcast sink bit as a 2-pin net).
