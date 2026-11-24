# HEAD hd_st_n4 exact global-placement start reseat (11-24)

Opened the exact global-placement checkpoint `056012c514ce` of the revised r18g START seating. Native E10 unit `oth-ubuntu-2753325-1795531290` produced it. With E10 scratching down to under 1 GiB, the completed ODB and exact generated kit were preserved on E9. E2 unit `oth-ubuntu-3235511-1795533814` measured and rendered the completed copy without GRT.

The original 95 captures above 405 µm drop to zero in the actual globally placed graph. Maximum register-to-register reach is 388.37 µm, down from 483.41. The independent placed scan has zero need-station and reach groups. The image shows the expected spread of inner banks and limited central buildup. Peak modeled column usage is 0.361. Pin capture p90/max are 23.9/86.4 µm, with all pins registered, no partial faces, relay collapse or clock-on-macro. The nearest clock reach maximum is 199.36 µm. Sparse fill and empty-area advisories remain.

This result confirms the specific START geometry repair at global placement. The private rerun still needs completed detailed placement, a fresh exact view and any separate sign-off admissions. The earlier signed release remains its own scope.

- [Viewed exact global placement](hd_st_n4_reseat_actual_gp_1124.png)
- [START seat changes](hd_st_n4_start_reseat_r18g_1124.md)
