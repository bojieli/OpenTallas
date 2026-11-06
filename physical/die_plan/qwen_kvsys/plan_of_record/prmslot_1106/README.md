# KV-PRMSLOT-1 11-06: qkd_hr_core_prompt slot event 233.28 -> 254.88

COORD 11-06 12:2x ruling (3), from the KV-PRM-B5 12:03 post. This is one hard-core slot event in kv3_hub_Wi. It uses the DIE-KV-40 q1/q2 widen form: the origin stays fixed at (319.68, 380.16) and the core grows east and north into free space.

- `hard_cores[host__qkd_hr_core_prompt]`: outline_um 233.28 -> 254.88 square. pins_file -> `pins/qkd_hr_core_prompt_pins_r26q5_g255.json`. The old r26q5 table is kept.
- Pin table: KV-PRM-B4 `grow_outline.py` (sha256 50c1797368ffefa3) is applied to the r26q5 centre-form pins. Coords >= 231.78 move +21.6, coords <= 1.5 are kept, and all others are scaled x254.88/233.28 and snapped to 0.048. 5124 pins. Faces, layers and order are unchanged. The result equals the KV-PRM-B4 vB kit `pins.json` pin for pin (edge form = centre form -/+ 0.096; max diff 3e-14).
- Clock tap `host__qkd_hr_core_prompt.ck[0]` xy moves 436.344,496.8 -> 447.168,507.6 to follow the core ck[0] pin. The insertion numbers are unchanged (proxy).
- ft24 station 3 (regs_um[3], bit_sites_um[2], 145 sites) was in the old 34.56-um prompt/rx street and is now covered by the grown slot. It moves +8.64 east (one die grid) to the street columns x 581.04/583.2, which ft6 station 1 already uses north of rx. The new street is 12.96 um (574.56 .. 587.52), so the sites keep 6.48 um to the prompt and 2.9 um to rx. The hops to stations 2 and 4 get shorter.
- No other plan object lies in the growth strips (scan of every coordinate in kv3_hub_Wi). The top-level plan note is left unchanged so the event merges cleanly with KV-SYSSD-2 (kv3_sys_SD).

Reproduce: `python3 -I prmslot_event.py <plan_of_record>` on the base plan. Render: `prmslot_wi.png` (`slot_render.py`).
