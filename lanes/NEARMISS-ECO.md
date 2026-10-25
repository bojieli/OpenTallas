# NEARMISS-STRUCT (file name kept as NEARMISS-ECO.md; lane renamed by OWNER CORRECTION 2026-10-25 ~04:15 PDT)

Brief: routed release-die runs (last 72 h) that only just missed sign-off. OWNER CORRECTION: no hold-buffer / resize / LVT ECOs.
For each near miss: render the routed layout, find the structural cause, propose an industry-practice fix (safe-tile checklist),
post a GEOM REQ; rebuild only after GEOM PASS. No ECO job was launched by this lane (correction arrived before any launch).

## Census 2026-10-25 04:28 PDT
Source: every signoff*.json < 72 h under /srv/opentallas-scratch{,2}/claude on epyc1/epyc2/epyc3/intel1/intel2 (1531 files, git
worktree copies dropped; scanner rtx-pro ~/coord-scratch/nearmiss/scan.py, filt2.py). Near-miss filter: NOT SIGNED, TT setup WNS
>= -30, FF hold WNS >= -30, DRC <= 50, face_guard + sdc_lint PASS, no SIGNED run of the same kit. 46 kit names matched; after
removing superseded / owned / structural-known ones, 7 remain.

### Kept (structural review below)
| run (host:dir) | die | TT setup WNS/ep | FF hold WNS/ep | DRC | DRV | clock gate |
|---|---|---|---|---|---|---|
| epyc2:s81-kits/c3/dsdv_eng_rr_h0_c | S81 | +3.57/0 | -0.08/1 | 0 | PASS | PASS |
| epyc1:codex-s81-split/ot_s81sl_ve_s_k_m0 (m5 same) | S81 | +32.82/0 | -2.33/16 | 0 | PASS | PASS |
| intel1+epyc2:s81-kits/c3/dsfd_su_t_rxsf_c | S81 | -6.19/1 | -2.52/13 | 0 | PASS | PASS |
| epyc1:codex-s81-split/ot_s81sl_ve_m_k_m5 (m0 same) | S81 | +45.66/0 | -5.93/2 | 0 | PASS | FAIL TT pin-reg I 313.7 vs 250+-40 |
| epyc2:codex-s81-split/ot_s81sl_vn_b_k_m0 | S81 | +17.71/0 | -7.44/29 | 0 | PASS | FAIL spread 122/109, I 425 |
| epyc2+intel2:s81-kits/c3/ot_s81sl_vsw_c | S81 | -11.44/3 | -10.28/22 | 0 | PASS | FAIL |
| intel1:codex-hbm-face/argmax_route_base (hbc_ot_hbm_argmax_static_sw_vm_r2) | HBM | +37.90/0 | -18.23/758 | 0 | FAIL slew 262 | PASS |

### Skipped (reason)
- QC qfd_dv_s8x_vmr* (FF -12.7/107 etc.): lane QC-CQB owns (GEOM REQ 04:18, COORD VERDICT 04:19).
- QC qfd_dv_s8x_crh* variants: type SIGNED OFF 03:08 (Codex ECO, archived). qfd_dv_s8_crh_rp1* (FF -18.3): pair skew 95-114 ps in every variant = structural, already with QC lanes (COORD 02:31).
- S81 head hd_elemB_rb (c8_rcx_m5: TT +112.9 / FF +5.05, slew 1) and hd_elemA_rb: S81-HEAD/Codex head3 live line (elemA SIGNED 04:08).
- S81 rxsb_c, eng_rr_h1_c: SIGNED (codex-s81-core-eco 03:40, c3 03:19).
- S81 slice_station kitsB / kitsBmw / share016 / r4d (t1 t2 t7 t11 t13 t14 t18 t24 t30 t31 t33 t34): old async-reset views, not die-usable; superseded by the wavefront x24/x6 kits (GEOM PASS-COND 00:49/01:20).
- S81 legacy kl_dsfd_rstg_c / kl_ot_s81_sstn_payload536_c: canonical face_guard FAIL (CODEX correction 03:31).
- S81 ot_s81c_attn_hcore r2/r3 (10-24): DEC12 re-plan changes attn_hcore reset relays (plan changed).
- CP1 dp_col_h10_r0_p1/r1 (cp1P, codex-cp1-push): live successor (epyc1 ot-run cp1_reach405R col_h10_r0_p1__t1 route, 7 h) + Codex CP1 ECO line.
- KV dp_kv3_io_ft / _v1 (TT -6.8/-18.4, FF -7.7/-9.0): PROTO STRUCTURAL (4 ft slots hop > 405 um) -> KV-G3 plan change pending.
2026-10-25 04:34 PDT HBM-CORES: shared root cause data (GRT-vs-RCX clock): HBM argmax routed DB, FF, 7357 sinks: GRT-est (default ASAP7 setRC) minus RCX arrival min 27.2 / mean 36.1 / max 54.3 ps. Uniform R+C scale fit: x0.8 -> +13.8, x0.6 -> -6.6, zero-mean ~x0.665, p95 residual 10 ps. Tool (re-GRT on 5_1_grt.odb + estimate per scale vs an RCX arrival TSV): claude/hbm-cores-1025@4b722d3388 tools/die_plan/rc_fit.tcl. HBM-CORES claims all HBM hard-core runs (argmax, gq_land, svc_pc, ep_static, sfustore, programme_store, exp lanes, HC W128).
