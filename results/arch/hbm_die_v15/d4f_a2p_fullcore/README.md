# d4f A2P full core, widened (coordinator 10-16 21:30: d4f chosen; widen to spread the core; HBM-ARRAY TP-192 core)
16 SMs (H-SM F108 columns) + 2 stacks; full d4c core: 4 VM hubs + 32 banks (2^18 words), 4 COLL engines, 4 SU quarter
cores + 16 slices (1,024 lanes), 4 SFU, 4 HC clients + hc_eng; 5 SerDes = ep/lk S0 (COLL_SW), S3 (SE), N0 (NW), N2 (NE),
S1 (host/spare). E-quadrant cores un-mirrored into the W half as a second band row per half (400 um apart); E hubs have
no SM side (H-NETLIST P1, VMS client-absent = fill option a; plan graph drops their SM-side links).
21,002.24 x 32,094.24 um = 674.1 mm2; reticle margins 0.91 (long) / 5.00 (short) mm; blocks 377 mm2 (0.56), ~0.60 incl relays.
Cuts 0.470 / 0.521, 0 lines > 0.60 (fill a). Under fill b (cross-quadrant fill) the same outline gives 0.625 / 0.539, 2 lines.
Stages: SM_X 11.8, SM_HBM 2.75, COLL_EP 19.2, HBM_VM 32.0, VM_HUB 27.4, VM_RING 5.5, COLL_RING 15.1, HC_ENG 9.5, SM_OUT 21.1.
Grants: results/arch/hbm_die_v16_d4f/grants_d4f.json (rehome_v6 --sm-side-drop SE,NE --drop-slots <4 SerDes pairs>
--drop-ghosts --sm-column --homes homes.json; a2p_sm_column_grant.py F108 pins): 0 outside/overlaps/bad points, reticle OK.
Reproduce: compact_plan <d4e args> --full-core --fill a --serdes 5 --core-channel 400 --channel 600 --sm-band-channel 300
--qw-extra 3760; a2p_fix.py DIR --phy-shift 4000.

## Revision pc637 (H-DIE 10-16 23:30): PC band 399.6 -> 637.2 (d4b GEN needed --pc-strip 237.6; H-DIE-B d4c GEN found ctl_/svg_
overlaps in a 399.6 band), core channel 400 -> 300, SM->band channel 300 -> 200 to keep the reticle margin:
21,002.24 x 32,169.44 um = 675.6 mm2; margins 0.83 (long) / 5.00 (short) mm. Cuts 0.505 / 0.521 at the core; v6_eval reports a
1.14 window over the N PHY at x 6,100 that cut_window_who.py measures as 0.08 (a lanes-model leg artefact of pc_NW2>sm_NW2
SM_HBM 1,132 b) -- GRT is the arbiter. Grants rebuilt with tools/hbm_die_v15/d4f_grants_build.sh (0 outside / 0 overlaps,
grants_audit.py); root sites regenerated with tools/die_clock/root_sites.py -> results/arch/hbm_die_v16_d4f/d4f_root_sites_pc637.json
(36 sites, 0 failed, 0 slot collisions). compact_plan args: + --pc-h 637.2 --core-channel 300 --channel 600 --sm-band-channel 200.

## Revision r2 (H-DIE 10-17 ~02:00, coordinator run1 review)
E column 3.1 -> 2.0 mm (hc_eng 2,000 x 4,750, aspect 2.4), SerDes lk tiles 250 x 2,250 -> 600 x 600 (no long-thin blocks), sucx
216 x 194 -> 270 x 270 (measured SYNTH 264.6 sq): 19,902.24 x 32,169.44 um = 640.2 mm2, margins 0.83 / 6.10 mm; core cuts 0.545 /
0.6 lines only at the PHY-row lanes artefact (see pc637 note). Shared-region fits (tools/hbm_die_v15/d4f_fit_slots.py): hb_dbk_SW/NW
800 x 560 (dbk + wb_kport), host_cp 1,300 x 700 (4 users), sfus_<Q> = SFU programme store r6 447.12 x 1,023.84; COLL v7 / tkm_SW
grants unchanged. Grants rebuilt by d4f_grants_build.sh: 0 outside / 0 overlaps. Root sites regenerated -> d4f_root_sites_r2.json
(36, 0 failed, 0 slot collisions). compact_plan: + --column 2000 --sucx 270 270; a2p_fix --lk-sq 600.
