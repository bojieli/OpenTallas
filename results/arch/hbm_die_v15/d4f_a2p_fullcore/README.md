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
