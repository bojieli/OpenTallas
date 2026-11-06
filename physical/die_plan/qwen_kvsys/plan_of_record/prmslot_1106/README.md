# KV-PRMSLOT-1 11-06: qkd_hr_core_prompt slot event 233.28 -> 254.88 (on-track pin table)

COORD 11-06 12:2x ruling (3), from the KV-PRM-B5 12:03 post. This is one hard-core slot event in kv3_hub_Wi. It uses the DIE-KV-40 q1/q2 widen form: the origin stays fixed at (319.68, 380.16) and the core grows east and north into free space.

- `hard_cores[host__qkd_hr_core_prompt]`: outline_um 233.28 -> 254.88 square. pins_file -> `pins/qkd_hr_core_prompt_pins_r26q5_g255t.json`. The old r26q5 table is kept.
- Pin table: the KV-PRM-B4 `grow_outline.py` transform (sha256 50c1797368ffefa3) on the r26q5 centre-form pins. Coords >= 231.78 move +21.6 and coords <= 1.5 are kept, as in that script. All other coords are scaled x254.88/233.28 and **snapped onto the layer tracks** (M4/M5 0.024+k*0.048, M7 0.032+k*0.064), which are the same tracks the kit's `make_tracks.tcl` makes.
  - The plain vB snap (k*0.048) leaves 4745 of 5124 pins between tracks: G0C `hard_cores` ERROR "4745 pins off the plan tracks". The same 4745 pins also sit off the vB kit's own M4/M5/M7 tracks (3_place.odb dump = io.tcl locations).
  - The on-track snap moves those 4745 pins along their face by <= 0.048 um (M5 1503, M4 2121, M7 1121). Faces, layers and order are unchanged, and there are no duplicate sites.
- Clock tap `host__qkd_hr_core_prompt.ck[0]` xy moves 436.344,496.8 -> 447.144,507.576 to follow the core ck[0] pin. The insertion numbers are unchanged (proxy).
- ft24 station 3 (regs_um[3], bit_sites_um[2], 145 sites) was in the old 34.56-um prompt/rx street and is now covered by the grown slot. It moves +8.64 east (one die grid) to the street columns x 581.04/583.2, which ft6 station 1 already uses north of rx. The new street is 12.96 um.
- No other plan object lies in the growth strips. The top-level plan note is left unchanged so the event merges cleanly with KV-SYSSD-2.
- Kits: the vB/vC kits use the off-track k*0.048 table, so they do NOT match this plan (pin_audit tol 0.001). `kit_repin_g255t.py KIT pins/qkd_hr_core_prompt_pins_r26q5_g255t.json` rewrites a kit's pins.json/io.tcl to this table, keeping the kit's face coordinates.

Reproduce: `python3 -I prmslot_event.py <plan_of_record> --on-track` on the base plan. Render: `prmslot_wi.png`.
