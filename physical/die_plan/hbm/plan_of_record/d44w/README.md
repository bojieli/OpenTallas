# HBM plan event d44w (DIE-HBM-59/CORES, 2026-11-03)

Base: d44t (claude/die-hbm-59-g0c-1102@d1fe917f36, die_plan 3837d4886dad). Sidecars are the d44o_cm plan dir,
except core_macros.json, clock_entries.json and the new cores/ pins files in this dir.
Built by results/die_hbm_1102/oneface/mk_event.py (d44t -> d44w core) and then mk_shrink.py (shrinks).

Classes (COORD GEOM 11-02):
1. MACRO-ARRAY ONE-FACE PINS (tools/die_plan/lane_pin_align.py)
   - sfustore_hw: S pins grouped by lane under each bank column; clk kept; fault kept on E, moved to y 10.008.
     Probe AUTO-GEOM 3_place: r2r 562.84/34 -> 419.47/1 (the last pair is fault, fixed by the fault move),
     relay_collapse 8 -> 0, pin_density/channel WARN gone.
   - keybuf_slice: W pins spread over the face (10.4 -> 7.7/um). The stack is unchanged (a shift put the clock
     island over a macro).
2. gq_land: W pins spread over the face (3 pins-file variants), 2775 pins, 17 -> 13.7/um, partial_face.
3. PLAN_CORE_MACROS: KNOWN static sites (core_macros_fix.fix, 10.8-um channels)
   - selector_static_sel: kits-26 placed sites
   - dma_back_static_vp4_banks_cp: PLAN-TRIAL rows promoted
   - svc_wb_kport_q: 4x8 columns
   gen --core-macros auto passes for wb_kport and dma_back.
4. Outline shrinks: height only, centre kept, hub_repack.run, W/E faces <= 5 pins/um
   - pgslice_lg__lanes8_11: 725.76 -> 311.04 (est fill 0.064 -> 0.150)
   - cxport_ij_q: 449.28 -> 414.72
   The changed stations keep their register counts (no latency change).
   Not shrunk: q3_body (the shrink needed +4 regs on inj stations), q2n2_vm (W pins need 535 um),
   q3_vm (W face at 6/um).
   The cxport fixed abstract lef/lib is dropped; the new kit re-cut supplies it.
Pins sha changes (fresh kits needed): sfustore_hw, keybuf_slice, gq_land, pgslice_lg__lanes8_11, cxport_ij_q.
Macro sites only: selector_static_sel, svc_wb_kport_q, dma_back_static_vp4_banks_cp.
G0/G0C: see below and g0/.

## Fix 11-03 (DIE-HBM-60/PLAN): shrink pins back on the plan tracks; G0/G0C

The first d44w cut (c49127a8d8) failed G0C with 48 NEW `hard_cores` errors: "pins off the plan track" on the two
height-shrink pins files (lanes8_11: 2241 pins, in q_su20/q_su30 (+pv1); cxport_ij_q: 4097 pins, in the 4 hub
instances). The cause was `hub_repack.remap_pins`, which scaled the W/E pins along the edge without snapping them to
the M4 0.048 grid.

Class fix in `tools/die_plan/hub_repack.py` (all dies, default on): each scaled edge pin keeps its ORIGINAL track
phase. After the >= 0.192 spacing rule it is rounded up to the next coordinate on that phase. Test:
`tools/die_plan/test_hub_repack_tracks.py`.

The event was rebuilt with the same builders (`mk_event.py` on d44t, then `mk_shrink.py`).
- die_plan.json is byte-identical (f83c5f4bdd3f), so stations and windows are unchanged.
- core_macros.json and clock_entries.json are unchanged.
- Only the 2 shrink pins files change (max pin move 0.046 um).

G0+G0C (`tools/die_plan/check.py --completeness`, the same tools on both plans: main 7cf44d5c0 + this branch + g0c-1102):
- d44t: 74 ERROR / 128 pending-view.
- d44w first cut: 122 (+48 off-track).
- d44w fixed: 74 ERROR / 128 pending-view. The message set is identical to d44t (0 new, 0 gone).

Reports are in g0/. Pins sha changes needing fresh kits: sfustore_hw, keybuf_slice, gq_land (3 tables),
pgslice_lg__lanes8_11, cxport_ij_q. Macro sites only: selector_static_sel, svc_wb_kport_q, dma_back_static_vp4_banks_cp.
