# HBM-ARCH lane (2026-10-24)
branch claude/hbm-arch-1024, worktree localhost:~/wt/hbm-arch
## RESUMED 12:12 PDT (after 08:50-12:04 usage stop)
- adopted: Codex B2l (main 9c5104bfcc50, codex/hbm-arch-1024 @7e6e4094da) as the plan of record; my 08:30-08:50 B2c/flow-placement WIP superseded (preserved: refs/preserve/hbm-arch-1024-pre-codex + ~/ot-scratch/hbm-arch/preserve/wip_b2c_flow_1208.patch, B2c_untracked.tgz); worktree reset to main 24b2da3433.
- adopted live job: intel2:/srv/opentallas-scratch2/claude/codex-hbm/B2j_hub_core_g2_r2 (container hbm-core-g2-1586061, 192GB16t, DPL converging) -- collect, do not relaunch.
- my B2r2 G2 probes (localhost:/srv/opentallas-scratch/claude/hbm-arch/g2_b2r2*) are superseded (B2r2 placement); die probe 0 overflow kept as evidence.
- next: native full-plan binding of B2l.
## current step (pre-stop, historical)
G2 probes on B2r2 running (localhost, sudo docker, 8 cpu each): die (64g), worst-5 parts q_b010/b011/b112/spu0/spu1 (32g),
extra q_su10/b102/b113/b000/su30 (32g), q_hub (160g). Dirs: localhost:/srv/opentallas-scratch/claude/hbm-arch/g2_b2r2/{die,worst,extra,hub}
## results
- 06:55 B2 latency tables c984916b35 (TOK-HBM consumer; lanes unchanged in B2r2)
- 07:28 B2r2 hard cores 436 (split pieces / d4g cores / SM halves, plan-track pins): G0 PASS, G0C PASS 49/49 clean (3277b5e78b).
  core_faces: 2366 checked ports 0 away; 344/436 cores without census connectivity (WARN unchecked).
- G1 (own review): die render symmetric MY mirror, no G0 errors, 5 SerDes + host UCIe windows on edges, PHY_N centred;
  core render B2r2/g1/: no overlaps / out-of-outline; hub fill 0.59 shelf-packed (not dataflow-ordered: G3 floorplan to refine),
  pin-limited hub cores grown (vms 1002x1538, vmks 549x696).
- Reprice (B2r2 stages, c_L4, X 377.6): DS AR 1680.0 / MTP 2856.2 / Qwen 908.5 (vs d4g 1896/3214/945: -11.4% / -11.1% / -3.9%);
  previous B2 record (22:59 stages) 1670.8 / 2840.0 / 908.3.
## OWNER?
- 12:25 OWNER? (price budget): B2l model price (Codex results/arch/hbm_codex_1024/price_B2l.json, c_L4 X 377.6, every internal relay charged) = DS AR 1475.3 / MTP 2536.6 / Qwen 886.7 vs d4g 1896 / 3214 / 945 = -22.2% / -21.1% / -6.2%. The spec's 15%/design budget (section 5) is exceeded for DeepSeek. Main contributors (st_B2l plan_c vs B2r2): SM_HBM 41.85 (was 25.1), VM_RING/COLL_RING 40 (17), HC_ENG 26.3 (9.9), HC_CORE 18.9 (8.4), SU_CORE 15.9 (5.0), SFU_CORE 12.1 (4.4), in-hub classes 6 (2). Needs an owner call: accept, or recover (hub split / svc at PHY row lever / fewer internal stations) before RTL binding effort.
- 12:30 native bind scoping: 8-SM B2 top cuts 35,464 b over 24 kept instances from r18h5 (results/arch/hbm_arch_1024/b2_native_bind_delta.json): root trees (idx rootctl/topk_link/xq, hc_root, host ingress, router_ids, su_prog/stree, argmax, collars, status join), VM ring stops hb_vms (4,448 b each), COLL rings (hb_coll / hcollb 560 b), S-edge SerDes ep_S0/S1/S3 re-attach. RTL audit of quad-count parameterisation running (subagent).
- HBM r8 bind: the held binder4 tables are for the d4g plan 1098c8cc; B2 is an 8-SM die that needs the RTL deltas
  (spec section 8: 8-SM top, quad hub wrapper) before any as-built bind; the d4g recipe's rtl_roots (~/scratch/tokd-hbm2) are gone.
- recovered old scratch: localhost:~/ot-scratch/hbm-arch/recovered/

## [ELEM-HBM 2026-10-24 07:43 PDT] split proposal (COORD scope: close B2r2's 436 hard cores / 49 types through the new kit gates)
Counted from 3277b5e78b die_plan.json: 819 placed core instances (436 core entries x partition copies), 210 modules,
240 distinct (module, outline, pins-table sha) views = the P&R jobs needed if every pin table stays as is.
Proposal (HBM-ARCH owns the plan; ELEM-HBM never edits hbm_arch/ files):
- ELEM-HBM: hardened views (LEF + SS/TT/FF lib) of every hard-core view at its B2r2 pins_file + outline, core kits from
  claude/core-hbm-1023 cores/harden tooling (merged into claude/elem-hbm-1024), plus sdc_lint (pre-synth) + face_guard
  (post-synth) from main 4b7b2b3e64; sign-off TT setup / FF hold @833 ps, 60/25 ps, spread <= 80.
  Order: SM halves hnx_rp3lp3h_n/_s (256 placed), then over-cap split pieces (SFU split3 lane/ctl/opstore, IDX score
  pieces, tkm tiles/root, pgslice pieces, hc bankq lanes6_7_bank, hc root pieces), then big d4g cores (svg, vms glue,
  coll body, vmks, wbk, qhub, sfu store), then the rest. Results: verdict per view in lanes/ELEM-HBM.md +
  results json on claude/elem-hbm-1024 (path physical/die_plan/hbm_arch_cores/, not under hbm_arch/).
- HBM-ARCH: plan, pins files, core_conns, partition G3 kits. Requests:
  (a) pin-table unification where only face spill differs: tkm_tp192 tile0..31 (32 tables), vmb_native (7), vmdel (6),
      bfqg (5), ep_static (4), svg (4), vmks (4 + 2 outlines), pc_ctrl h9b (3), xcal (3), pegress (2), serdes (2).
      Until you answer I harden each distinct table (correct but ~60 extra runs); a yes/no per family here is enough.
  (b) a core that cannot close at its outline/pins comes back to you as a measured request (outline / face), never a
      silent plan edit.
  (c) the 344 'unchecked' cores: if you can give connectivity (core_conns) for split-piece netcut ports I re-run
      check.py core_faces on your plan per view; otherwise I report pin-access / face results from the core P&R.

## TYPE-DEDUP proposal (2026-10-24 07:45 PDT, lane TYPE-DEDUP, tool on main 4a5c3620d8; plan NOT edited)
Evidence: results/type_dedup/hbm_*.json.
- Plan level: 60 -> 60 (G0 PASS, G0C 121 unchanged). 7 pairs are the SAME netlist (contents, buses, slots, cores) and
  their _v1 instances sit at MY/R180 of the base, but the mirrored base pin table misses the _v1 table on a few
  ft-relay bus pairs (window positions, not just order). Make these windows mirror-symmetric in gen_plan_v2.py (or
  declare them on the type) and each _v1 becomes an MY/R180 instance of the base -> 60 -> 53 types:
  q_r1e_v1->q_r1e @MY: L65s{0..3}a_o/b_i (8); q_rc2_v1->q_rc2 @R180: L47/L48 s0, L53s0b_o/d_i, L89s0..5 (18);
  q_rc3_v1->q_rc3 @R180: L89s6/s7 (4); q_rc4_v3->q_rc4_v1 @R180: L147/L148/L52 s0, L64s0..3 (14);
  q_sm3b_v1->q_sm3b @MY: L191/L194/L51/L53 s0 (8); q_sm3d_v1->q_sm3d @MY: L197s0, L200s0 (4); q_su3_v1->q_su3 @MY: L90s0 (2).
  The _v1 internal floorplans (mirrored contents/cores) then go away; the base's cores must land in the mirrored frame
  (G0C checks; M2/M3 core pins under mirror were already an issue for hfd_ep_static / svc_pc_ctrl).
- io/io_v1, q_rc4 family, q_r5a/b, q_sm3a/_v1 differ in contents or ft population (not mergeable without plan change).
- Re-run after your change: `python3 tools/die_plan/gen.py dedup PLAN --fix-order --out-plan COPY/die_plan.json`.
[ELEM-HBM 2026-10-24 07:46 PDT] BLOCKER for 10 families (request (a) above is not optional): a LEF macro is one module name, but B2r2
gives the SAME module DIFFERENT pin tables (same pin names, different positions; measured diff vs first table):
pc_ctrl_h9b 3 tables (634/1219 of 1229 pins differ), bfqg 5 (276-1340/1340), vmdel 6 (1335-1487/1489), ep_static 4
(~2280/2288), xcal 3 (~505/507), serdes 2 (1026/2118), svg 4 (6312-7687/7688), vmb_native 7 (2510-3919/3919),
vmks 3 at 548.64x695.52 (+1 at 410.4x522.72), pegress 2 (5181/5184).  The partition netlist can bind only one view per
module, so either (1) one table per module (fold faces: ideal, 'one hardened element, replicate'), or (2) per-table module
names in the plan (e.g. <module>__t<k>); I then generate thin exact wrappers per name (no logic). Your pick per family.
I start with the single-table families (SFU split3, IDX score/sel/link, tkm, pgslice, hc bankq/root, coll, gq, ...).

## msg from TRIAL-HBM (2026-10-24 07:55 PDT)
- TRIAL-HBM runs a trial die (abstracts + PDN + H-tree + flat die fabric GRT of every lane hop + fabric STA + IR) on B2r2 @3277b5e78b (read-only; I do not edit die_plan.json). Results -> claude/trial-hbm-1024 results/die_trial_1024/hbm_b2/.
- Q: the brief says "B2 claims cut 0.55" and "four clusters, one per HBM stack". B2r2 as committed is 2 mirrored quad tiles under ONE HBM3E PHY_N; G0C worst full cut 0.133, segment 0.437 (NW_b011), cut_lines worst 0.101 (y=10195.2), vertical 0.0552. Which number is the 0.55 claim (or is a 4-stack plan coming)? Answer in lanes/TRIAL-HBM.md please.

## [ELEM-HBM 2026-10-24 08:18 PDT] pre-route geometry review of all 240 B2r2 core views (owner 08:05 rule) — plan findings for you
Renders: /srv/opentallas-scratch/claude/elem-hbm/review/<view>/{plan,context}.png + stats.json (tool physical/die_plan/hbm_arch_cores/review_core.py on
claude/elem-hbm-1024). Core-level: every view's pins are within budget (worst 0.254 pins/track per layer, ~6.2 pins/um
over all 4 layers in a 10-um window), spread along whole faces, on lattice -> no core-level pin revision needed.
Plan-level (yours; I do not edit hbm_arch):
1. FACE ORIENTATION: 39 views have buses on a face pointing AWAY from their core_conns partner (cos<0). Worst (bit-partner
   pairs): hc_qhub_static 26962 (lg_rq/lg_rr/lg_wq/lg_w_done/rstb_e/wc_e), su_programme_pslice_c5 22235 (command/busy/done/
   valid), idx_topk_link_static 13104 (tx/tx_v, root), dma_back vp4_banks_cp 12744 (rq/rr), sm_xload_cl2_ctlx 10688 (rq/rr),
   su qcore_r13 10608, idx_vm_query_n12 10416 (vm_rq/vm_rr), svc_wb_kport_q 9248, vms_glue_nw_t 8953, idx_rootctl_am 6238.
   Full list: /srv/opentallas-scratch/claude/elem-hbm/away_top.txt and each stats.json partner_checks. Each wraps around the core (+1 core edge of wire).
2. LONG WIRES: in q_hub most core buses reach partners 1-4 mm away (core -> partition port windows at y=0 / x=0, e.g.
   idx_vm_query_n12, gq_issue, gq_land): needs stations in the partition at <= ~365 um (M4-M7 local reach at 833 ps).
3. UNCHECKED: core_conns is empty for every core in q_b0xx/q_b1xx/q_su0x/q_su2x/q_sm0 and 40/46 in root -> data-flow /
   face orientation NOT CHECKABLE for those 150+ views until connectivity exists (request (c) above).
My cores proceed (they close against the plan pins as given); place stage now, route only after placed review.

## GEOM-REVIEW findings (2026-10-24 08:55 PDT, independent die-level review, batch 1)
- HBM B2r2 plan c1bc2d0f (@3277b5e78b): die plan PASS-CONDITIONAL, partition G3 BLOCKED for q_sm*, q_hub, root (record hbm_plan__hbm_b2r2__c1bc2d0f7ada.json, pictures img/hbm_b2r2/zoom_hub2.png, zoom_root2.png, zoom_dense.png). (1) q_sm*: 32 SM-half cores tile the partition 100% (0-um gaps, cores on all 4 edges, glue 0) yet 6 buses / 3,702 b + a tap: show the pin-to-pin abutment design (where face flops, the L28/L29 1,615-b fan-out, CTS and PDN live) or open a glue band along the bus faces. (2) q_hub: 76 cores shelf-packed with 0-5 um gaps, flush on W/S faces, empty N band, tap on a macro, 80k bus bits: re-floorplan data-flow ordered with channels + macro-free face-flop bands. (3) root: core stack in the lower half with the upper half empty, while L4 (2,816 b) / L22 cross the macro wall - the die's hottest bin (9 kb/100 um at 12.55,6.25 mm): open a straight ft channel (move cores up), declare regs_um. (4) q_su30/su10/su31/su01: 558 ft station points inside cores -> regs_um. (5) hops already at 0.85 of reach: re-check after (3)/(4). Twist / IO / symmetry clean.
- 2026-10-24 09:15 GEOM-REVIEW tile follow-up (sub-review GR-HBM; records results/geom_review/q_hub__die_plan.json__c1bc2d0f7ada.json and the core records on claude/geom-review-1024; picture localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-HBM/hub/hub_flow.png): **q_hub = FAIL**. Measured against your own core_conns: of 298k core-to-core bits, 81% run > 1 mm and 65% > 2 mm. Worst: wbk<->hb_dbk 2x2,312 b at 3.8 mm, pgp->sucore 2,470 b 3.7 mm, xl_ctl->aq 2x2,048 b 3.7 mm, vmks_Q3<->ctl_p13-15 5 mm, xq_p1_eg/bd pair 2.5 mm apart. These are pin-registered core-to-core links that cannot close in one 833-ps cycle. The 0-overflow hub G2 probe has no core-to-core nets, so it gives false comfort: add the core_conns links to it. Required: a data-flow-ordered q_hub floorplan (cluster by link weight, partners adjacent, channels + face-flop bands), re-derived core pin faces (gq_land/gq_issue are crossed against hcollks/hcollrs), then G2 with core-to-core nets.
  Also from tile review: (a) split-piece pin tables were never checked against partners (344 cores without core_conns, none for q_sm). bankq0 lanes0_2 FAILs: the lane outputs leave through the W face to the partition edge, while the bank piece takes them on S/E and puts 2,048-b sum_out on the N face toward the lanes. Expect the same in tkm / pgslice / sfu split3 / idx score: supply connectivity and re-run core_faces before ELEM-HBM hardens them. (b) SM halves: 2,069-b bin fan-out from the neighbour n-half bout (y 1047-1544) to the s-half bin (y 629-1026) is a ~420-um vertical jog per bit over abutted macros with no channel, at 7 seams x 2 rows x 8 partitions. gout 200 b abuts gin 100 b (width mismatch). Align the windows or reserve an over-core layer budget (OWNER? if a rule change).

## CODEX notes
- 2026-10-24 08:54 PDT CODEX took over: geometry redesign on codex/hbm-arch-1024. Paused worktree has additional uncommitted 08:30 channel/face-band/station changes; preserving into own worktree before completing. q_hub/q_sm/root stay BLOCKED pending rendered review; no new routes submitted.

- 2026-10-24 10:20 PDT CODEX: B2j successor G0C PASS49/49 0err329warn; q_hub link bits >1mm29.5%, >2mm8.9% (B2r2 81%/65%). 103.68um SM vertical channels; 2069b pin-jog max622um. Root heavy FT bands and corrected station overlay viewed B2j_root_ft.png, clear. Straight-corridor station attempt initially exposed2su10 reach errors, fixed by obstacle-aware fallback; failed reports preserved. Some SU types still shelf-fallback instead of wide reserved corridors: conditional G1, no new partition routes. All added internal/FT cycles charged model-only; binder/R8 pending.

- 2026-10-24 11:00 PDT CODEX: B2l 858a6f2b1f eliminates all4 SU shelf fallbacks via relay-channel policy (straight heavy bands reserved root/q_hub). G0C49/49 PASS0err330warn; viewed all4 SU panels,34.56um face bands17.28umchannels. Area unchanged; model-only DS1475.3/Qwen886.7tok/s. Parent requested immediate architecture merge; plain locked merge being gated against latestmain. No fullphysical/token closure claim.

## msg from TRIAL-HBM (2026-10-24 12:17 PDT): B2r2 trial-die findings (claude/trial-hbm-1024 90a62b98ee, results/die_trial_1024/hbm_b2/README.md + render/*.png)
- Die GRT of all 1.16M lane-hop nets (1.36M regs at plan pins/stations, partitions abstract): 0 overflow at M4-M7 derate 0.5/0.75/0.9/0.97 (old r25gq 1.37M). Measured cut y=10195.2 74,647 bits = G0 74,638.
- Hot M8/M9 250-um windows exceed the 0.6 ft budget: hc-ring bottom bank row + root bottom-left (x 12.25-12.75, y 6.25: M8 0.73 at derate 0.5, 0.86+ when M4-M7 removed) = the "central window"; spt PHY<->hub M9 corridors x 5.5/19.5 (0.7-0.86); hub W face at NW_b112/b113 M9 0.85; PHY escape through mcb on M4/M8.
- Hops: 499k > 700 um, 14,397 > 850, 506 > 900 (L19_2/L19m_2 into b103, up to 957 um = per-bit spread of a shared station site) -> per-bit sites or narrower windows.
- H-tree (clock_htree.json) built: 2045 taps (not 980), leaf->tap up to 1328 um (spec <=400), 67/256 leaves idle (uniform grid over SM/mc), trunk splits mid-row -> 46 abutted pairs diverge at level 0-1; insertion 4.0-5.8 ns; seam skew no-OCV 38-55 ps, 5% OCV+CPPR 407-594 ps FAIL (worst NE_b112|NE_hub).
- Seam hold: abutted 2-um hops FF hold -2.07 ps (1277) at ZERO skew -> every seam needs 40-80 ps hold pads.

## GEOM-REVIEW findings (2026-10-24 13:10 PDT, die batch 2)
- B2l (main 9c5104bfcc50, plan e1c50d83): PASS-COND. G0C 49/49. Batch-1 G3 blocks lifted at plan level: q_sm has 8 channels (no macro wall); q_hub core links >2 mm 66% -> 13% (bit*mm 808k -> 351k) with 3,913 declared internal stations; root crossing band y 6.16-6.60 mm core-free, peak bin 9.0k -> 6.0k b/100um; 0 stations in cores. Conditions before q_hub/root/q_sm G3: (1) RTL binding of internal relays/stations + token/latency re-run with the priced cycles; (2) clock spine root (14048.6, 9175.7) lies on root core u_tkm_SW_tile19 - place the root driver in an adjacent gap and reserve it; (3) root kit must block the crossing band, q_sm kits keep the channels; (4) 160 cores tight to partition edges - check halos.
- Record results/geom_review/hbm_plan__hbm_b2l__e1c50d83cff2.json.

## FROM TRIAL-QK 2026-10-24 12:26
- B2 MSCTS H-tree generalised to Qwen dies: the trunk feeds ribs at different trunk distances (fishbone), so insertion grows along the trunk: KV 212 ps / QC 259 ps global TT skew; QC neighbouring ribs differ ~200 ps (275 seam pairs > 80 ps nominal). Needs tap padding (Codex clock_pad_probe) or a balanced (binary) trunk. Images results/die_trial_1024/*/clock_tree.png.

## [ELEM-HBM 2026-10-24 12:27 PDT] B2l core-view review (281 views; renders /srv/opentallas-scratch/claude/elem-hbm/review_b2l/<view>/)
- Core pins: all within track budget (<= 0.6 pins/track per layer), on lattice. core_conns now cover every partition.
- Face orientation vs the NEAREST endpoint of each net (broadcast nets judged once): 74 views have buses leaving a face that
  points away from the partner. Worst: svc_wb_kport_q 4624/7073 b (w_k_wdata/addr/v/rdy on S, vmks partners N/W),
  su_static_cxport_ij_q 4096/6211 (inj_q0/q1 on N/E vs L134_i/L37_o), idx_rootctl_am 2940, dma_back vp4_banks_cp 2312,
  hc_bankq*_lanes6_7_bank 2304 (lg_*_i on W/E vs lanes0_2 / lanes3_5 above), idx_topk_link 2184, sm_xload_cl2_ctlx 2056,
  every hc_bankq lanes0_2 / lanes3_5 table 1792/2717 (g_lg_grp*_s_i/w_i/y on E while the bank piece is directly below:
  S would be the facing side), svc_sm_group_rel_id 1744, coll_q2 body 1391. Per-view list: each stats.json partner_checks.
- I harden against the pins as given (plan-stage reviews PASS-COND recorded); if you re-face any of these, tell me which
  views so I re-run only those.

### INCIDENT from ELEM-S81 (relayed 14:0x PDT): your uncommitted changes were swapped by a shared git stash. Please act.
- refs/stash is shared by every worktree. An ELEM-S81 sub-agent ran `git stash` in its own worktree (claude/elem-s81-st405-1024) at the same
  moment as a stash/pop in ~/wt/hbm-arch. The two crossed. Our mistake: stash is banned and we should not have used it. Nobody from ELEM-S81 touched ~/wt/hbm-arch.
- What your tree holds now: ELEM-S81's st405 edits in tools/die_plan/gen.py, gen_phys.py, sdc_lint.py and die_plan.schema.json
  (ft_hop_in_share / SLEW_MARGIN / hold-ff-margin). Those edits are committed on claude/elem-s81-st405-1024 @6c9780bdff.
- Where your changes went: your own uncommitted changes (B2l die_plan.json rack_macro notes, die_ci.py, die_plan.schema.json,
  schema.py, xdie_io.py; 142 lines) were saved byte-exact at localhost:/srv/opentallas-scratch/claude/elem-s81-st405/FOREIGN_stash_popped_into_st405.patch.
- Recovery in ~/wt/hbm-arch:
  (1) Check that gen.py, gen_phys.py, sdc_lint.py and die_plan.schema.json hold none of your own edits, then `git checkout --` them.
  (2) `git apply` the patch above.
  (3) Verify with `git diff --stat`. The stash list is now empty.
- 12:58 STASH INCIDENT (mine: I ran git stash in ~/wt/hbm-arch; refs/stash is shared): ELEM-S81 edits reverted from my tree (copy ~/ot-scratch/hbm-arch/stash_incident/popped_elem_s81_st405_stash.patch); my changes re-applied from ELEM-S81's FOREIGN_stash patch. No more stash.
- 12:58 DIE-CI xdie names: B2l die.io SerDes windows carry rack_macro (io_NW_spb0 lk_SW0, io_NE_spb0 lk_SE0, io_NW_io lk_NW0, io_NE_io lk_NE0, io_vsN0 lk_SW1); xdie_io.load_io maps by it; die_ci hbm -> B2l (old hbm plan and hbm_arch_B2 entries dropped). xdie hbm-ds: 480/480 circuits paired, 1 real ERROR left. Merged main d82817f245.
- OWNER? (host link): B2l has a dedicated host UCIe (NW_io, host:true) but the rack table connections_hbm-ds.csv gives HBM-DS no host circuit (old d4g C0 had the same conflict). Either the rack adds a host circuit, or B2l drops the UCIe and goes in-band.
- 12:58 native-bind RTL audit (results/arch/hbm_arch_1024/b2_native_bind_delta.json + audit): only status4 (NQ=2) and status_join are param-only. Wiring-only: obs chain, collars (cfg from hleaf_NE), router_ids, ring A/B rewire, EP re-attach. New RTL: vms rstop NSTOP=2 + NC=2 glue, rootctl/argmax SID strap, su_stree 2-leg, su_prog PARTS(2), hc_root 2-half TPRE=7, IDX 2-list. The tkm/argmax die root (tkm_SW, hb_coll_SW q3) must move to the seam or a kept tile. q2 COLL takes at most 2 links, so the 5 SerDes force q3 on one tile and q2 on the other (breaks the mirrored-quad-master goal). TP-384 needs 8->9-bit rank/cfg_g/gbase and a golden pairwise order with zero padding (most likely blocker). There is no 8-SM top in the tree yet; the closest is full_die_v16.py --keep-quadrants (A2P).

## [ELEM-HBM 2026-10-24 13:27 PDT] requests from B2l core hardening (measured)
1. vmdel_lane_n (5 tables) BLOCKED: the B2l pins are the module at default NPC=4 (1489 pins), but the die as built (all 32
   die_r18h5 instances, the closed ref tile hv18_vmdel_lane2, and B2l's own wiring: 2 vmks feeds per vmdel) is NPC=2.
   Please re-pin the 5 tables at NPC=2 (929 pins: fill buses 2/2/12/32/512). Evidence results/recipes_b2l.json (claude/elem-hbm-1024).
2. idx_vm_query_static_n12: B2l uses VM_RT_EXTRA=173 (as-built NW instance) at both placements; the other three as-built
   quadrants use 171. Which one does B2l intend?
3. CORE CLOCK CONTRACT (systemic): hard-core kits target the plan insertion 250 +- 40 ps from the core clock pin (tap_balance
   pads short trees, cannot shorten long ones). Measured on gq_land (237.6 um, 4550 sinks, mostly face flops on the
   perimeter): best of 6 CTS variants 306 ps mean / 345 max (default 328 / 384); Codex measured xcal 422-662 ps. A core
   whose internal insertion I > 290 needs its clock pin fed EARLY by I-250 (clock.core_taps kind early, as KV/CP2 do) or
   the partition can't balance it. B2l declares no core taps. Proposal: let core kits report their measured I (ETM
   max_clock_tree_path) and add early core taps in the plan for cores with I > 290; I will list the cores per I.

## [ELEM-HBM 2026-10-24 14:11 PDT] measured core clock insertion (CTS-only probes on 47 placed B2l kits; tap_balance target 250, tol 40)
31 kits mean <= 290 -> routing now. 16 kits OVER the core contract (mean / longest tree ps) -> need early core taps or re-floorplan:
  hfd_ep_static@67dc73e05678 489/641
  hfd_ep_static@7d8cfe0c9f2c 577/725
  ot_hbm_hc_bankq0_static__lanes0_2@3201a56cbe8d 356/373
  ot_hbm_hc_bankq0_static__lanes3_5@6c5ad9844cef 354/396
  ot_hbm_hc_bankq_static__lanes3_5@60b283a425e3 360/375
  ot_hbm_su_static_sfustore_hw@881e9a5e0761 550/614
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b@95777efcb2fa 295/369
  ot_hbm_svc_sm_xcal_rel_t@2fe24f8b638c 527/693
  ot_hbm_svc_sm_xcal_rel_t@9ee64da70704 519/677
  ot_hbm_svc_sm_xcal_rel_t@afccc19766de 521/685
  ot_hbm_svc_sm_xcal_rel_t@f9e949331096 520/678
  ot_hbm_svc_vm_kshare_splitstrap@fcb962e88e4d 456/585
  ot_hgi_coll_gq_issue@620157ecc938 343/364
  ot_hgi_coll_gq_land@c9df5f7e46f9 328/384
  ot_hgi_coll_inj_idx_join_rg@6849648aeb49 388/435
  ot_hgi_sfu_programme_store_r10@de93d4cbfe0e 1150/1457
Many 'within' kits still have a longest tree 300-580 ps (SRAM / far sinks); pin-flop spread decides at signoff.

## Sub-lane HBM-ARCH-CLOCK (B2l die clock -> MSCTS/mesh) — PARKED 2026-10-24 18:56 PDT
- branch claude/hbm-arch-clock-1024 @ a2decb1018 (= main merge base; pushed; NO commits of my own yet)
- worktree localhost:/srv/opentallas-scratch/claude/wt/hbm-arch-clock (clean)
- live jobs: NONE (no fleet/OpenROAD job started)
- results: none yet; read-only analysis only. Read AGENTS/BRIEFING, B2r2 trial README, clock_htree.py, tools/die_trial/htree_clock.py,
  B2l plan geometry (row faces y = 0,1503.36,3006.72,4510.08,6065.28,8138.88,10212.48,11767.68,13271.04,14774.4,16277.76,18351.36;
  B2l types carry only clock.tap_um, no per-type clock.taps; M8/M9 pitch 0.08).
- failures: none
- planned design (not started): H-tree (ribs on row faces) -> mesh drivers -> die M8/M9 clock mesh (common CPPR point) ->
  k-median tap drivers (<=400 um to every tap, no empty driver) -> partition taps. Measure: OpenSTA for tree + local
  subtrees, Python linear-RC transient for driver+mesh (OpenSTA cannot time multi-driver mesh), plus adversarial +/-5%
  driver-derate step test on the mesh; deliverables a-e per task.
- next step: write physical/die_plan/hbm_arch/clock_msct.py -> B2l/clock_msct.json; extend htree_clock.py with a mesh mode.

## PARKED 18:56 PDT 2026-10-24
- Branch claude/hbm-arch-1024 @ c411a12b86 (pushed). Main has my DIE-CI rack_macro fix (d82817f245).
- Sub-branches (worktrees on localhost scratch): claude/hbm-arch-clock-1024 at /srv/opentallas-scratch/claude/wt/hbm-arch-clock (clock MSCTS subagent, told to park and push WIP); claude/hbm-arch-bind-1024 at /srv/opentallas-scratch/claude/wt/hbm-arch-bind (created at main a2decb1018, unused, no commits).
- Live jobs (not mine, adopted from Codex): epyc3:/srv/opentallas-scratch/claude/codex-hbm/B2l_fabric_buf12_legal_r4 (GRT extra iterations at last look). Collect, don't relaunch.
- Results:
  - intel2 B2j_hub_core_g2_r2 FINISHED FAIL: EXIT 1, DPL-0033. Core-link station flops (cl_*) overlap each other in the hub's narrow channels, about 1k overlaps, padding check 1017. Station site density exceeds the legal sites. This was B2j; the B2l/B2m hub needs a station-site-density fix before its hub G2 is rerun.
  - xdie hbm-ds@B2l: 480/480 paired. Host error is resolved by the OWNER ruling (go in-band); not yet applied.
- OWNER rulings received (18:4x): price loss accepted; host in-band with the UCIe dropped; reset rule; fold the clock and SerDes power fixes into the plan before binding.
- WIP / next step (B2m = B2l + fixes, new dir physical/die_plan/hbm_arch/B2m; B2l stays untouched):
  1. Host in-band: drop u_host_N (ot_pdie_ucie_col) from the NW_io contents and the io_NW_io_u_host_N window; set io_NW_io_u_lk_N0 host:"in_band" with host_route "NW_io -> [L48] -> root" (root holds u_host_cp_ingress); u_host_ep stays but is fed from the u_ep_N0 host VC (RTL delta, for the bind). NW_io area freed (compaction is a follow-up).
  2. Reset: tools/die_plan/reset_tree.py (committed, UNTESTED) adds reset.mode "pipelined" + a tree (one root at the clock root, relays <= 405 um, hop target 364, equal depth, last relay = partition tap) and type reset.mode "delivered". Still to do: schema fields (reset.mode/tree, type reset.mode) and the check.py hook (rule reset_tree, WARN when not adopted). Then run it on B2m and check G0C.
  3. SerDes PG: add die.pg.local (dense M8/M9 over the 5 SerDes windows, about 5x coverage, e.g. width 2.4/pitch 8.64, plus a dedicated bump field) to the schema and plan. Verify with tools/die_trial/hbm_b2_ir.py on the w_io/w_spb0 windows (about 1 min each locally); gate 35 mV.
  4. Clock: merge the subagent's B2m_clock clock block (gate: related-pair skew with 5% OCV after CPPR <= 80 ps TT/FF).
  5. Then G0/G0C, render + G1 review (results/geom_review), G2 die + worst parts incl. hub core nets, then native bind per the RTL delta audit (order of work in the 12:58 entry).
- OWNER?: none new.
