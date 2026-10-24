# KV-G3 (lane file)
Host: intel2 (+ epyc3 overflow). Branch claude/kv-g3-1024 (from kv-p8-hub-1023 @1f988a72f, v3.8s; main not yet merged by ROOT-MERGE).
## Current step
13:38 UTC setup: worktree ~/wt/kv-g3; scratch from old hosts lost -> must regenerate bind dir (kit_rtl) for kv41.
## Notes
- COORD 23:22 owner clock decision (geom-review8 56152858e): binding clock check = related-pair CPPR skew <= 80 TT+FF + STA; max-min face spread is info only. Will report both.
13:47 UTC: bind dir rebuilt from committed bound_pv (kv41) + e33504a6f src at localhost:~/scratch/kv-g3 (asbuilt_kvg3.json remaps lost scratch paths). kit-rtl hub_Ei OK (0 narrow/unbound/spare).
hub_Ei clock variants (G3 kit, gen.py phys --kit-rtl, plan v3.8s): vA grid400 cap3000 (plan default) | vB grid400 cap1500 | vC grid+sinks r250 cap1500 | vD grid300.
Runs: intel2:~/scratch/kv-g3/g3/{vA,vB,vD}/kv3_hub_Ei (run_kit.sh route 64G 16cpu; pids 63611/63614/63619 = nohup wrappers)
13:55 UTC absorbed old intel2 scratch (read-only /mnt/old-nvme0/claude): copies at localhost:~/scratch/kv-g3/recovered/
 - clk-std-1023/hubEi_b: hub_Ei trial b (grid400+sinks, cap1500, kv39 RTL) 4_cts placement RC: related-pair CPPR skew TT 79.11 / FF 72.67 (<=80 PASS), face spread TT 85.0 / FF 82.8 (info), STA TT WNS -679 / WHS -71.7 (4_cts, placement RC, unrepaired).
 - clk-std-1023/hub/Ei_b_clkstd: CLK-STD kit (unpushed clock_taps distance+load, tap_balance window 20 on GRT RC) died at CTS -> relaunched as vE (same bound RTL, kv41 wrapper) intel2:~/scratch/kv-g3/g3/vE (run3.sh route+post_route).
 - kv-p8-hub-1023/Ei_b_grtprobe: GRT on trial b 4_cts, 5 congestion iters: overflow 9723 (max H19/V18), usage 7.5% -> CONGESTION risk for grid+sinks.
 - kv-p8-seam-1023: sys_c->io_E5 seam STA on routed io_cor_v1 (neighbour model): TT ft0-10 all >= 0; FF hold 2 ports negative (ft0_i -9.62, ft5_i -6.18). k9ft kits never ran.
07:03 PDT: old-scratch copies complete at localhost:~/scratch/kv-g3/recovered/ (clk-std incl. Ei_b_clkstd logs/reports, hubEi_b, kv-p8-hub (no odb), kv-p8-seam, intel1 kv-p7-1023/hub logs/reports); nothing of mine runs from /mnt/old-nvme0.
## 07:20 PDT RESUME (new agent after coordinator restart 07:03)
- vA-vE all alive on intel2 (vA-vD in 4_1_cts, vE in 3_5_place_dp); collecting, not relaunching. Branch ff'd to main 7353065934+.
- kit-rtl regenerated for hub_Wi/Eo/Wo/C, hg, hgi, pc, pv, phy at localhost:~/scratch/kv-g3/kit_rtl/g3/<type>/ (kv41 bind, plan v3.8s wrapper).
- FINDING: kv41 is bound on plan v3.6 -> hub_Eo/Wo bound RTL has NO v3.8s FIRM astk internal stations (lat_delta_v38s: L0..+1..+3 cycles); no tool realises internal_stations in RTL/kits yet. hub_Eo/Wo G3 kits need (a) astk core views, (b) station insertion.
- FINDING: hub_Wi 22 host cores = host_root_cluster partition_plan children; members incl. glue:* re-cut pieces (A1/A2) that do not exist as instances in the bound host leaf qkd_host_root_admission_obsx.
- Next: sub-agents KVG3-CORES (KV hard-core harden flow: core RTL from bound netlist + core kits + views) and KVG3-WI (hub_Wi host-core pins, G0C).
