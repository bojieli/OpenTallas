# SFU core k9s3: reset-release delta (LH-K9R 2026-10-19)

k9s3 = k9s2 (results/rtl/hbm_safe_k9_1019/schedule.md: WPIPE +1 edge bank-write landing, <= 2 edges per SFU invocation)
plus RST_TREE=1 (registered reset distribution trees with kept copies, rtl/lib/ot_rst_kept_tree.sv). Data edges unchanged.

| reset pin | k9s / k9s2: port -> consumers | k9s3: port -> consumers | delta |
|---|---|---|---|
| rst_n (bridge, engine, fault) | 2 face landing + 3 ot_rst_relay (2 sync + 1 relay) = 5 | 2 landing + 2 tree = 4 | -1 |
| rst_lg_n[3:0] (VM lg taps) | 2 landing = 2 | 2 + 2 = 4 | +2 |
| rst_map_n[15:0] (lane maps) | 2 | 4 | +2 |
| rst_lane_n[15:0] (lane leaves) | 2 | 4 | +2 |

- All four resets now release on the SAME edge (4 after the die drives the pins), so the compiler's reset contract is one
  constant: the first programme word may be presented >= 4 edges after the die releases reset (bench: configuration starts
  long after release; lockstep vs ot_hgi_sfu_scheduled_engine unchanged).
- Assertion is synchronous through the same 4 registered stages (the clocks run during reset; the die holds reset >= 8
  edges, bench 8).
- Price: a one-time constant at power-up / reset only; 0 edges per token, 0 % of the HBM token rate (DS AR / MTP / Qwen
  0.00 %). No calendar change (make_qswiglu_io_calendar.py unchanged).
- Owner of the reset contract in the die schedule: H-D4G / TW5-HBM-DIE (die reset sequencer: hold >= 8 edges, first SFU
  programme word >= 4 edges after release).
