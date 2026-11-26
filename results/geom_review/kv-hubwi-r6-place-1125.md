# KV Hub Wi R6 placed review

Viewed both the exact R6 placed-checkpoint geom/auto_geom.png and gen/kv3_hub_Wi/run/layout_review/place/density.png on the Intel2 kit KV-A5t9-r6-publish-1125/items/kv3_hub_Wi. The upper macros leave narrow channels. The densest placed soft cells collect between the middle and lower rows of macros, and the placement leaves much of the west and east floorplan empty. Clock sink clusters collect near the west, north and east faces and around the center macros. PDN and abutment still require the subsequent placed candidate checks.

The image's exact auto_geom.json reports FAIL. Its key measurements are channel estimates 1.783 horizontal and 7.694 vertical, col_v 8.986, 5,287 sinks on the most loaded tap, 0.6194 empty area and 115,957 FFs. KIT-WAVE reports 406,762 standard cells at floorplan. The geometry snapshot, collected later, counts 662,789 placed standard cells.

Verdict. HOLD route for the exact R6 Hub Wi. Keep the study of fixed-cycle START and feed-through seats and split the placement scope. C-STREET, C-TAP-LOAD, C-LEG405 and cell-cap. The exact visual artifacts are on Intel2 as named above.
