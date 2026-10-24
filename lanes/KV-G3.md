# KV-G3 (lane file)
Host: intel2 (+ epyc3 overflow). Branch claude/kv-g3-1024 (from kv-p8-hub-1023 @1f988a72f, v3.8s; main not yet merged by ROOT-MERGE).
## Current step
13:38 UTC setup: worktree ~/wt/kv-g3; scratch from old hosts lost -> must regenerate bind dir (kit_rtl) for kv41.
## Notes
- COORD 23:22 owner clock decision (geom-review8 56152858e): binding clock check = related-pair CPPR skew <= 80 TT+FF + STA; max-min face spread is info only. Will report both.
13:47 UTC: bind dir rebuilt from committed bound_pv (kv41) + e33504a6f src at localhost:~/scratch/kv-g3 (asbuilt_kvg3.json remaps lost scratch paths). kit-rtl hub_Ei OK (0 narrow/unbound/spare).
hub_Ei clock variants (G3 kit, gen.py phys --kit-rtl, plan v3.8s): vA grid400 cap3000 (plan default) | vB grid400 cap1500 | vC grid+sinks r250 cap1500 | vD grid300.
Runs: intel2:~/scratch/kv-g3/g3/{vA,vB,vD}/kv3_hub_Ei (run_kit.sh route 64G 16cpu; pids 63611/63614/63619 = nohup wrappers)
