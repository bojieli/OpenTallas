# QC-STA-HOP handoff (parent QC-ALLFIX). Updated 2026-11-25 07:45 PST.
Goal: st_a 651 um data hop (FABLE-RC-QC row "st_a (all 11 types, v13 census)") + name owners of the other 3 classes.
Finding: 651 um = ADV-G0-HOPS checker artefact. Slot b_hw_ctl_hc0 is explicit_stage0 with 5 bit_sites stages; kit places bs[j] at stage j
(ft_bit_sites.table first=0, face_flops ff_place_explicit_stage0); die_hop_scan.station_site used bs[j-1] and dropped bs[4].
Build-model worst on v13 aa3a14fb7484 = 333 um, all 11 types. Residual: v2 x5 cws0 406 um (12 bits), placed E5 not over 405 -> no row.
Placed probes (plan 9292a6474e9b): cland_b_hw_ctl_hc0_i -> ft_b_hw_ctl_hc0_o_0 438 um, 186 bits REACH; E5 signed all gates anyway.
Tool fix: commit 0b204b064d3 in epyc10 /srv/opentallas-scratch2/claude/QC-STA-HOP/wt (die_hop_scan.py, adv_g0_hops.py, test_die_hop_scan_exp0.py);
tests pass (28). Fable review running; push via ot-push-main after PASS.
Files: epyc12 + epyc10 /srv/opentallas-scratch2/claude/QC-STA-HOP/ (census2_v13.json, census_sta_hop_v13.tsv ec5a0029579c, g0_fixed.out).
Owners: tap sinks = QC-SINKBINS; clock_leg = SINKBINS retap + CORE-TAP-EARLY-STA 9339ff774fe6 (QC-STA-PROBE); macro_channel = no row (E5 DRC 0), v1 verdict from QC-STA-PROBE v1 DRT.
Hosts: epyc10/11 only until C1o v13 BIND-PASS (QC-ALLFIX 07:3x).
