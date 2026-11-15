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

## Cores launched (OVERSIZE-1 kits, QC gen_core_kit_qc.py recipe; lane dir /srv/opentallas-scratch2/claude/oversize-1/ on epyc8, epyc9, epyc10, same content)
Kit: rk/<m>/kits/<m>_synth0 ; generator mkcore.py (args: name W RSTREP H(0=auto) Wd CSC WRITE_CHUNK); RTL rtl_kv/ (ot_dp_clk_landing_ca.sv 78c7d01d, ot_dp_clk_landing.sv 15ffde74, ot_meso_fifo.sv ab1a4d96 = kvgeom4 kits).
KV pv/hg family (CSC1): kv3_cland_w1057_e_s35 (49.68x217.728, 40 inst), w259_e_s11 (40), w257_e_s11 (26), w288_e_s11, w416_e_s15, w397_e_s15, w269_e_s11, w909_e_s31, w781_e_s27, w653_e_s23, w544_e_s19, w525_e_s19, w800_e_s27, w672_e_s23.
KV hub family (no CSC, WRITE_CHUNK16): kv3_hcland_w300_e_s11, w292_e_s11, w268_e_s11, w1119_e_s37.
Launch: intel2 ~/tmp/oversize-1/logs/<m>*.log (ot-run --mem 32/48 --threads 16 --hosts epyc8,epyc9,epyc10 -- run_kit.sh K finish; run_kit runs signoff.py tt,ff).
Watcher (no LLM): intel2 ~/tmp/oversize-1/watch.sh, 10-min loop -> status.tsv; adds one AUTO-RESIGN.tsv row per SIGNED (signed.done).

## Not yet built / next
- KV hgi rings (w1560_s51, w1045_s35, w553/550/549/524_s19), hg extras (w1063_s35, w573/523_s19, w652_s23, w268 CSC1), hub_C W259 no-CSC / W549 / W523 / W294.
- kv3_hub_C engine split; serdes__t1 u_core child; QC st_b region cores + hc xl core.
- After SIGNED: export_view.py + archive to rtx-pro and AGIdock /archive (count from AGIdock).
- Parent rebinds are the die owners' plan events (KV-102 etc.); OVERSIZE-1 supplies the signed masters.
