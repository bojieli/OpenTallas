# FABLE-UNC-S81-LEAF handoff (agent a123f45b0c046602a; updated 11-23 02:3x PST)
Brief: localhost scratchpad fable_uncovered_brief.txt + rules.txt. Die S81, event J9, cut 18:00. R5 intake: Wave A rows GATED 10:30, Wave B 12:30 HARD.
Items: rc4/rc5 (leaf ft corridor t58/t61), rc12 (kv_leaf t1/t4), rc62 (bk_sel), rc55 (seqhost), rc59 (gunit), + [hop-S81-leaf] 513 placed-hop gaps (FIX-LEDGER 02:1x, hard stop 12:30; class table lanes/handoff/FABLE-UNC-S81-DIE-hopclass-j8.tsv; tool rt/current tools/die_plan/adv_hop_gap.py).
Work dir: epyc9 /srv/opentallas-scratch3/claude/fable-unc-s81-leaf (an*.py, cong.py = overflow clustering of congestion.rpt, patched lanech_row.py + lanech.py, j9u.sh pipeline, tmp/).
## Findings (posted 8c75d5a8)
- LCBC row 3d j9R (lanech_row.py --ftcorr ac6181e7727a; bind running since 02:13) does NOT widen the t58 hotspot: ve_m|vsw H channel x302-449 y414-432 stays 17.28 (16 k of 24 k overflow there, nets u_ft_ft7_o_3). Cause: ft_pairs tests straight regs_um polyline; ft7 line passes through ve_m (obs 7).
- t61 ve_s|vsw widened only to 34.56 for ~2.4 k bits (needs ~69 at 31 tracks/um).
- kv_leaf t4 W=0: core-margin 17.28 on E face short by 2.2 um. --core-margin 8.64 gives t1 40 / t3 40 / t4 34.56 / t5 34.56.
- Patch: L-path legs least inside cores, non-junction channels only, width = bits/tracks 34.56..69.12, ranked search (corridor >= half, junction >= 30.24, strip >= 43.2).
## Running / next
- j9U pipeline (ot-run unit oth-ubuntu-3756638-1795428954, log j9u.otrun.log): -> j9U_final.json + pre_j9U.2.log. Then: post PRE result to LCBC + R5; in-plan probes t58 and kv_leaf t4 (LCBC intel2 leaf-route-cbc/probe/pfork.sh pattern, own out dir, OT_LANE=FABLE-UNC-S81-LEAF); read with cong.py against baseline (t58 24212; kv t1 944).
- One leaf row only (LCBC's 3d): ask LCBC to take the patch and re-bind; do not file a second leaf row.
- rc62: R7 root cause = J7/J8 l20s lacks OT_BKSEL_L4 RTL (0 u_lpd cells); J9 source row BKSEL-IDS-RSPLIT v2. J8 plan seats u_vm.r FIRM; review ask = placed hop u_lpd.q -> u_vm.r on the probe + why bind passed without L4.
- rc55/rc59: VIS-S81-MISC v3 (worker ae8b400df024d32b4, epyc7 /srv/opentallas-scratch2/claude/vis-s81-misc/rows3, vism_j9.py) in progress; seqhost J8 type has NO internal_stations key; review when v3 rows exist.
- Reports to COORD: (1) causes + rows within 1 h; (2) when all GATED/REASONED.
