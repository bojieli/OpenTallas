# SD PHY physical declaration repair

The event28w_c logical `serdes` contents omitted the bound hard macro metadata.
The kit wave therefore stopped with ORD-2013: its synthesized w521/w522 macro
was absent from the generated LEF/lib inputs. `apply_sd_macro_declaration.py`
adds the existing physical identity and views to a copy of the plan of record.
It leaves ports, clock/reset, bands, partition outlines, placements and every
other type unchanged. No RTL or latency changes.

These are the same academic physical abstracts staged by DIE-KV-43 SD try6:
macro origin (17.28, 54), size 1848.96 by 972 um, R0; SD w522 and SD_v1 w521.
They model the PHY interface; analog implementation remains outside this view.
The files were copied byte for byte from the declared macros in that kit.

The helper was checked against event28w_c 16980115aa4a: `type_macros` resolves
one correct physical master per SD type, both LEFs declare the matching size,
and every non-contents field and every non-SD type compares equal. This is a
plan declaration fix, not a placement, timing, geometry or sign-off claim.

After applying it, G0C and generation run against the plan of record. The
separate SD landing-band/reset/secondary-clock candidates are not adopted by
this repair. Current try6 runs remain live and are never overwritten.
