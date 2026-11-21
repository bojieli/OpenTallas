# FAM-S81-LEPE handoff (11-21 ~05:15 PST) -- context near limit, successor needed (Sonnet/Opus FAM-S81-LEPE-2)
Representative dsdv_slice_lepe_mu_LP__t2. Family: lepe_nh_mus_LP t1, lepw_mu_LP t2, lepw_mus_LP t2, lepw_mu_C t1.
## Landed
main 4ee24dd3c24: OT_S81SL_LEP_ROS (default 0, selectors ROS2/ROS3) + benches RIP<=4/ROS. J6 rows posted pending proof8 (post 95083e32).
## Proofs (epyc9 /srv/opentallas-scratch2/claude)
- fable-lepe/opus-p7-r2, fable-lepe/opus-p8-local/r4 (7b): hold read only. Pre-GRT FF hold after repair -62.27 / -64.45, setup -272.7 / -243.9; in GRT. Old waiter (bp0rlvp6k) died on a quoting bug; reads are by file (run_grt.log).
- fam-lepe/p8x = PROOF8 (unit oth-ubuntu-1650150-1795255723, ot-wait waiter armed, sta8/ has STA json): RIP2+ROS2+li D1 + n_st D1. Post-CTS TT repair wns -220.33 (7b -245.46), pre-GRT FF hold -207.20. NOT near -42; GRT repair will not close it.
## proof8 classes (fam-lepe/sta8/setup3000.json, 1261 neg ends): 
ros_r[0] stage after rop -202 (121 ends: the added stages are NOT spread, first leg still ~1.4 mm); rx_mem rd_out -> rid -182 (161), -> ml_wd -140 (65); g_wrep n_r -> count_r/wp_r -196 (63 ends, TX window state to address counters); lep rip rd_r -> ri -102 (121); u_status -> ph_r -220 (12); pair_b -> registered_select -139 (16).
## NEXT
1. FIRM sites (istations.tcl p6_put by name) for ros_r[k][*] and rd_r[k][*] chains: stage k at rop + k/(ROS+1) * (roq - rop) per bit, using proof8 placed positions of rop/roq (read from 3_place.odb); stations.py (r4) is the model, drift tolerance 16 um.
2. rd_out -> rid/ml_wd: needs a registered macro read (not a station): +1 on {rhd, relp, rhk, ring meta, ml_rd, ml_rv} with lep_mu bench; or move rx_mem banks nearer rid.
3. g_wrep n_r -> count_r/wp_r: relay or per-bank replica (WREP) of the window count.
4. Then proof9; carry proven rows to siblings; hand rows to S81-J6-ASSEMBLY-R2 (J7 after 13:00 PST).
Scripts: fam-lepe/p8x/{plan8.py,prepare8.sh,run8.sh}, fam-lepe/clone (lane clone, main-based), sta: fam-lepe/sta8/sta.sh (edit K for a new kit).
