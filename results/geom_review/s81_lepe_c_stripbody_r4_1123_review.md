# S81 LEPE C strip/body R4 geometry review

HOLD. Plan `e514ee9ab319` and sidecar `532721ce4c8d` are under `epyc9:/srv/opentallas-scratch2/claude/flow-stripbody-r2/codex_r9_north/split_body_clocks/seat_xring_body_r4`.

I inspected the full three-piece geometry for `77d93ca7de6f` and the before/after body crop for R4. Full renderer `r9_body_covered_geometry.png` is `0192d8a4ca82`. R4 crop `r9_body_xring_r4.png` is `95600c93e98`. Both are in `intel2:/srv/opentallas-scratch2/claude/flow-stripbody-r2/codex_reset_probe`.

The original `xring_i0` band overlapped CP3 by 1,643.772 µm². R4 uses the two rectangles below and preserves 9,329.8 µm² of band area across the plan and sidecar.

- `[1374.850781, 8.64, 1421.76, 177.12]`
- `[1412.652, 177.12, 1434.24, 243.2]`

The two pieces clear CP3 and the body clock taps by 4.32 µm at the closest boundaries. The model reports 204.64 µm clock reach, 25.32 µm worst pin-to-register distance, and 390.84 µm worst register-to-register distance. Peak nearest-tap load remains 2,519 against 1,500 and three body faces still fail pin clustering. The north and south strips retain aspect findings. Separate strict binding and placed geometry remain pending.
