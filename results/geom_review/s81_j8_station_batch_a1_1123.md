# S81 J8 placed station review

Viewed 2026-11-23 08:48 PST.

## slice_station__t20

**FAIL**

- Exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t20/gen/slice_station__t20
- Viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t20/geom/auto_geom.png
- The image concentrates wide port banks and station rows against the west edge, with the closest usable clock 463.23 um from one sink. The east and south relay reach pattern leaves 52 register hops beyond 405 um. The worst 758.92 um hop is u_rrl_100_t to u_cland_monitor_1/arm[0]. Localize the monitor-arm reset fanout on an equal-depth relay hook and sweep the nearby tap position on the changed form.

## slice_station__t7__cl362204c4

**FAIL**

- Exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t7__cl362204c4/gen/slice_station__t7__cl362204c4
- Viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t7__cl362204c4/geom/auto_geom.png
- The layout shows two concentrated south boundary groups on separated relay columns. Pin capture is stretched to 254.86 um on one data edge, with p90 39.48 um. Nearest clock reach is 250.87 um and register hops are within 405 um. Reseat the long pin capture in the correct south landing group before routing this form.

## slice_station__t7__cl503f4913

**PASS-COND**

- Exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t7__cl503f4913/gen/slice_station__t7__cl503f4913
- Viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t7__cl503f4913/geom/auto_geom.png
- Discrete west and middle station rows align with matching north and south launch groups. Clear spaces between the rows and zero unregistered pins. Longest pin registration 91.95 um, register hop 288.06 um, nearest clock 213.19 um and predicted max tap load 842. Exact pre-CTS sources clock_taps.tcl to replace the raw 1,201.30 um source span. Continue through normal CTS and route timing gates on this exact form.

## slice_station__t44

**FAIL**

- Exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t44/gen/slice_station__t44
- Viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t44/gen/slice_station__t44/run/layout_review/place/density.png
- Also viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t44/gen/slice_station__t44/run/layout_review/place/layout.png
- The placed layout and density views show two dense south rows, a wide open middle and a 72.2% local density cluster at the middle of the east border. The reset fanout structures spread 536.1 um from u_rrl_14 and 526.7 um from u_rst_in. Recluster the east landing and reseat the reset branches at equal depth on the changed form.
