DIE-HEAD-31 Thu Oct 29 03:10:56 PM PDT 2026 HEAD canary of the S81 collector face-flop fix (9b39beae2 = main 1ae7d17ef) on hd_ctl.
Kit: tools/s81_head/head_ctl_hk5_kit.py at main da6a5e79e1 on intel2 die-head-30/ctl/source -> die-head-31/ctl_canary/hd_ctl
(also carries beat_tx IDLE_ZERO, main c67a94721); run_kit.sh floorplan (unit oth-ubuntu-2071068).
RESULT FACE_GUARD PASS 4424/4424 (was 4420/4424, 4 unregistered cland_dn_{ready,fault}_{ctrl_i0,n_rx_i}), face_guard_odb
       PASS, port_bind PASS 4474/4474 missing 0 extra 0, REG_FANOUT PASS (CHECKED).  LEC of this kit running inside the
       same unit (lec/lec.json when done).
RE-KIT TYPES (regen of all 25 wrappers with main vs the die-head-30 gen; only face-flop hunks differ, CHECKED by diff):
       hd_ctl 4, hd_host_n 2, hd_mesh_e 2, hd_spn 4, hd_spn_end 4 ot_dp_landing_face flops (16 total, +1 status cycle
       on those boot status edges, 0 data cycles); the other 20 types byte-identical.
