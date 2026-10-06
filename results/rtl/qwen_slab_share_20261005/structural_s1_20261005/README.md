# Slab port group: S1 boundary-context measurement and S3 bench (2026-10-05)

Design note: `/tmp/claude-review-20261003/handoff_to_codex_20261004/qwen_slab_structural_claude_to_codex_ampere.md`. Sources: `physical/qwen_slab_structural/`; S3 is in `rtl/physical/ot_qwen_slab_port_group.sv`.

**Vehicle.** Codex `qss_fanout_twoface_570_l7` `3_place.odb`, rerun through the ORFS CTS stage (`run_cts.sh`) with:
- `old`: its own SDC;
- `new`: the same SDC plus, after the tree is built, every boundary delay re-referenced to the propagated tree (`refpin_sdc.py`; hold min 0, setup max 0.2 T).

**S1 result, CTS stage.**

| | control (old) | S1 (new) |
|---|---|---|
| first hold report | 6,084 endpoints, −893 ps, TNS −783,605 ps | 3,719 endpoints, −88.9 ps, TNS −9,030 ps |
| hold repair | stopped after the first report | 4,830 buffers, hold met (+10.005 ps) |

The control is the Codex run, which needed 34,024 hold buffers and then failed GRT. Under S1, setup WNS is −267.6 ps, dominated by the meso FIFO and the multiplier tag fan-out; the paths are in `post_cts_paths_s1.rpt`. Those are what S2 and S3 address.

**Bench** (`bench_main_vs_s3.txt`): main RTL and S3 RTL both PASS, 1,505/1,505 bit-exact, 751 argmax tops, the same `$finish` time (3,067,500 ps).
