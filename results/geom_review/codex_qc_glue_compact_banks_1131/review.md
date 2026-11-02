# Same compact option: explicit native CA bank assignment

Status: one source/geometry assignment, personally viewed, not adopted. No GEN, CAD, source/model/default or layout change. The completed B database and PRE-D13 canonical event remain immutable.

Six actual D2D input CA banks move from north M5/M7 to proposed west M4/M6: 1,200 data-plus-epoch contacts. This is an explicit parent boundary, layer and incoming clock/FSTART physical event, not an existing west interface. Twenty-four banks retain north M5/M7 with 470 contacts; one bank retains east M4/M6 with 77 contacts. Every bit has a proposed contact coordinate/layer in the compressed assignment. Those coordinates have not been track, access, PG or parent-seam qualified.

The 31 contacted buses have literal DEPTH4 ring instances, native input bin instances, fclk/FSTART/reset/strap port expressions and actual native consumer ports recorded. All native consumer mappings resolve. The nested seq_cfg_image_ready expression retains its real cland_up_ready gate after the existing delay. The highest incoming bit is the native ea input; existing eq capture semantics/reset are preserved. The 1,716 pure data source pairs and 31 separate epoch controls must not be conflated.

Exactly 54,997 existing cells / 13,592 FFs / 7,626.025260 um² are assigned once to these source-level bays (zero duplicate memberships). This includes ring logic, matching native bins and actual cells from existing delay instances. The area is already part of the actual 28,564.946460 um² whole standard-cell footprint; it is not an added cost. West contains 4,393.099800 um²; north 2,911.246920; east 321.678540. The colored rectangles are memberships and reservations, not placements or bank outlines qualified at a target density.

There are 890 literal source delay instances: 888 D1 and two D2. The two D2 instances are u_pd2_embed_prov_embed_scale_re_0 and u_pd2_sys_face_tt_control_stores_ready_0, each with two actual FFs. u_pd1_sys_face_seq_dc_54 has no actual mapped FF, so it earns zero physical stage/reach credit. All source parameters and actual physical FF identities are retained separately. Across these delays there are 891 actual FFs. No extra state or pipeline cycle is proposed.

| Bank | Actual contacted bus | Proposed face | Data+epoch bits | Existing assigned FFs | Existing cell area um² | Actual native consumer | Proposed membership rectangle um |
|---|---|---|---:|---:|---:|---|---|
| B01 | coll_flt_i | N | 2 | 81 | 64.531 | u_sys_face | (4.320,332.856)–(13.886,375.840) |
| B02 | coll_fltv_i | N | 71 | 499 | 282.517 | u_or_0 | (13.886,332.856)–(54.539,375.840) |
| B03 | ctlm_flt_i | N | 2 | 81 | 65.493 | u_or_0 | (54.539,332.856)–(64.213,375.840) |
| B04 | d2d_rom__native_tx_payload | W | 549 | 3395 | 1866.823 | u_d2d_rom | (4.320,108.000)–(56.160,201.960) |
| B05 | d2d_rom__native_tx_v | W | 2 | 82 | 61.688 | u_d2d_rom | (4.320,201.960)–(56.160,205.600) |
| B06 | d2d_rom__obs_native | W | 61 | 495 | 263.169 | u_d2d_rom | (4.320,205.600)–(56.160,219.210) |
| B07 | d2d_rom__x3 | W | 525 | 3775 | 1898.491 | u_d2d_rom | (4.320,219.210)–(56.160,311.528) |
| B08 | d2d_rom__x3_generation | W | 3 | 87 | 62.169 | u_d2d_rom | (4.320,311.528)–(56.160,315.370) |
| B09 | d2d_rom__x3_identity | W | 60 | 429 | 240.760 | u_d2d_rom | (4.320,315.370)–(56.160,328.320) |
| B10 | embed_prov__core_start | N | 2 | 81 | 58.801 | u_embed_prov | (64.213,332.856)–(73.138,375.840) |
| B11 | embed_prov__core_token | N | 19 | 183 | 113.695 | u_embed_prov | (73.138,332.856)–(89.928,375.840) |
| B12 | embed_prov__embed_code_addr | N | 25 | 219 | 130.899 | u_embed_prov | (89.928,332.856)–(109.216,375.840) |
| B13 | embed_prov__embed_code_re | N | 2 | 81 | 59.851 | u_embed_prov | (109.216,332.856)–(118.259,375.840) |
| B14 | embed_prov__embed_scale_addr | N | 19 | 201 | 118.506 | u_embed_prov | (118.259,332.856)–(135.587,375.840) |
| B15 | embed_prov__embed_scale_re | N | 2 | 83 | 60.871 | u_embed_prov | (135.587,332.856)–(144.743,375.840) |
| B16 | sys_face__head_descriptor_generation | N | 3 | 87 | 63.831 | u_sys_face | (144.743,332.856)–(154.423,375.840) |
| B17 | sys_face__head_descriptor_tag | N | 60 | 429 | 258.664 | u_sys_face | (154.423,332.856)–(191.258,375.840) |
| B18 | sys_face__head_descriptor_v | N | 2 | 81 | 60.755 | u_sys_face | (191.258,332.856)–(200.402,375.840) |
| B19 | sys_face__io_cmd_free | N | 2 | 82 | 65.129 | u_sys_face | (200.402,332.856)–(210.034,375.840) |
| B20 | sys_face__io_fault | N | 2 | 81 | 64.531 | u_sys_face | (210.034,332.856)–(219.600,375.840) |
| B21 | sys_face__native_fault | N | 2 | 81 | 60.492 | u_sys_face | (219.600,332.856)–(228.714,375.840) |
| B22 | sys_face__seq_cfg_image_ready | N | 2 | 82 | 61.076 | u_sys_face | (228.714,332.856)–(237.894,375.840) |
| B23 | sys_face__seq_dc | N | 57 | 466 | 271.480 | u_sys_face | (237.894,332.856)–(275.970,375.840) |
| B24 | sys_face__seq_descriptor_obs | N | 70 | 562 | 297.315 | u_sys_face | (275.970,332.856)–(318.086,375.840) |
| B25 | sys_face__seq_program_obs | E | 77 | 611 | 321.679 | u_sys_face | (358.560,108.000)–(427.680,250.560) |
| B26 | sys_face__tt_command_stage | N | 7 | 117 | 79.024 | u_sys_face | (318.086,332.856)–(329.847,375.840) |
| B27 | sys_face__tt_control_stores_ready | N | 2 | 83 | 61.192 | u_sys_face | (329.847,332.856)–(339.040,375.840) |
| B28 | sys_face__tt_layer_context_v | N | 2 | 81 | 60.813 | u_sys_face | (339.040,332.856)–(348.190,375.840) |
| B29 | sys_face__tt_native_pos | N | 19 | 183 | 115.503 | u_sys_face | (348.190,332.856)–(365.182,375.840) |
| B30 | sys_face__tt_native_tok | N | 19 | 183 | 113.986 | u_sys_face | (365.182,332.856)–(382.004,375.840) |
| B31 | sys_face__tt_program_obs | N | 77 | 611 | 322.291 | u_sys_face | (382.004,332.856)–(427.680,375.840) |

## Actual transport and remaining source obligations

Each exact member is identified by its original instance name, master, cell ID and original box in exact_membership.json.gz. Literal ring/native ports, matching source pairs and opaque epoch-control cases are preserved. None of the 944 retained B long-transport chain sequences directly intersects these ring/bin/delay memberships; their existing stage identities remain separate. They are not spare pipeline stages to attach to a bank.

Another 155 common cland FFs lie outside the 31 bank memberships: origin, FSTART, collector and monitor roles require their own protected source-aware placement constraints. The remaining 34,147 whole-frame native FFs, including those controls and functional/transport logic, have no inferred placement from these bank rectangles. Logical clock names, RAW/run reset sources/depths, bootstrap/mission roles, epoch handling, selected EFALL=false/PAD0 START mode, macro interfaces and all cycles remain unchanged.

Real source/access limits remain open: the incoming parent fclk/FSTART driver and seam/arrival contract after each N→W change; local strap homes/unchanged values; actual functional FF homes behind native ports; per-port macro tie/capture net correspondence; legal M4-to-upper via stacks; upper-layer signal ownership; PG and local clock cuts. The actual macro pin/OBS and unique-net tie census from 19567464b remains the constraint. No claim that pin contacts freely cross the narrow gaps or macro body follows from these bays. The actual two pad/capture local homes remain protected below 1 um.

This is the same 432 × 380.16 um / 4.32 um inset compact option and its explicit parent west-strip/interface/clock/START event. No old 51,596-home clock geometry, fixed-frame B result, START proof, sparse-outline exception, new global clock port or unchanged-arrival claim is transferred. No physical execution approval is contained here.

## Literal macro role followup and real local ties

Read-only extraction of the exact mapped preplacement macro instances resolves each scalar LEF pin to its actual source vector bit. This distinguishes clock, output, nonconstant input and explicit constant0/1 roles; no all-live assumption remains. Code SRAM east has 546 constant contacts (512 mask ones,34 repair zeros) and246 nonconstant inputs. Its west face has all512 outputs,280 nonconstant inputs andclock. Each D2D east has169 constants and60 nonconstant inputs; west has137 outputs,90 nonconstant inputs,clock andone constant read-enable. Sys ROM has no constants.

The actual placed direct tie source groups match: code512 TIEHI+34 TIELO; eachD2D138 TIEHI+32 TIELO. All1,226 connected tie instances are retained by identity in the compressed pin-role artifact. Proposed narrow local tie regions outside the two macro placement halos use actual tie dimensions0.162×0.27um: each inter-D2D gap group170 cells/7.436um² in117.286um², code546 cells/23.882um² in117.609um². These are gross regional area reservations, not legal placement or a guessed port-to-clone bijection. Actual per-port postplacement labels are absent from geom_dump; that specific mapping remains open.

The actual source PDN has M5 width0.12/spacing0.072/pitch4.32/offset2.064, M6 width0.288/spacing0.096/pitch4.32/offset1.968 and M7 width0.288/spacing0.096/pitch8.64/offset4.128, with M4-to-M5 macro PG connections. The new compact grid has not been emitted. Any M4-to-upper signal escape must explicitly share real via and track capacity with these PG structures. Code west and sys-ROM clustered contacts may need more than a single local horizontal escape plane or controlled vertical fanout; no M6/M8 route or cut is assigned by this receipt. Neither treating546 local constants as546 long links nor treating M5+ as unlimited capacity is valid. No new cells, stages, cycles or physical execution are proposed.

## Exact upstream physical interfaces and parent obstruction

All31 upstream logical and schema-expanded physical source ports resolve:27 from native59,4 from coll_f3. Fourteen are explicit buses;17 are existing FT-slot output ports, not missing declarations or guessed aliases. Preserve their literal station contracts: four1-station,one2-station,twelve3-station sources. The JSON records each current crossing, physical face/layers/window, partition origin/orientation/outline, slot and data width. Every crossing width equals the receiving bank data-plus-epoch width minus one.

Twenty native59 south outputs feed proposed north banks, six native59 south outputs would feed the newly proposed west banks, and one feeds the existing east bank. Four coll_f3 west FT outputs feed proposed north banks. These are existing source identities; their new physical seams and actual related clock/FSTART arrival contexts remain unqualified.

The current GLUE origin is(0,10022.4), with native59 at(0,11491.2): the original1468.8um GLUE height abuts native59 south. Keeping the GLUE origin while shrinking to380.16um creates a1088.64um gap. West x=0 is also the die edge, so the six proposed N→W banks have no source counterpart west of the current frame. The same compact option therefore requires a coherent multi-part parent repack/interface event or a qualified bridge using already permitted stages. No new neighbor origins, bridge stages, cycles, clock ports, pad origin or global arrival contracts are assumed by this receipt.

The current forwarded clock contracts select the actual source partition's clk port for all31 banks (27 native59,4 coll_f3). Literal generated identities are srcpart.fclk_out_<srcbus> → glue.fclk_in_<dstbus>, and srcpart.cland_fstart_out_<srcbus> → glue.cland_fstart_in_<dstbus>. These source-clock, START and phase/count identities must survive the physical interface event; no nearest-tap substitution or ideal-arrival claim is implied.

Proposal halo correction: the actual code SRAM top328.356 plus4.32 halo reaches332.676. The old north bay floor332.640 overlapped that halo by0.036um. Raising only its floor to332.856 leaves0.180um additional clearance; north reserve is18,197.706240um² and total N/W/E reservation39,472.842240um², still above32,047.918um². Frame, macros, memberships, bit contacts, clocks, source/cycles and all native artifacts are unchanged. Updated drawing personally viewed; no packing or CAD approval implied.
