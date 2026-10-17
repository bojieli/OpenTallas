# d4f A2P full core (HBM-ARRAY 10-16 TP-192 census: 4 COLL delivery lanes, SU 1,024 lanes, VM 2^18 words, 5 SerDes)
16 SMs (F108 columns) + 2 stacks, but the full d4c core: the SE/NE band content un-mirrored into the W half as a second
band row next to the die centre (4 hubs/COLL/SU cores, 16 SU slices, 32 VM banks), 5 lk/ep pairs, 400 um between band rows.
19,502.24 x 31,694.24 um = 618.1 mm2; reticle margins 1.31 (long) / 6.50 (short) mm; blocks 377.3 mm2 (0.61), ~0.69 incl relays.
Stages: SM_X 15.1, SM_HBM 3.2, COLL_EP 17.8, HBM_VM 33.6, VM_HUB 26.1, HC_ENG 7.9, SM_OUT 22.3; cuts 0.646/0.626, 6 lines > 0.60
(guidance; the 100-um band->column-top strip carries the 4-hub SM_X; widening it to 400 um moves the worst cut to the PC row).
Variants (same flags): core-channel 100: 606.4 mm2, cuts 0.698/0.629, 20 lines > 0.60; core 400 + sm-band 400: 629.8 mm2, 0.661/0.627.
compact_plan <d4e args> --full-core --serdes 5 --core-channel 400; a2p_fix.py DIR --phy-shift 4000.
