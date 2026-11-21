# Clock-first comparison, KV D26 kv3_hg_v1p2

I inspected the exact placed control overlay for official attempt 3. The main vertical channel is heavily used near the middle macro crossings. The overlay has interior clock taps positioned above macro outlines, and many sinks remain attached to a few corridor taps. The retained scan has eleven taps over macros, a maximum tap load of 10,009, 9,082 long register hops, and 387 collapsed relay pairs.

Image: epyc7, /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D26/items/kv3_hg_v1p2/attempt_3/geom/auto_geom.png.

Verdict: FAIL for route on this geometry. The read-only flow proof moves to the separately reviewed HEAD hd_spn checkpoint. Read the exact layouts of the two inherited place arms before any route decision.

## Private clock-first-only variant 1121123820

Reviewed exact placed layout and density on epyc8 scratch2 under `claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D26/private/FLOW-CLKGRT-R2/kv3_hg_v1p2_1121123820/gen/kv3_hg_v1p2/run/layout_review/place/`. The lower and upper core columns again meet at the narrow central street. The central stacked elements have dense placement on their sides and ends, with concentrated density in the east-west crossing and along the left inward turn. Automatic local density is 1.385. The route option cannot move the macro or untangle this traffic. **FAIL** for manual route approval.

## Private clock-first and resistance-aware variant 1121130355

Reviewed exact density on epyc7 scratch2 under `claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D26/private/FLOW-CLKGRT-R2/kv3_hg_v1p2_1121130355/gen/kv3_hg_v1p2/run/layout_review/place/density.png`. The central strip is nearly full between the facing middle macro columns, its southern exits remain pinched, and the left-hand turn remains concentrated. **FAIL** for manual route approval.
