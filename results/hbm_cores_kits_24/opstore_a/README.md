# HBM-052 opstore_a cut map regenerated on the current plan (HBM-CORES-KITS-24, 2026-10-29)

COORD 10-29 ~20:00: the stored whole-bus cut map (canonical_ports_split.json sfu_opstore_a) lists 8 buses; the current
plan pins (d24a cores/ot_hgi_sfu_core_split3__opstore_a__388.8x345.6__canon__c20g_390.528x436.32.json) have 29.
main physical/die_plan/hbm/cores/ports/ports_cut.json already has the same 29 buses/widths (CHECKED).

Method (all CHECKED, intel1 run dir /srv/opentallas-scratch2/claude/hbm-cores-kits-24/opa):
* master elab `elab.ys` (= fcad66c6d split3_master_elab.ys, output path only) in docker openroad/orfs:asap7lock, 48 GB cap.
* main `split_bitmap.py` (cut = ports_cut.json, rest top = rtl/.../ot_hgi_sfu_split3_opstore_a_core.sv): 29/29 buses,
  0 problems, 0 RTL inputs uncovered, 0 outputs open, verdict UNPROVEN on 4 buses (bitmap_opstore_a.json).
* `prove_unproven.py`: the cut record split/wip_unverified/ot_hgi_sfu_core_split3__opstore_a.map.json gives each plan bit
  its master net name; resolved to the elaborated sigbit and compared with the candidate RTL bit (rest_wrap u_x path):
  - glue[4] -> u_core_io_r[3:0]: SAME_NET 4/4 (u_core.io[400..403])
  - glue_1 -> u_core_u_engine_u_memory_fault: SAME_NET 1/1 (u_core.u_engine.store_fault)
  - x_u_core_u_engine_u_arithmetic_vm_waddr -> u_grid_vm_waddr[143:0]: SAME_NET 144/144
  - g_operand_0_u_group_sw_mask -> stage_mask: CONST_UNREAD. Master cell u_memory.g_operand[0].u_group
    (ot_hgi_su_lgroup2) port sw_mask = 64 x constant 1 in the elab; the cut record is 64 x 1; RTL stage_mask is
    declared but never read in the opstore_a core (the core folds the master constant). The mapping cannot change function.
* Sidecar physical/die_plan/hbm/cores/harden/canonical_bitmap_split.json (opt-in, sfu_opstore_a only) carries the
  slices, mapper_verdict UNPROVEN and the proof per bus; check.verdict PASS.

Kit: ot_hgi_sfu_core_split3__opstore_a@759d2e684001 _k24 on d24a generates (was MAP_AMBIGUOUS). KIT_PREFLIGHT --contract
FAIL 3 = macro_channels / clock_entry_clear / macro_pin_grid only: d24a core_macros status UNKNOWN (3 SRAM masters,
no placement at the plan outline) -> plan item for DIE-HBM-25, not a map issue. No place/route, no LEC yet.
