# Wide fmt3 R25 geometry study

Remote geometry model executed on ot-epyc2 through measured 1 GiB admission,
using generator source 0cb3d962452b9a627de3a386cd4e0baf5be0c7bf and
tools/qwen_r25_fmt3_die_fit.py. This is a placement study, not network or timing
qualification. No headline performance or adoption follows from this record.

The naive 4 by 2 substitution fails the existing reticle assertion at
38,680.848 by 20,854.8 micrometres. The actual 3 by 3 physical grid preserves
eight logical SMs per group and four groups (32 total), with an empty ninth
slot, 259.2 micrometre column corridors, and 207.36 micrometre side padding.
Its exact 3214.08 by 1131.84 micrometre SM produces a 31,734.288 by 24,051.6
micrometre die, 763.2604012608 square millimetres. The generator reports 142
instances with zero overlaps and zero instances outside the outline.

The die outline costs 10.0696487731 square millimetres against adopted R25,
and 19.949359104 square millimetres against the unadopted SM3 reference with
the same retile. These are whole-outline deltas, not the sum of SM areas.
Reticle margins are 1265.712 micrometres horizontally and 1948.4 vertically.

The old network probe uses historical logical tree associations and original
SM3 result-pin offsets. Actual widened pin coordinates, owner reservations,
registered relay endpoints, clock delivery, and the composed latency remain
separate obligations. Geometry legality alone does not prove those contracts.
