# FABLE-RC-QC-SU handoff (Opus 5.5; QC SU/ST family review only; split from FABLE-RC-QC 11-23 20:52 PST)
Scope: slw_su*, sle_su* (su_c, su_l1), slw_st*, sle_st*, st_a. Read-only; hub posts only; never launch jobs.
## Open items
1 SU2R-FIX3 (QC-ALLFIX-SU): sle_su_c raw rr_t85 at x_ctl_o s6 + x_su_l0_stm_o s6/s7 + x_su_l1_stm_o s6/s7. Need: pick by property, leaf->port map for 3 su_c, one pass LAND-CAP+G0+scoped strict on 21 SU2R types. Proposed class fix: writer START FLOW-6 export pair (clock_landings.py:1812) + PRE ADV.
2 C1d rebind (C1c 3b12251bfd6c + FIX3) in epyc7 QC-ALLFIX/cE: read strict/LAT.
3 stm/sc probes from C1-noSU 12b66c0e4829 (cC, strict ETA 21:50; QC-OPEN-SU): baseline only, no SU2R credit.
4 su_c probes on C1d + su_c over-core census + C1c die render path (owed by QC-ALLFIX).
5 42 in-core rsn #2-#4 stations in su_l1 u_lane4-7: die row or RSN probe placed-xy proof (FABLE-RC-QC 20:51).
6 STATION-REGEN slw_su_l1 cla2a78701/clcc9d0155 (epyc11, V3 plan): ISTATIONS missing 0, render PASS, CTS setup -23/-21, hold -190/-202 on lpad_x_su_c_i chain (rc103). Await final GRT read.
7 st_a held on rc97 (btab g_read reach -59.92) till C2.
## Log
- 20:52 TAKING 69b870bb. 20:59 FIX3 review 5cf69ed3. 21:0x station-regen review 473c39fb.
