# HBM plan event d55a_rd1_1111 (HBM-COMPOSE-2 for DIE-HBM-100, 2026-11-12) DO_NOT_COUNT

Plan die_plan.json.gz sha256 02659299fcf0 (full: see queue READY) = d53b ad080c302a2b + deltas/ctlr5_d54_dlhbm_1112.json.gz (DIE-LAYOUT-HBM, q_hub_nw only: ctl_r5 146.88x86.4 declared core-shape exception at (5736.96, 1036.8) + u_host_boot_hop04 MOVE +43.2 um; PENDING COORD acknowledgement of the exception if no ruling is queued).
rd1 raw files (HBM-HUB-RTL-1, claude/hbm-rd1-coll-1111@e77f8fff1b, APPROVED; compiler-cal-rd1 225791101e APPROVED, merge pending): deltas/d_rd1_coll_vmrt4_1111.json.gz (keys v2 b6a8ea27), rd1/t11_top_rd1.sv (sha 7aa058d5...), rd1/asbuilt_keys_rd1.json.gz, corelat/cycles_vecd4ae_rd1_1111.tsv. The die_plan.json differs from d53b only by ctlr5_d54.
Recipe: results/hbm_hub_rtl_rd1_bind_1111/plan_event/README.md on e77f8fff1b (elab -> splice -> fused_close -> prune -> cache_names -> remap -> map_fill -> pass 1 -> pads -> pass 2); bind_rd1.sh here is the copy used (paths point at the private dir rd1d54b).
Bind of this plan (strict two-pass, epyc8): BIND_OK, 92 partitions, 420 crossings, n_errors 0, stale 0, LC REGEN 38 / 0 errors, pad_flops 945214. SHA256SUMS 5f5f70bf7afc6bfb, bind_report 7e022bf183b8d6e2. xp_ctl binds as ot_hgi_qdq_transport_ctl_r5 with rl_cfg 8'b01111111.
Control: d53b-only (no ctl_r5) rd1 bind also BIND_OK 92/420/0 (control/).
Exact changed bound files (cmp_final_rd1_vs_ctl.txt, 12): bound top, root, q_hub_ne, q_hub_nw, q_su00, q_su11, q_su20, q_su31 and their physical_v1 copies for the SU types.
Price (record only): -0.531% / 1639.25.
