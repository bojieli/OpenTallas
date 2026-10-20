# qfd_c_b16_fulln -- FULL 16-region landed CB16 parent on the 43.2 joint solution (MAIN; QW-CB16A0 10-20), A0 = STAND-IN

Generated: tools/qwen_cluster/qc_fullm_kit.py (RTL rtl/physical/qcluster/qfd_c_b16_fullm.sv = fullk RTL modulo top rename,
normalized SHA identical, 0 added edges) -> fullm_joint_solve.py (CP-SAT hard station + ring bay placement) ->
fullm_control_model.py -> fullm_control_ac.py (scalar FF sites) -> fullm_materialize.py -> `ref_tile.py gen`.
Do not hand-edit. CRITICAL prefix qfd_c_b16: gate + coordinator review only (no REVIEW.json, no submit).

Successor of qfd_c_b16_fullk / fullkb: fullk 030948 FAILED at GPL (ODB-0359: FIRM soft-ring leaf cells moved). One failed
route = structural redesign:
- every hard origin (A0, xstn, stn514/516) on the 43.2 lattice; stations moved <= 4 lattice steps by a joint CP-SAT model
  (3-deep pads = same-clock soft rings), hard-hard and hard-bay clearance 21.6 um;
- ring halves = EXCLUSIVE legal regions (fabric_sites_place_m.tcl: GPL owns the ring cells; row-capacity fill <= 35 % guard),
  no FIRM ring blocks; bank data / vld are ORDINARY single-cycle paths (all multicycle masks removed);
- every scalar reset / control FF (rpin, reset copy runs, farq straps) at a legal site found by arc consistency on a
  10.8-um grid outside hard children (+10.8) and bays (+4.32), all control edges <= 385 um planned.


QW-CB16A0-3 10-20: qfd_c_b16_fulln = qfd_c_b16_fullm (same RTL, sites tsv, place.tcl, SDC, PDN, pins) with ONE structural
change: PRE_GLOBAL_PLACE_TCL = physical/qcluster/fabric_sites_place_n.tcl.  Ring bays are deterministic uniform FIRM
lattices (every full-width row of the bay, even site-snapped pitch, odd rows half-pitch interleaved; fill <= 0.215),
released to PLACED for DPL by fabric_sites_release.tcl.  GPL places only the combinational cells.
Root causes (OpenROAD walks of the failed ODBs, scratch/qw-cb16a0-3/gpl): fullmb/mr/mbr GPL-0305 = GPL stacked identical-net
ring flops inside 43.2-um EXCLUSIVE regions (qc_bay_77: 145 of 693 flops in one 5.4-um bin, overflow stuck 0.22 > 0.10,
penalty 1e33 -> NaN); fullk ODB-0359 = 30 DUPLICATED site prefixes (5-col + 7-col line for the same stage -> same flops placed
twice).  The new hook refuses duplicate prefixes / double placement.  Hook proof on the fullmb 3_2_place_iop.odb:
161,549 of 161,549 flops placed, 108 bay lattices, 0 FIRM-FIRM overlaps.
Checklist items 1-8 unchanged from fullm (below); item 6 adds: ring flops on the uniform bay lattice (no GPL stacking).

## Safe-design checklist (owner 10-19) + pre-gate native census
1. Pins: PASS -- every data port lands in a hard station register; rst_<q> in its rpin register + equal-depth soft trees;
   ring halves re-register rsi (unchanged fullk RTL).
2. Reach: PASS (plan, independent replays) -- data (results/arch/qw_cb16_legal_bays_1020/grid43/qfd_c_b16_fullm_data_replay.json): hard per-bit max 402.9 um
   (71984 endpoints), soft-hard max 404.6, bank half-half max 401.8, soft max 401.8;
   control (results/arch/qw_cb16_legal_bays_1020/grid43/qfd_c_b16_fullm_control_replay.json): 653 scalar FFs, 855 edges, max 384.5 um
   (scalar_d 378.0, hard_rst_n 379.9, hard_sidx 83.5, soft_rsi 384.5); 16 static far-strap inputs (set_case_analysis 0, fixed tie strap), 0 unknown.
   Placed / routed reach confirmed by the gate.
3. Fanout: PASS -- fullk RTL: gate PRE_GATE_NATIVE_CENSUS on the mapped netlist fullk 030948 max 31 / 730,293 roots / 0 violations,
   fullkb 031034 max 31 / 617,488 / 0; this kit's in-flow census (limit 32, refuse) re-measures before layout.
4. Depth: PASS -- no logic between stations; ring read = registered one-hot + 4-term AND-OR; write = 2:1 enable mux.
5. Storage: ring = landing-contract D4 ring (fixed rotating pointers, constant-index read), kept as flops (as fullk).
6. Floorplan: all hard origins on 43.2 (replay), 21.6-um hard / bay clearance, outline 3067.2 x 5486.4 = 16.828 mm2, aspect 1.79.
7. Clock: 16 regional roots ck_c<c>r<r>, landed crossings; gate --cts measures pin-flop spread (<= 80 TT/FF); io_hold_margin 0.03.
8. Schedule: PASS -- static; identical edge counts to fullk / the qc_gen fabric (0 added cycles).
Owed: full-parent lockstep bench vs qfd_c_b16_dv; A0 regeneration on the qualified A0 LEF (stand-ins here).
