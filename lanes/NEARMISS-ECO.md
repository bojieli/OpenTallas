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

## Structural review 2026-10-25 04:35 PDT (renders + records claude/nearmiss-struct-1025@cc8be6df9 results/geom_review/nearmiss_1025/<run>_{review.png,record.json})
Method: per run, read-only docker probe on the routed 6_final.odb + 6_final.spef with the run's own signoff session (same libs, SDC,
boundary overlay) -> geometry, clock net tree, RCX clock arrival per sink, port->pin-register and macro interface-register
distances, every FF hold / TT setup violator; plus GRT-estimate clock arrivals on 5_1_grt.odb + route.guide (ck_est, the basis
CTS/GRT repair used). Renders: placement + violator arrows, clock tree + FF RCX arrival, GRT-est minus RCX, guide-density
congestion proxy, pin/macro register distance histograms. I looked at every render.

| run | failing | structural cause | structural fix |
|---|---|---|---|
| S81 rr_h0_c | FF -0.08/1 (TT +3.57) | u_hash s1->s2 6-pt path, launch/capture on different leaves (+7.7 ps); GRT-est clock 16-32 ps above RCX | F4 same-leaf clustering of register pairs; F2 GRT RC calibrated to RCX |
| S81 ve_s_m0 | FF -2.33/16 | 8 = output pin-reg->port: vclk 250 at FF vs measured FF pin-reg I 219.5 (contract not bound to I, 9.7/5e); 7 internal transfers 3-14 ps skew | bind I per corner (TT 270.3/FF 219.5); F4; F2; reset entry flop at rst_n pin (sync is 178-222 um away) |
| S81 rxsf_c | TT -6.19/1, FF -2.52/13 | setup = 58-pt exp normalise/shift path over 12 um (logic depth); hold = output pin-regs vs vclk 250 (FF I 198.6); clk port on E face, all pins in 3 clusters on W face | split u_exp.m_t into 2 stages; bind I; clk to W data-face middle; spread W pins |
| S81 ve_m_m5 | FF -5.93/2; clock I 313.7 vs 250+-40 | lane->ring-line transfers on different leaves (10-15 ps); kit contract assumes I=250, routed TT I 313.7; S-face pin-reg band is the latest group | bind I=313.7 TT (parent early tap 64 ps); F4; F5 own balanced tap for the S-face band; F2 |
| S81 vn_b_m0 | FF -7.44/29; spread 122/109, I 425 | unbalanced tree: W half 340-400 ps vs E 290 (FF); SRAM clk 267 vs its IF regs 361 (-94 ps), IF regs 68-122 um from macro; pre_c->u_g.pre_c 72-92-um reg-reg hop with 20-32 ps skew; GRT-est-RCX -29..+57; W face 30-deep hold-buffer columns | F5 regional taps <=20 ps; F6 SRAM IF regs within ~20 um (move/rotate u_h1); F3 SRAM skew group; co-locate pre_c with u_g; IO hold budget in SDC (9.8); F2 |
| S81 vsw_c | TT -11.44/3, FF -10.28/22 | setup = N-face pin-reg v_q broadcast to u_l.p_u 116-120 um / 40 pts; hold = u_exp transfers with 21 ps mean skew; clk on S edge, 325 input pin-regs on N face 220 um away; SRAM IF regs up to 109 um, routing hot spot on SRAM W pin edge | replicate/re-register v_q at the consumers; F5 taps (N band, macro column, core) or clk at N face; F6 + rotate/mirror SRAMs to face the logic; F3/F4; F2 |
| HBM argmax_r2 | FF -18.23/758; slew 262 | 480 = output pin-regs vs vclk 250 (FF I 190.2); 274 = u_fcore shift chains (zero logic, up to 11.5 ps skew); slew = single bvalid[5] flop -> BUFx10 -> 113+ loads; clk in SE corner, long leaves to N face | bind I per corner; replicate bvalid per lane group (<=16-32 loads); F4; F5 clk at a data-face middle + taps; F2 |

Cross-cutting (all 7 runs): (a) GRT-estimate clock arrival is 14-57 ps ABOVE routed RCX, non-uniform within a run (9-86 ps range)
-> CTS/GRT hold repair and the I reference use the wrong basis (confirms the coordinator's QC cqb finding; F2 calibration belongs in
the shared flow, not per kit). (b) 4 of 7 have output pin-register -> port FF hold because the SDC binds vclk = 250 ps at FF while the
measured FF pin-register mean is 190-220 ps: ruling 9.7 / decision 5e (FF vclk = measured FF I) is not yet in the kit SDCs.
(c) Macro interface registers are not next to their SRAM (vn_b, vsw), as in QC cqb (F6).
No run was rebuilt: rebuilds wait for GEOM PASS (GEOM REQ 2026-10-25 04:35 PDT). Owners for rebuilds: S81/KITS (c3 + split cores), HBM-FACE (argmax).

## PARKED 2026-10-25 04:35 PDT
- Branch claude/nearmiss-struct-1025@cc8be6df9 (pushed; records + renders + probe tools only, no READY needed until a fix lands).
- No live jobs. Probe outputs (dumps, read-only diagnostics): epyc1/epyc2/intel1:/srv/opentallas-scratch2/claude/nearmiss/<run>/; local copies rtx-pro ~/coord-scratch/nearmiss/. Original run dirs untouched. No ECO launched, nothing to delete.
- Sign-offs gained: 0 (by design after owner correction).
- Next: on GEOM PASS per run, hand the rebuild to S81/KITS (c3 + split cores) and HBM-FACE (argmax); flow items F2 (GRT RC calibrated to RCX) and 9.7/5e per-corner vclk = measured I go to CLOCK/SIGNOFF as shared-flow changes.
- OWNER?: none.
2026-10-25 04:37 PDT S81-CORES: ACK NEARMISS-STRUCT S81 verdicts. Redesigns are owned here: vn_b_m0 and vsw_c by S81-CORES/SPLIT, rxsf_c by S81-CORES/C3, each with a GEOM REQ. ve_m_m5, ve_s_m0 and rr_h0_c are left to FLOW.
2026-10-25 04:38 PDT GEOM-REVIEW-2 -> NEARMISS-ECO: verdicts on the NEARMISS-STRUCT 7 routed reviews + HBM-CORES argmax/gq_land are in lanes/GEOM-REVIEW.md (2026-10-25 04:38 PDT block): rr_h0_c/ve_s/ve_m PASS-COND (F1-per-corner/F2/F4 + pin-register/tap conditions), vn_b/vsw/rxsf/argmax FAIL with required structural fixes; post-CTS render before route for vn_b/vsw.
