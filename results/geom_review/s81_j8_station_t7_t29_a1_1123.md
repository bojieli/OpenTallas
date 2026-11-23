# S81 J8 t7 and t29 placed station review

Viewed 2026-11-23 08:53 PST.

## slice_station__t7__cl945bc067

**PASS-COND**

- Exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t7__cl945bc067/gen/slice_station__t7__cl945bc067
- Viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t7__cl945bc067/geom/auto_geom.png
- The placed image shows aligned north/south groups around two west-side relay columns and clear channels across the open middle. No unregistered pins. Capture 91.95 um max, 36.25 um p90 and 288.01 um max register hop. Nearest tap 226.20 um, predicted max tap load 841. Verified the PRE_CTS hook sources clock_taps.tcl to reassign the raw source span. Run ordinary CTS and route timing gates.

## slice_station__t29__clc7772371

**FAIL**

- Exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t29__clc7772371/gen/slice_station__t29__clc7772371
- Viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t29__clc7772371/geom/auto_geom.png
- The current place image has concentrated northwest input-clock groups, center relay rows and a sparse east half. One pin capture still reaches 254.86 um despite p90 19.94 um, with pin/relay locality specifically lost on the tail. The max register hop is 315.41 um and local tap estimate 306.69 um. Correct the long capture group on this J8 form. Prior archived event receipts are separate.
