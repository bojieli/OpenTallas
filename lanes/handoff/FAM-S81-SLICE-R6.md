# FAM-S81-SLICE-R6 handoff (11-22 23:0x PST)
Dir: intel2 + epyc7 /srv/opentallas-scratch2/claude/fam-s81-slice-r6/{rows,tmp,j8bind,trees}
Plans: rows/plan_j8_slice_v9.json (5ef4a74c48a0, bound fork trees/s81_j8v9 on epyc7); rows/plan_j8_slice_v10.json (74cbb9822c02 = v9 + c1x_C t8 ft1 stage-2 moves), handed to S81-J6-ASSEMBLY-R5 PROVISIONAL; v10 gate epyc10 j8bind/gate_v10y.otrun.log (expect only 9 inherited J7 G0 errors).
Signed: t29 cl2e5c855a, t36.
Live run-items (rt/current 4baf0383f1e1, tmp/launchr.sh, --goal route, resumed from place): t45 oth-ubuntu-2004733, t18 -2004712, t40cl1e -2007228, t6cl07 -2007067, t6cl54 -2007268, t29clc7 -2009047.
Probe: kv512_C t1 OT_PROBE_THROUGH=1 spec _1122181858 unit oth-ubuntu-2109218 (epyc10).
Other kits: kv512_C t1 v9 _1122065315 (oth-ubuntu-3193381); t52 J7 _1122065653 (oth-ubuntu-3341374); c1x_C t9 v9 fork _1122185740 (oth-ubuntu-3214932, epyc7); t22 attempt 2 in wave.
Holds (kit_wave.json 75cf8123374): t40 cl1ea9de02 (J8); lepe_mu_C t1 (J9: LEPE-4 54c1e2 + strip/body, rows/plan_j8_slice_cm_v2.json); c1x_C t9 J7 row (private v9 kit / J8).
Waiters: loop ot-wait --durable until rc!=75 per unit. Private specs on the fork need --host epyc7.
