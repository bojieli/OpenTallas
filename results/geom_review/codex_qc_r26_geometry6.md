# QC R26 complete clock placement, Codex review

Picture viewed: `results/qc_clk_mesh3/r26_codex/geometry6/all_tree_geometry.png` (native100 IO-window successor; exporter receipt retained by the physical-export lane).

Verdict: **PASS-COND for trial clock placement and dry physical import.** This is not die clock sign-off or a die freeze.

The A0 row bands are regular; band drivers and the W-edge vertical feed sit in the reserved gaps. The previous diagonal buffer paths through A0 macros and per-row W-edge crossings are gone. The W-edge feed crosses to the main tree in the free row bands. The complete-cell census reports no hard-core overlaps, seam-body failures or cells outside the die. All physical buffer-to-buffer stages satisfy the 450-um limit (maximum 447.848 um); the long mesh straps are a multiply driven continuous mesh and still need electrical qualification. There are 33,417 groups / 50,149 real cells and 33,416 tree nets in this trial geometry.

Before GRT/STA, the actual mesh, its crossing vias and the PG/shield geometry must pass the physical import/census; the tree router must reserve those conductors before choosing tree tracks. The V2 primitive has demonstrated actual tied pins, mixed wire widths and a continuous mesh in OpenDB, but it does not establish full-die routing or timing. Full partition clock-footprint identity differs in many types and stays a type-reuse review item. The current mesh output boundary is still the old R2 mesh foot: actual local clock delivery to every partition entry, especially the long W-side stubs, remains open. All timing, extraction, PG continuity, IR and real-entry delivery qualifications remain required.
