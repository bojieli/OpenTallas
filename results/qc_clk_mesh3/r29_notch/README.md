# R29 same-net shield notch correction

The NC3 result is reproduced: DRT reported no errors on these windows, while a KLayout same-net spacing deck finds24 M9 gaps of20nm. They arise when a VSS PG stripe overlaps one shield and reduces the neighboring nominal40nm shield gap to20nm.

The encoder post-pass increases the gaps to40nm by trimming20nm only from the outer edge of the affected640nm shield. Its clock-facing edge remains fixed. The alternatives must not be confused: filling the gap would merge the shield/PG into a wide component and can require a new1um spacing class. This fix does not join them.

OpenDB coupon recreates316 actual rectangles extracted from the24 affected windows in intel2:/srv/opentallas-scratch2/claude/qc-mesh-r25/drc/tree/routed.odb. It invokes the same generated Tcl used after shield merging. Native readback matches the pure geometry model exactly:24 shields become620nm wide; all other-net shapes remain unchanged. KLayout0.30.12 reports M8/M9 same-net space/notch0 and other-net40nm separation0 after correction. The original24 M9 violations are the positive control. coupon_review.png was viewed before native qualification.

Source base18c6286d88, also the exact HEAD of the paused intel2 claude/qc-r29-notch-1027 worktree. That paused worktree had no implementation delta or notch jobs and was not edited. Work occurred in codex/qc-notch-r28-1027. The repair marks created shield SWires in combo_tcl; only marked shield boxes may be trimmed, so PG cannot be mistaken for a shield of the same width. The post-pass requires this marking rather than guessing from widths.

Scope: actual encoder geometry coupon, not a full-die route, IR or timing result. R28 planner dry-build errors remain with the planner owner. Source model keepouts remain conservative over the small removed shield strip. Full candidate rebuild/census must include the actual trimmed geometry before routing/RCX; there is no clock or uncertainty relaxation.

Native run: intel2:/srv/opentallas-scratch2/claude/codex-qc-notch-r29-1351 (all jobs terminal). Extract3565115, model3639366, native3669548, qualification3695743. Native ODB retained there; source/model/native rectangles and the KLayout deck are committed here.

## Root-review correction: explicit outer-face guards

The initial SWire-only eligibility was insufficient as a generic encoder policy; that eligibility is superseded. Production fw now marks each created shield SBox with its actual OUTER edge relative to the source clock and nominal width. Same-track merging retains this metadata only if every merged source agrees. Unmarked PG, unknown faces and shared shields facing clocks on both sides cannot be trimmed. The normalizer checks the exact edge it would remove against that outer-face metadata.

The guarded native coupon passes all24 cases again, with180 source shields' face relations independently derived from actual neighboring clock rectangles. Native controls confirm: SAFE same-face union trims640->620; WRONG clock-facing edge remains640; DUAL opposite faces on a shared shield remain640; EXCESS160->140 would remain above tech minimum but is refused by the coupon-qualified maximum3.125% width-loss guard. These are actual OpenDB controls, not string matching. Guarded KLayout/native results are in guarded/.

Width/EM census:24 changed M9 rows,640nm nominal ->620nm actual,3.125% cross-section loss. At fixed current the density multiplier is32/31=1.0322580645. This is an explicit EM burden, NOT an EM PASS or an assumed headroom margin. The geometric loss guard only bounds this coupon-qualified change; actual shield current/density and full candidate PG/EM remain open. Every production edit prints nominal/actual width, outer face and density multiplier. No clock-facing edge, clock conductor or PG box is moved.
