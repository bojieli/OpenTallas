# KV CTL mu5 macro contact audit

Exact c5fbbded9 kit uses three `ot_sram_1r1w_128x256_m1_r2c2` macros. The actual LEF is 94.824 by 41.064 um, with 410 west and 409 east contacts: 9.984 and9.960 per um. Both fail the required full-face limit6/um. Parent channels or larger halos do not change this count. All contact names, rectangles, USE roles and source hash are in contacts.json. Existing gate outputs are diagnostic; no new gate or submission is authorized.

A successor must model real banked storage or a truthfully regenerated wider-pitch macro including physical and electrical effects, preserve actual OLD-data read/collision/boot-write semantics, and cure all reset/input/functional transparent fanout32 before build. The current kit additionally targets reset fanout256; that source census remains open.
