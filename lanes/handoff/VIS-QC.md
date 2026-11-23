# VIS-QC handoff (Opus 5.5, started 11-22 22:5x PST). Briefs: scratchpad visual_brief.txt + visual_brief2.txt (every unsigned QC type, die level, look-before-launch).
Work: local scratch /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/visqc (tools vq_extract.py, vq_dump.tcl/.sh, vq_render2.py; per-kit json/png); hosts /srv/opentallas-scratch2/claude/VIS-QC/{tools,tmp}.
51 unsigned QC types (OWNERS-SWEEP 22:51). Forks (background): st_a -> cov_sta.tsv/form_sta.md; cb -> cov_cb.tsv/form_cb.md; fe/fw+misc -> cov_fefw.tsv/form_fefw.md. Me: su family (6), coll_core, die-level, V4 composed plan floorplans before 06:00 -> tell OPUS-FIX-QC-V4-R2 PROBE-PASS/NONE-NEEDED.
## Findings so far
- slw_su_l1 cla2a78701 (epyc2 GRT, ovf 2244): single hotspot (455-510,170-320) = lpad_x_su_c_i 4596 + ist x_su_c_i lane4->5 4176 flops blobbed in the 69-um gap between u_lane4 E edge (x432) and landing macro u_cland_x_su_c_i (501-579,188-278); taps clk_t6 5677 @(441,220) and clk_t8 8741 @(480,400) on it. V5b re-seat moves x_su_c_i (571+503 bits) and p1 (256) station columns to x=436/501 in the same 190-um E channel -> risk of worse.
- slw_su_c cl19bb38ef (V1/V2, epyc10 GRT 75 h): hotspots (460-510,400-530) su8 E edge / su8-ch 34-um slit and (630-700,330-420) ch SW corner on the 129-um street where lpad_x_su_l0_i row (6780) crosses pd35/pd37 pad columns; taps clk_t46 6186, clk_t39 3839 on it. cap2b (SLWSLE) moves l0_p1_o/l1_p1_o stations off the street.
- slw_st_a_v2 cl9f076a5c: V overflow band y480-500 x450-555 below btab g_btb[2], along cland landing row. slw_st_a_v1 pvf82a6c28: global ~70% GRT usage, btab SE cluster + tall E cland strip.
- coll_core pkit_core4: hotspot (230-310,1150-1250) xs cone + ist_rec_tx_s0 between g_xf u_fs cores; 2nd (440-500,450-560) rec_tx_s1/s2.
## Die level (V4 l1r plan, plan_review pack epyc9 VIS-QC/renders/die_cores.png, die_wire.png)
- QC die 31216 x 25644 um (800 mm2; reticle 26 x 33 -> +1.78 mm width / +0.36 mm height available). 12 slice columns (E0-5, W0-5) in a 4.5-mm middle band (y 10.2-14.7 mm) carry all the lane wire; ROM arrays above/below are quiet. All unsigned slice types share 613-622 um widths (aspect up to 2.99 on stm/sc). Channel fraction only 2.3%.
- Cross-type cause: slice strips are too narrow for their bus columns (fe/fw stacked on spine; su_l1 E channel 190 um with mid-channel landing macro; st_a btab wall in E corridor). Die-level form VISQC-DIE-1 (proposal to QC plan lane, not V4): grow die width by up to 1.78 mm and give it to the slice band as +~150 um on one strip per slice column (fe/fw strip 622->778 per FEFW-1, or su_l1 622->700 + st_a corridor), ROM columns get a matching channel. Decide per column after the FEFW-1 / SU-1 probes show which width each needs.

## 11-22 23:5x update
- 51/51 QC rows have verdicts (commits 1f91d83, 293937c). DRAFT 45, NONE-NEEDED 5, PRE-PASS 1 (glue).
- cb family (17): VISQC-CB-1 form at lanes/handoff/VIS-QC-form_cb.md. Channel tap grid from placed sink bins (cap 900) plus margin landing re-site. GRT is not the blocker (overflow 707-4615); the over-cap taps line up with the pin-window hotspots at x~691. Owner: FAM-QC-CB-R4.
- V4 gate is unchanged. The cb types are held until a CB-1 probe passes.

## 11-23 00:1x CB-1 build (COORD: drive probes myself)
- Work dir epyc2 /srv/opentallas-scratch2/claude/VIS-QC/cb1 (fork tree = ot-tree-fork of V3 qwen_compute_v3p7c5rt, launch = rt f01b2d631780).
- Placed clock-sink dumps of 12 cb types (sink_bins_from_place dump, ot-run) -> cb1/bins/*.json; ODB copies cb1/odb (ot-delete after probes).
- Compose (step_b.sh): fable1 3916798ffca5 (CB-R4) + Row D chain affinity 64/150 (tap_radius_um kept: changing it re-sizes the density base and breaks added-tap names) + cbx bc_i30 re-site (517 keys x3) + VISQC-DIE-COLL-BANDS + tap_split --sinks-dir bins cap 900 radius 150 -> plan_c; + 11 st_a types of l0b with STA-1 (merge_sta.py, relay sites out of new halos) -> plan_d (CB-1+STA-1); + CB-R3 street on cbn_q00 cl622f65d2 (street.py) -> plan_s.
- Next: bind.sh cb1d plan_d (tree/launch) [+ second fork for plan_s], then probe kits (private-spec --goal grt --ab OT_PROBE_THROUGH=1) on cbn_q01__cldd6ea846, cbf_q01_s2, slw_st_a_v2__clf4365a62.
