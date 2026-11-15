# OVERSIZE-1 handoff (lane started 2026-11-14 ~17:30 PST; owner-approved FABLE-WAVE-REVIEW fix 8 / R-CAP-3)

Goal: no type >400k movable goes through the flat flow; split into hard child cores or harden logic. Core gates: DRC 0, TT setup >= -42 ps, internal FF hold >= 0.

## Inventory (unsigned, current plan; synth = pre-floorplan std cells; ring/ft = soft ot_dp_clk_landing(_cas) share)
| die | type | synth | placed/proj | ring+ft | owner | plan after split |
|---|---|---|---|---|---|---|
| KV | kv3_pv_v4n | 476.6k | proj 1.37M | 58% | KV-102 | rings hard -> ~265k |
| KV | kv3_pv_v3n | 473.1k | - | 54% | KV-102 | ~243k |
| KV | kv3_pv_v5n / v5 | 463.0k / 459.3k | proj 1.02M | 57% | KV-102 | ~238k / 234k |
| KV | kv3_pv_v2 | 455.0k | - | 54% | KV-102 | ~264k |
| KV | kv3_pv_v6 / v6n | 408.0k / 404.9k | - | 63% | KV-102 | ~228k / 225k |
| KV | kv3_pv_v1n | 389.7k | meas 632k movable | 51% | KV-102 | ~205k |
| KV | kv3_pv_v12 | 386.9k | - | 62% | KV-102 | ~229k |
| KV | kv3_pv_v7 | 355.8k | - | 61% | KV-102 | ~211k |
| KV | kv3_pv_v8 / kv3_pv | 296.8k / 299.1k | meas 468k / proj 750k | 45% | KV-102 | ~231k / 233k |
| KV | kv3_hub_C | 769.2k | 706.6k old | 42% | KV-102 | rings -> ~654k; still needs 3-way split (u_pvfin 42k+pvfin_out 23.5k core, 36% unnamed engine) |
| KV | kv3_hub_Eo / Wo | 374.2k / 382.8k | proj 713k | 57% | KV-102 | ~269k / 277k |
| KV | kv3_hg_v1p5 (p2/p4/p5 same) | 279.9k | proj 577k, p6 meas 421k | 35%+ | KV-102 | ~170k |
| KV | kv3_hg_v3 | 264.6k | CTS 402k | 37% | KV-102 | ~168k |
| KV | kv3_hgi_v7 | 224.5k | proj 601k | 75% | KV-102 | ~79k (hgi cland w1560/1045/55x not yet in my set) |
| S81 | dsdv_slice_iq_C__t1 (+15 dsdv_*_C) | 384.6k | meas 621k / 1.40M | 20% | DIE-S81-92 | HARD-S81-DSDV-1 / TYPE-XS4 shared xs4 engine core (not duplicated here) |
| S81 | serdes__t1__clfe1f0815 | 315.7k | proj 638k | 0% | DIE-S81-92 | 72% u_core: harden u_core as child core (proposal; no kit yet) |
| S81 | slice_station__t36 (t37/t43) | 216.3k | place 452k | 99% ft | DIE-S81-92 | ft landing W1105/669/596/277/71 (DSREP8 LOCAL1 WNEG1) -> CLAND-MACRO-1 masters |
| QC | sle/slw_st_b_v1/v2 (4 types) | 361.8-377.3k | NEAR, route | 26-27% | DIE-QC-103 | ring children (W1575/653/537/457/517/259) -> ~265-277k; u_u_r# region blocks 135-141k as region cores like st_a |
| QC | sle_hc0 / slw_hc1 x2 / sle_hc2 / slw_hc2 | 345.7-376.1k | NEAR | 11-17% | DIE-QC-103 | rings (W1574/517/515) + u_u_xl 53k lane core |
| QC | slw_fw_v1 / v3 | 215.5k / 205.7k | GRT census 418-428k | 61-64% | DIE-QC-103 | rings -> ~80k |
| QC | cbn_q01__cld9ff4c40 | 251.0k | proj 676k | 26% (46% all rings) | DIE-QC-103 | rings -> ~187k |
| QC | sle_stm_v1 | 259.5k | CTS 311k, hold-structural fail | 37% | DIE-QC-103 | rings -> ~163k |
| QC | sle_ctl, sle/slw_st_a | >400k | - | - | DIE-QC-103 | already done by s29q103S ring children (QC-CORES-HEAD) |
| HEAD | none measured >400k (hd_lep0N plan est 365k) | - | - | - | HEAD-99 | watch only |
| HBM | parked (owner) | | | | | out of scope |

Estimate: hardened ring = 25 cells/bit (measured from cat_*.jsonl). Ring cores: 0 added cycles (exact parent parameters, drop-in), W-side instances placed mirrored MY.

## Cores (DEDUP with CLAND-MACRO-1 done 11-14 19:3x; merged set = lanes/handoff/KV-RING-CORES-MERGED.tsv, one master per exact params + face axis)
CLAND-MACRO-1 derives the face per instance from parent pins.json (ns = d S / q N, ew = d W / q E); my first wave was E/W-only, so most of it was the wrong face.
Stopped (dirs kept), mine: kv3_cland_w{1057_e_s35, 909_e_s31, 800_e_s27, 781_e_s27, 672_e_s23 (exit 1 FACE_GUARD land_slot), 653_e_s23 (exit 1 FACE_GUARD land_slot), 544_e_s19, 525_e_s19, 416_e_s15, 397_e_s15, 288_e_s11, 269_e_s11, 259_e_s11}, kv3_hcland_w{1119_e_s37, 300_e_s11, 268_e_s11}.
Stopped, CLAND-MACRO-1 (mine further along): kv_cland_w257_ew_69586 -> kv3_cland_w257_e_s11 (epyc10, CTS); kv_cland_w292_ew_abd47 -> kv3_hcland_w292_e_s11 (epyc8, place). Both mine have d on E = theirs mirrored MY.
Running, mine (OVERSIZE-1): kv3_cland_w257_e_s11, kv3_hcland_w292_e_s11, and 7 new configs nobody had, generated with CLAND-MACRO-1 mkmacro.py into /srv/opentallas-scratch2/claude/oversize-1/rk2/ (epyc8/9/10, configs.json there):
  kv_cland_w269_ns_0fea0 (pv_v1n x6), and hub_C (PLACEREP=1 rings, differ from hub_Wo): kv_cland_w300_ew_ba263 x2, w292_ew_81b3f x2, w549_ew_bf94f, w523_ew_05742, w294_ew_a7ae4, w259_ns_a43af x8.
Logs intel2 ~/tmp/oversize-1/logs/ (first wave) and logs2_<m>.log (rk2). Watcher intel2 ~/tmp/oversize-1/watch.sh covers logs/*.log only (first wave); rk2 builds: check signoff/signoff.json in each kit (TODO: extend watcher).
All other KV configs: CLAND-MACRO-1 builds (their status.tsv).
Correction: serdes__t1 is 72% flattened <top> logic, u_core is only 30k (9.5%); a u_core child alone does not fix it.

## Not yet built / next
- hg/hgi rings: all covered by CLAND-MACRO-1 masters (checked hg_v3, hg, hgi_v7 faces).
- QC st_b: u_u_r0..7 = 8x qfd_dv_s8_station_tail1_orq3 (HI_PAD29 NB_IN_PAD11 NB_PAD13 RD_PAD13 SKEW_N6 SKEW_S7), 141k = ~17.7k each: one region master x8 + rings -> st_b ~136k. Not built yet (needs registered-port check).
- QC hc: u_u_xl#_# 53k + rings 39k+26k; <top> 226k flattened still -> needs RTL split.
- kv3_hub_C engine split; serdes__t1 u_core child; QC st_b region cores + hc xl core.
- After SIGNED: export_view.py + archive to rtx-pro and AGIdock /archive (count from AGIdock).
- Parent rebinds are the die owners' plan events (KV-102 etc.); OVERSIZE-1 supplies the signed masters.

## Successor state (2026-11-14 ~20:20 PST)
- Waiters (intel2 ~/tmp/oversize-1, no LLM): watch.sh (first wave, final), watch2.sh (rk2), watch_sig.sh (rk2 w292_ew_81b3f/w300_ew_ba263/w523_ew_05742: intel2 clients died 19:57, units alive on epyc10; polls signoff.json), watch3.sh (QC st_b region kits, logs3/).
- KV rings SIGNED (AUTO-RESIGN rows in): kv3_hcland_w292_e_s11, kv_cland_w259_ns_a43af, w294_ew_a7ae4, w549_ew_bf94f. FAILED HOLD_STRUCTURAL: kv3_cland_w257_e_s11, kv_cland_w269_ns_0fea0 = OT_STB latest-sink target chasing ~1% fclk outliers (p99 ~530 ps) -> +~295 delay bufs -> hold -303/-316. ASKed Fable/KIT-OPS-5 review; A/B = resume from 4_cts with OT_STB_EST=placement. Not relaunched.
- QC st_b: ports registered except flt_*_i (face flop wrapper = sta_region_nb0 form w). 4 regions/type (r4..r7), 34.7k each. Built+queued epyc9: stb_region_orq3_h29_n6_s7, stb_region_orq3_h29_nb2_rd1_s8 (qcr/<m>/kits/<m>_synth0; generator oversize-1/mk_stb_region.py; plan rows qcr/<m>/plan_rows_<type>.json sent to DIE-QC-103). 5 other region classes pending these two.
- Corrected size attributions (anon ABC cells by net vote, attr.py): hub_C u_pvfin 267k (54%); serdes__t1 u_dec 172k + u_enc 68k (RTL split exists: OT_S81_RCK_REFORM); sle_hc0 xh0 56k + 8x xl0 27-31k. PLAN-ASKs posted to KV-102 (u_pvfin plan row needed before kit), DIE-QC-103 (hc lane masters), DIE-S81-92 (adopt RCK_REFORM + RCK core lane).
- QC stm/fw: per FABLE-TYPES-QC-EAST cause B, re-measure after relay_bay.py fix before any split.
- On SIGNED: export_view.py + archive AGIdock /archive/opentallas-signed-1114 + rtx-pro /home/ubuntu/signed-export-1114 (not done yet for the 4 KV rings).
- 20:17 u_pvfin: kv3_pvfin_s kit epyc9 oversize-1/kvr (generator mk_pvfin.py), slot from KV-102 kvgeom6 (1296,48) 501.12^2; waiter watch4.sh.
- STB-EDGE-1 proof: w269 resumed from 4_cts w/ stb_edge1.tcl (epyc10); stb_proof.sh auto-resumes w257 on pass; watch5.sh signoff.
- STB-EDGE-1: w269 SIGNED (TT +161.8, FF +3.0, DRC 0); w257 resumed 20:31 (watch5.sh).
