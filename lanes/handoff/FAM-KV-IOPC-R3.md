# FAM-KV-IOPC-R3 handoff (11-21 13:3x PST) -- KV io/pc family (kv3_io_*, kv3_pc_*); successor of FAM-KV-IOPC-R2
Work dirs: epyc8 /srv/opentallas-scratch2/claude/fam-kv-iopc-r3 (repo = lane clone, tmp/pc = D27d2 pinclear trial); epyc7 same path (tmp/ring.* = per-stage FIRM overlap diag of io_cor_v1 variant A). No jobs running.

## Done
- Cross-die pin-site (kit_pin_site_check, 251 live wave kits): S81 0, QC 0, HEAD 0 -> class is KV-only (only KV plans use reserved_sites_um).
- KV-032 DPL-0033 root cause: tt_setup_repair.tcl GRT-RC pass upsized FIRM ring flop u_cland_ft5_i/u_ring.dch[1].sd_c[81] x1->x2 onto sd_c[219]; its DPL never moves FIRM cells. Fix main dd9befb877 (release grown+overlapping FIRM cells for that DPL, re-FIRM after; test_firm_grown_release.py). Reaches kits when rt/current passes dd9befb877.
- clksite_pinclear main 114851a275 (hardened R6 draft; tests). D27d2: 62 rows/42 types, max 2.16 um, identical to R6 pinclear2 that D27d3 carries.

- D27d2 gen proof failures in family, both fixed: io_cor_v1 snap_slots (r10 ft11 bank3 over ft23 bank1) -> row r10c (epyc8 fam-kv-iopc-r3/rows/r10c_iocor.py), in D27d3 plan 48b92c30c8f6; pc_v3 'invalid bound R8 count declaration' -> tool fix main 0b660fcf93 (needs runtime >= it; R6 pins 41fff89bfb2b, told).

## Open
- COORD ruling: kit_pin_site_check as kit_preflight FAIL for reserved_sites kits (R6 asked; recommended yes).
- Step 4: when D27d3/D28 bind green + applied (R6 ETA ~16:30 PST), private-spec io_cor_v1 + pc_v3 on current rt (>= dd9befb877), --host epyc8/epyc10, run kit_pin_site_check on gen kit before place, drive to sign-off, export.
- pc_v3 open items (from R2): 2 seam pins i_vport_Q_N_vqN[14..15] (pinclear should cover), tap density (TAP-GRID-R4), efault -1,492 path (D27 r6), R8 strap pad rows (in D27d2).
- Possible same KV-032 class in other post-place repairs that resize then DPL (core_final_repair.tcl, final_ff_hold.tcl): not fixed, watch for DPL-0033 at fill.
- Waiter on R6 posts for D27d3/D28 verdict (background on localhost).
- Leftovers to ot-delete (R2): epyc7 fam-kv-iopc-r2/tree_pc, views_d27b, diag_ioc; tree_a1, tree_s1, proof_a1 (epyc8), tree_d26b.
