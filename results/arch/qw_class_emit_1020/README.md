# Forwarded-lane class emission source candidate, 2026-10-20

Enable with OT_SPLIT_FWD_CLASSES=1 alongside OT_SPLIT_FWD_LANES=1. Default remains off.
The generator reserves class-sized rectangles before placement. Source composition
uses the true class master, legal orientation and class frame, splits wide paths
into parallel <=600-bit classes, preserves each physical lane's original n/E/K,
and connects spare inputs to the native landing tie_lo. Spare outputs are distinct
unused nets. Superseded per-frame masters are removed from the generated master set.
The existing reach, native calendar, binding and per-bit geometry gates remain required.

Committed evidence:
- source_checks.log: four tests pass, including all widths 1/32/128/548/600/1088,
  source/calendar mismatch refusal and missing reservation refusal. The actual
  lane_latency_audit passes on every emitted fixture, including two physical
  544-bit lanes for the 1088-bit source path.
- rtl_pass.log: pinned Verilator 5.050 compares the actual generated 2x600-bit class
  composition against the original 1088-bit ot_qfd_lane_st/ot_qfd_land chain over
  1000 receiver cycles. All 1088 output bits agree.
- slice_swap_fail.log: swapping the two source slices fails equivalence at cycle33.

Live integration at Claude return (22:29 PT):
- ot-epyc6 /srv/opentallas-scratch/claude/codex-qw-classgen2220, ot-heavy unit
  oth-ubuntu-38466-1792560109, local ot-run session28368, local log
  /home/ubuntu/claude-takeover-20261007/qw-classgen2220.log. Independent immutable
  g5r2b source copy from codex-qw-facts2210-v2 plus initial class hooks; no live
  predecessor source was edited. GEN is still planning/reparing class-size frames.
- This run uses the initial uncentered composition helper from the first candidate.
  Current source additionally centers class frames inside reservations, compresses
  contiguous emitted bit expressions, removes unused legacy masters, exports the
  class receipt in fwd_lanes, validates source width, and handles split fanout merges.
  These followups require a fresh actual GEN after the live run ends.
- Full-die strict bind / zero lane no_view / final geometry are NOT yet established.
  No route was submitted and no closure claim is made.

Resume: collect the live GEN failure/pass first; preserve its evidence. Apply the
final exporter from codex/qwen-gen-facts-1020 (6926a4cc8), preserve unconditional
slice normalization in _pin_pos plus ext, and use current class source for the next
fresh GEN. D4 e1 closed classes are primary; D8 remains fallback.
