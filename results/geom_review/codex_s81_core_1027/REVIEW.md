# CODEX S81 core entry correction 2026-10-27

Images VIEWED: qbank.png and sstn.png (same frozen family slices as c16; the only implementation change is clock entry snap/access).

Qbank: centre entry feeds two short horizontal legs, then four balanced quadrants; wide sink groups stay local, no macro walls, longest plotted branch 15.7 um. Clock-only centre M5 pin now stays on the kit routing track with 0.048x0.48 access in BOTH io.tcl and the later pushdown hook.

Sstn: centre entry feeds the sparse upper/lower sink groups with four local islands; asymmetrical sink occupancy explains differing first-leg lengths (max30.8 um), downstream leaves remain local (max13.5 um). No long unrepeated leg or macro obstruction appears in the planned tree.

Verdict PASS-COND for one corrected trial each. Data floorplan, face pin order, outline, PG and latency are unchanged from c16. Prior DRT-0255 failures remain FAIL. Fresh kits check-kit PASS with the effective snapped core_infra_plan.json; detailed route must confirm clock-pin access, and signoff.py decides closure.
