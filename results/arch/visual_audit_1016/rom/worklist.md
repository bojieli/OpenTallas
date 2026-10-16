# VIS-ROM worklist: every open finding, grouped by owner (2026-10-16 ~03:30 PT)

For parallel execution, use one helper per item. Sev: 1 = blocks closure, 2 = costs timing/congestion/area, 3 = waste/low. "partial" = owner already partly fixed it.
Gains are the measured figure from the audit (see `findings.json` for full evidence and images); closure items are counted as closure, not ps.
Total open items: 54. Closure-blocking status is tracked separately in `status.md`.


## Q-COMPUTE-DIE (5 items)

| sev | id | item | state | expected gain | dependency | suggested helper |
|---|---|---|---|---|---|---|
| 1 | D-QC-02 | DIE r2b2 net n_rst_field (rstseq_rom.rso_f) | open | closure: removes 1,585-terminal reset net (r2b2 worst path -13.3 us) if not already fixed in FULL mode | r2h1/r2h2 GEN output | helper: read r2h* GEN reset_over_500 + fix xcol/xcol_e rst_n INOUT in generated LEF |
| 1 | QC-01 | qfd_tile_nk (rp2_45_a2 repack) | confirmed | closure: 92 illegal cells -> 0 (768-instance NK tile) | QC-11 lint exemption before r4 | helper: r4 NK repitch kit + gate; target DPL 0, W band >=40 um |
| 1 | QC-02 | qfd_tile_nl (rp2_45_a2 repack) | confirmed | closure: 53 illegal cells -> 0 (NL tile) | QC-11 | helper: NL tap glue into empty NE slot + ROM-top band widen; gate |
| 2 | D-QC-01 | DIE r2b2 (GRT running E4) / r2f2 plan | confirmed-partial | area: candidate (a) -53 mm2 done at plan level; (b) centre trim up to ~25 mm2 more | r2hs GEN/GRT; producer masters for the area above su64 | helper: run r2hs GEN+GRT; second helper: price centre trim (b) |
| 2 | QC-11 | qfd_tile_nk_rp2_45_a2 / qfd_tile_nl_rp2_45_a2 (r4 kit) | open | unblocks QC-01/02 r4 gate (3 lint channel FAILs) | none | helper: extend abutted_stack lint to E-W pin-free abutment + test; 1 small PR |

## Q-DVM+LINK (2 items)

| sev | id | item | state | expected gain | dependency | suggested helper |
|---|---|---|---|---|---|---|
| 1 | QC-05 | qfd_xs_tap | confirmed | closure: native capture 502 ps -> <=190 (route pending) | xt10 route | helper: collect xt10 route + native audit; N-band congestion check |
| 2 | QC-04 | qfd_d2d_static | open | timing: r1 hold S band 76 ps late; r4 gate clock ins 417-501/spread 84 over the 300/80 rule | r5 gate | helper: r5 gate->route + native audit; cancel r4 if r5 is clean |

## Q-ELEM (13 items)

| sev | id | item | state | expected gain | dependency | suggested helper |
|---|---|---|---|---|---|---|
| 1 | QKV-02 | qkd_ectl_a_tp8_epoch_direct | open | closure: ectl_a manual recovery stuck at 4 DRT shorts for 53+ iterations | none | helper: ectl_a re-pin kit (row buses split over both SRAMs, rs on two layers) + gate |
| 2 | QC-06 | qfd_crom_g | open | timing: SS -333 ps path from bottom ROM (~450 um reach); 729 N pins at 9.6/um | none | helper: crom_g re-kit: spread N face on M5(+M3), clock at column centre or 2x3 ROM arrangement; gate |
| 2 | QC-07 | qfd_sp_band_lanes | open | closure: newest full-tile runs failed hold; channel 19 um / row gaps 16 um congested | none | helper: band_lanes re-place macro columns (centre channel ~40 um) + gate |
| 2 | QKV-05 | qkd_embgw | open | closure (bind): routed embgw has 4,143 pins + N face vs die abstract 3,541 pins, no N face; E/W 8.7-8.9/um | die abstract | helper: re-pin embgw from die LEF + gate |
| 2 | QKV-06 | qkd_ctrl_pc | open | timing+area: E 617 pins squeezed into 46% of face; fill 0.24 -> shrink 246x173 -> ~200x150 (~-30%) | none | helper: ctrl_pc re-pin + shrink + gate (128 instances: ~1.6 mm2 saved) |
| 2 | QKV-08 | qkd_astk (astk_pv_tp8 leaf) | open | timing: astk_pv_tp8 fill 0.60, N/S 9.4/um, NE-corner clock | none | helper: grow ~180x130 + spread N/S + centre clock; gate |
| 2 | QKV-09 | ot_qkh_lane8 | open | timing: lane8 (2,048 inst) native launch 233 ps on 30 pins; NW-corner clock, fill 0.635 | none | helper: lane8 clock to E-face centre, util <=0.55; gate + native audit |
| 2 | QKV-10 | qkd_pv_join (ot_qwen_tp8_pv_join_t) | open | timing: pv_join r5 FF -5.2 ps after route (hold ECO running); E 1,540 pins at 9.4/um | r5 ECO result | helper: if ECO fails, move y output off E; re-gate |
| 2 | QKV-11 | qkd_ectl_c_tp8_direct / qkd_ectl_b_tp8_direct (h13) | open | timing/congestion: ectl A/B/C row pins misaligned (B left half, A right half) -> parent faces jog | none | helper: align A/B/C row pin x columns + parent check |
| 3 | QC-08 | qfd_su_cbuf_g | open | timing (small): NW-corner clock on 194x216 tile | none | fold into next cbuf_g touch |
| 3 | QC-09 | qfd_tt_scale_leaf (Q-ELEM scale tc1) | open | area: fill 0.148 on 345.6x216 (shrink ~-40% per instance) | instance count / die slot | helper: scale-leaf own outline ~200x216 if instanced; else skip |
| 3 | QC-10 | qfd_tt_core_leaf | open | area (low): fill 0.198; optional 260x216 | none | skip unless die area binds |
| 3 | QKV-12 | qkd_cdc_wleaf / qkd_host_rt(host_ctl) / qkd_pv_ctl / qk | open | small: pv_ctl S 10.6/um, host_ctl fill 0.12, land_emb_ifw hot window | none | fold into next touch |

## Q-KVSYS-DIE (7 items)

| sev | id | item | state | expected gain | dependency | suggested helper |
|---|---|---|---|---|---|---|
| 1 | QKV-01 | qkd_pv (PV 2x16 block: pv_slice/pv_join/pv_ctl) | open | closure: PV column 321.9 um too tall for north slot; south spine 1,287 um vs 1,598 needed | kvs11 trial; relay re-plan | helper A: zero inter-slice gap screen (8,294 um) + case; helper B: split-PV case with south arrays shifted ~160 um |
| 1 | QKV-03 | qkd_d2ds (qkd_d2d_static) | open | closure: 45 GRT overflows in 20 um SRAM channel (M4 34, M5 11) | none (tile cap M5: widen channel, no M6) | helper: d2d_static re-place SRAMs (channel >=40 um or outer-edge SRAMs) + gate |
| 1 | QKV-04 | qkd_rly_* family (relays) | open | closure/congestion: every KV relay at 20.9 pins/um M4-only (rly_2089 x61, 1025 x252, 1048 x82) | die abstract generator | helper: relay abstract regen <=8 pins/um/layer, two layers; re-run kvs case |
| 2 | D-QK-01 | DIE kvs11-v143c case (PDN) / kvs10 | open | area: spine S 13.9 + N 12.1 + corners 10.1 mm2 empty (~36 mm2) | QKV-01 decision | same helper as QKV-01 B |
| 2 | D-QK-02 | qkd_astk / qkd_astk_n / qkd_land / qkd_land_n | open | timing: astk->ectl_c links up to 9.06 mm inside a 220x9,675 um strip | parent hardening plan | helper: segment astk/land into ~1.2 mm replicated segments (plan + one segment gate) |
| 2 | QKV-07 | qkd_ahub (parent) / qkd_ahub_core | open | timing/congestion: ahub_core N 1,345 pins at 8.9/um half on M3; parent q8 failed hold | none | helper: ahub_core re-pin (half zh to S/W, M5+M7->M5+M3 cap) + parent gate |
| 2 | QKV-13 | qkd_static_kv_return_slots_mc (mc_r3) | open | timing: in->reg -69.5 ps, one reset flop -> 8,940 loads | none (running in loop as submitted) | helper: replicate rp[] per bank group (<=256 loads), outline ~160x180; re-gate |

## S-DIE (13 items)

| sev | id | item | state | expected gain | dependency | suggested helper |
|---|---|---|---|---|---|---|
| 1 | S81F-01 | dsfd_rly_283_EW (+dsfd_rly_266_EW, rebind target) | open | timing: rly_283/266_EW (3,042 inst) launch 243/237 ps from wrapping inputs; ~835k bits facing away | c26b GEN audit; S-NET+FILL L/U + WE views | helper: score c26b relay_face_audit.json; second helper (S-NET+FILL): build 283/266 WE + L/U kits |
| 2 | D-S81-01 | DIE VM-centred v2 plan (vmc2_plan) | open | area: hub band 161/315 mm2 white; HC_T ~10 mm from VM | hub v2 regeneration (gen26a failed twice) | helper: hub compaction study (HC tower on VM E face, SU_S under VM), price mm2 returned |
| 2 | D-S81-02 | DIE c21h (inherited, GRT running E4, iter 9/12) - colum | open | timing: 451-terminal column reset nets; INOUT abstracts | c26b GEN (--col-reset-tree, --lef-pin-dir) | same c26b scoring helper |
| 2 | S81F-03 | dsfd_node_LLfd (=LLfu canonical, LLd) | confirmed-partial | timing: LL nodes (2,417 inst) a/b still 18.4 pins/um in 7 um of W face, density 2.03 | S-NET+FILL re-kit | helper (S-NET+FILL): node a/b to E face, >=30 um span, clock at centroid |
| 2 | S81F-04 | ot_s81_cfg7_seq | confirmed-partial | timing: die-side 152 um cfg/go_e jog + 896 bit-reversed bundles (tile part fixed) | die placement | helper: co-place cfg7 under qbank_S.i_cfg; mirror qbank_S/q element with the FN pair |
| 2 | S81F-05 | dsfd_qbank_S | open | timing: qbank_S (1,898 inst) W-end clock on 60 um tile; N half empty; 896 reversed | with S81F-04 mirror fix | helper: qbank_S clock to S-face centre, height ~18 um; gate |
| 2 | S81F-06 | dsfd_rly_536_SN (RTL only, 898 inst) + dsfd_sstn_*_x2 | open | congestion: 156 bundles jog 74 um in a 6.2 um channel (536_SN vs sstn x2) | sstn window request (S-NET+FILL) | helper: window alignment in generator |
| 2 | S81F-07 | dsfd_rly_15_* (SN 786, EN 244, NS 439, WE 73, SW 30) | open | timing: rly_15_* 42-100% facing away, up to 338 um | S81F-01 generator fix | covered by c26b scoring helper |
| 2 | S81F-08 | small relay members with 100% facing-away: dsfd_rly_63_ | open | timing: small relays 100% facing away (63_EW load 697 um behind) | S81F-01 | covered by c26b scoring helper |
| 2 | S81F-09 | dsfd_m2l_vr_68x11__hr_E4 (rebind -> hr_W1, identical RT | open | timing: m2l hr launch 380 / capture 485 ps; SW-corner clock; 35% empty | none | helper: hr_W1 canonical re-kit: clock at sink centroid, ~158x100 um; gate + native |
| 2 | S81F-13 | dsfd_xstg_515 | confirmed-partial | congestion: 82 um jog in a 6.3 um gap xstg_515 -> bk_collector_c1 (tile native fixed: 356 -> 126 ps) | die placement | helper: align o window with bk_collector cSW or open gap >=36 um |
| 3 | S81F-14 | dsfd_rly_63_* (WE 8471, WS 5538, NS 5250, NE 2052, WN 9 | open | small timing: rly_63_* in/out bands offset ~4.5 um -> jog on every straight hop (21,000+ inst) | S-NET+FILL re-kit | helper: centre i/o band in the 63_* family kits |
| 3 | S81F-15 | narrow-bus relays/stations: dsfd_rly_2_* (5890 inst), r | open | area: ~2.2 mm2 of 1-6% fill narrow relays/stations | die netlist bundle merge (phase-3 dedupe) | helper: dedupe plan, later |

## S-NET+FILL (2 items)

| sev | id | item | state | expected gain | dependency | suggested helper |
|---|---|---|---|---|---|---|
| 2 | S81F-10 | dsfd_stnh_70x1 (2505) / dsfd_stnv_70x1 (1350) | open | congestion: 3,855 stations at 20.8 pins/um (every M4 track) | S-DIE plan with --stn-pin-pitch2 (c26b) | helper: route stnh/stnv_86x1 2-track views |
| 2 | S81F-11 | dsfd_sstn_e0c0si / e0e1c0c1si (and _x2 RTL-only, 476+74 | open | area: sstn fill 0.107 -> halve width (~90 um) | gen26a/c26b pin windows | helper: sstn re-cut after c26b |

## S-ELEM-PQ (6 items)

| sev | id | item | state | expected gain | dependency | suggested helper |
|---|---|---|---|---|---|---|
| 1 | S81F-02 | dsfd_cfifo | open | closure (bind): 68,864 die bits unbound (cfifo without xd2/xf2) | v2 RTL | helper: close cfifo v2 + rebind; place x2 under sinf x2i |
| 1 | S81H-01 | dsfd_host_c | open | closure: 22,965 hold violations from 4 unbalanced CTS roots | none | helper: host_c single-root clocking (or retime at ck_ingest->ck) + n5 route |
| 1 | S81H-02 | dsfd_stage_seq_static_c8 | open | closure: FLOORPLAN_MARGIN at 66% util | c10 RTL | helper: c10 kit at <=57% util + gate |
| 2 | S81H-03 | dsfd_bf_front_static | open | timing: bf_front c9 now TT -35.73 / FF -7.86; W/E 10.4 pins/um in 37% of face; SW clock | none | helper: c10 re-pin W/E full face, split N bus, centre clock; gate |
| 2 | S81H-04 | dsfd_sp_collective_static_c | open | area+congestion: vm_boundary 74% empty, SW knot from mismatched W/E bit order; 151 -> ~60 um width | none | helper: align W/E bit order + shrink; gate |
| 3 | S81H-12 | dsfd_ctrl (leaf dsfd_ctrl_pc) | open | area (low): ctrl_pc fill 0.14 | none | fold into next touch |

## S-VM (4 items)

| sev | id | item | state | expected gain | dependency | suggested helper |
|---|---|---|---|---|---|---|
| 1 | S81H-14 | dsfd_vm_static_wfc_ctl | open | closure: wfc_ctl refused (unsynchronised core->serial CDC: x43f, vm_fault, x34f) | none | helper: RTL CDC fix (static-schedule capture in core domain) + bench + gate |
| 2 | D-S81-03 | VM (MIX4 slot A + hop-1 + lever 2, adopted) | open | closure risk: VM cut exactly 0.600 (no margin), 98,672 leaf links >500 um | VM parent kit | helper: move 4-6k bits S/N -> E (E 6,987 vs S 19,288) in the parent kit; re-measure cut |
| 2 | S81H-08 | s81_a2f_field4 (dsfd_sp_vm child) | confirmed-partial | timing (residual): field4 W i_sel wall (672 pins one M4 column) | S-DIE pin grant | helper: i_sel W+S split kit if input hold tight |
| 3 | S81H-09 | s81_a2f_control4 (dsfd_sp_vm child) | open | area: control4 fill 0.19 -> 194 -> ~130 um (~8,000 um2 x4) | S-DIE slot change | re-pack item with the VM parent kit |

## S-FUNC (2 items)

| sev | id | item | state | expected gain | dependency | suggested helper |
|---|---|---|---|---|---|---|
| 3 | S81H-05 | dsfd_sp_hc_c / dsfd_sp_hc_t (HC kit ot_s81_hc_ctfl_nt) | open | area: ctfl_nt 88% empty (576 um wide, pins in 20%) | none | fold into next HC re-kit |
| 3 | S81H-07 | dsfd_sp_hc_c / dsfd_sp_hc_t (HC kits ctfn_nt / ctfs_nt  | open | small timing: ctfn/ctfs/ctfnq3 flops walled on N face (p90 density 1.12-1.14) | none | only if HC row timing tightens |

